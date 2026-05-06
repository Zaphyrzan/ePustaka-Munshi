"""
OCR Service - Tesseract-based OCR processing for Malaysian library ledger digitization

Handles extraction of ledger table with columns:
No Perolehan | No Panggilan | Pengarang | Tajuk Buku | Tempat & Nama Penerbit |
Tarikh Penerbit | Tarikh Perolehan | Bil. No. | Punca | Harga RM Sen | Muka Surat | Catatan
"""
import os
import re
import json
from datetime import datetime
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass, field
from PIL import Image, ImageEnhance, ImageFilter

# Tesseract OCR
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

# PDF support
try:
    from pdf2image import convert_from_path
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False


@dataclass
class LedgerRow:
    """A single row extracted from a Malaysian library ledger"""
    row_number: int
    raw_text: str
    
    # Malaysian ledger fields
    no_perolehan: Optional[str] = None      # Accession/Acquisition Number
    no_panggilan: Optional[str] = None       # Call Number  
    pengarang: Optional[str] = None          # Author
    tajuk_buku: Optional[str] = None         # Book Title
    penerbit: Optional[str] = None           # Publisher (Place & Name)
    tarikh_penerbit: Optional[str] = None    # Publication Date/Year
    tarikh_perolehan: Optional[str] = None   # Acquisition Date
    bil_no: Optional[str] = None             # Bill Number
    punca: Optional[str] = None              # Source/Origin
    harga_rm: Optional[str] = None           # Price (RM)
    harga_sen: Optional[str] = None          # Price (Sen)
    muka_surat: Optional[str] = None         # Page Count
    catatan: Optional[str] = None            # Notes/Remarks
    
    confidence: float = 0.0
    bbox: Optional[dict] = None  # {x, y, width, height}
    
    # Per-field confidence
    confidence_details: Dict[str, float] = field(default_factory=dict)


class OCRService:
    """
    OCR processing service for Malaysian library ledger digitization.
    Uses Tesseract OCR with image preprocessing for improved accuracy.
    """
    
    def __init__(self, tesseract_cmd: str = None, languages: str = 'eng'):
        """
        Initialize OCR service.
        
        Args:
            tesseract_cmd: Path to tesseract executable
            languages: Tesseract language codes (e.g., 'eng', 'msa', 'eng+msa')
        """
        self.languages = languages
        
        if tesseract_cmd and TESSERACT_AVAILABLE:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        
        # Common date patterns for Malaysian context
        self.date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # DD/MM/YYYY or DD-MM-YY
            r'\d{1,2}\s+\w+\s+\d{2,4}',         # DD Month YYYY
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',     # YYYY-MM-DD
            r'\d{4}',                            # Just year (common in ledgers)
        ]
        
        # Patterns for No Perolehan (e.g., 40.21, 40.22, 401.3, or just 4021)
        self.no_perolehan_pattern = r'\b\d{3,5}\b'
        
        # Patterns for No Panggilan (call numbers like 400.233, 500, 600)
        self.no_panggilan_pattern = r'\b\d{3}[-.]?\d{0,3}\b'
        
        # Price patterns
        self.price_pattern = r'(\d+)[,.](\d{2})'
    
    def is_available(self) -> bool:
        """Check if Tesseract is available"""
        if not TESSERACT_AVAILABLE:
            return False
        try:
            pytesseract.get_tesseract_version()
            return True
        except:
            return False
    
    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image to improve OCR accuracy.
        
        Steps:
        1. Convert to grayscale
        2. Resize if too small
        3. Increase contrast
        4. Apply sharpening
        5. Binarize (convert to black & white)
        """
        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')
        
        # Resize if too small (OCR works better on larger images)
        width, height = image.size
        if width < 1500:
            scale = 1500 / width
            new_size = (int(width * scale), int(height * scale))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        # Increase contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        
        # Increase sharpness
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.5)
        
        # Reduce noise with median filter
        image = image.filter(ImageFilter.MedianFilter(size=3))
        
        # Sharpen again after noise reduction
        image = image.filter(ImageFilter.SHARPEN)
        
        # Binarize using threshold
        threshold = 150
        image = image.point(lambda x: 255 if x > threshold else 0, mode='1')
        
        # Convert back to grayscale for Tesseract
        image = image.convert('L')
        
        return image
    
    def process_image(self, image_path: str, preprocess: bool = True) -> Tuple[str, List[dict]]:
        """
        Process a single image and extract text with bounding boxes.
        
        Args:
            image_path: Path to the image file
            preprocess: Whether to apply image preprocessing (default True)
        
        Returns:
            Tuple of (full_text, list of word data with positions)
        """
        if not self.is_available():
            raise RuntimeError("Tesseract OCR is not available")
        
        image = Image.open(image_path)
        
        # Preprocess image for better OCR accuracy
        if preprocess:
            image = self.preprocess_image(image)
        
        # Configure Tesseract for better table/ledger recognition
        # PSM 6 = Assume uniform block of text
        # OEM 3 = Default, based on what is available
        custom_config = r'--oem 3 --psm 6'
        
        # Get full text
        full_text = pytesseract.image_to_string(
            image, 
            lang=self.languages,
            config=custom_config
        )
        
        # Get detailed data with bounding boxes
        data = pytesseract.image_to_data(
            image, 
            lang=self.languages, 
            config=custom_config,
            output_type=pytesseract.Output.DICT
        )
        
        # Structure word data
        words = []
        for i in range(len(data['text'])):
            if data['text'][i].strip():
                words.append({
                    'text': data['text'][i],
                    'x': data['left'][i],
                    'y': data['top'][i],
                    'width': data['width'][i],
                    'height': data['height'][i],
                    'confidence': data['conf'][i],
                    'line_num': data['line_num'][i],
                    'block_num': data['block_num'][i]
                })
        
        return full_text, words
    
    def process_pdf(self, pdf_path: str, dpi: int = 300) -> List[Tuple[str, List[dict]]]:
        """
        Process a PDF file, converting each page to image and OCR.
        
        Returns:
            List of (full_text, words) tuples, one per page
        """
        if not PDF_SUPPORT:
            raise RuntimeError("PDF support not available. Install pdf2image and poppler.")
        
        # Find Poppler path - check common locations
        poppler_path = None
        poppler_locations = [
            r"C:\Users\wanza\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\poppler-25.07.0\Library\bin",
            r"C:\Program Files\poppler\bin",
            r"C:\Program Files\poppler-24.02.0\Library\bin",
            r"C:\poppler\bin",
        ]
        
        for loc in poppler_locations:
            if os.path.exists(os.path.join(loc, "pdftoppm.exe")):
                poppler_path = loc
                break
        
        # Also check PATH environment variable
        if not poppler_path:
            import shutil
            if shutil.which("pdftoppm"):
                poppler_path = None  # It's in PATH, no need to specify
        
        try:
            if poppler_path:
                images = convert_from_path(pdf_path, dpi=dpi, poppler_path=poppler_path)
            else:
                images = convert_from_path(pdf_path, dpi=dpi)
        except Exception as e:
            raise RuntimeError(f"PDF conversion failed: {str(e)}. Ensure Poppler is installed.")
        
        results = []
        
        for image in images:
            # Save temp image
            temp_path = f"{pdf_path}_temp.png"
            image.save(temp_path, 'PNG')
            
            try:
                result = self.process_image(temp_path)
                results.append(result)
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        
        return results
    
    def extract_ledger_rows(self, text: str, words: List[dict]) -> List[LedgerRow]:
        """
        Parse OCR output to extract Malaysian library ledger rows.
        Handles the 7-column format:
        
        1. NO PEROLEHAN (Accession Number)
        2. NO PANGGILAN (Call Number)
        3. PENGARANG (Author)
        4. TAJUK BUKU (Book Title)
        5. TEMPAT DAN NAMA PENERBIT (Publisher Place & Name)
        6. TARIKH PENERBIT (Publication Date/Year)
        7. PUNCA (Source/Origin)
        
        Plus optional fields: Tarikh Perolehan, Bil No, Harga RM/Sen, Muka Surat, Catatan
        """
        rows = []
        lines = text.strip().split('\n')
        
        # Try to detect table structure from word positions
        column_boundaries = self._detect_columns(words)
        
        data_row_num = 0
        for i, line in enumerate(lines, 1):
            line = line.strip()
            # Skip empty lines or very short lines
            if not line or len(line) < 3:
                continue
            
            # Skip header lines (contain Malaysian column names or English equivalents)
            if self._is_header_line(line):
                continue
            
            data_row_num += 1
            
            row = LedgerRow(
                row_number=data_row_num,
                raw_text=line,
                confidence=0.5  # Default confidence
            )
            
            # Extract fields using the best available method
            try:
                if column_boundaries and len(column_boundaries) >= 7:
                    # Use detected columns for structure-aware extraction
                    row = self._extract_fields_by_columns(row, words, i, column_boundaries)
                else:
                    # Use pattern-based extraction (more robust fallback)
                    row = self._extract_fields_by_patterns(row, words)
            except Exception as e:
                # If extraction fails, at least preserve the raw text
                print(f"Warning: Field extraction failed for row {data_row_num}: {str(e)}")
            
            rows.append(row)
        
        return rows
    
    def _is_header_line(self, line: str) -> bool:
        """Check if a line is a header row"""
        header_keywords = [
            'no perolehan', 'no panggilan', 'pengarang', 'tajuk', 'penerbit',
            'tarikh', 'bil', 'punca', 'harga', 'muka surat', 'catatan',
            'accession', 'call number', 'author', 'title', 'publisher'
        ]
        line_lower = line.lower()
        matches = sum(1 for kw in header_keywords if kw in line_lower)
        return matches >= 3
    
    def _detect_columns(self, words: List[dict]) -> Optional[List[int]]:
        """
        Detect column boundaries from word positions.
        Returns list of x-coordinates marking column boundaries.
        """
        if not words:
            return None
        
        # Group words by line
        lines_dict = {}
        for w in words:
            line_num = w.get('line_num', 0)
            if line_num not in lines_dict:
                lines_dict[line_num] = []
            lines_dict[line_num].append(w)
        
        # Analyze gaps between words to find column boundaries
        # This is a simplified approach - could be enhanced with ML
        all_x_positions = [w['x'] for w in words if w.get('x')]
        if not all_x_positions:
            return None
        
        # Use clustering to find column positions
        all_x_positions.sort()
        return None  # For now, fall back to pattern-based extraction
    
    def _extract_fields_by_patterns(self, row: LedgerRow, words: List[dict]) -> LedgerRow:
        """
        Extract 7 structured fields from a ledger row using intelligent pattern matching.
        
        Column order (7 main columns):
        1. NO PEROLEHAN (accession number) - pattern: digits/dots
        2. NO PANGGILAN (call number) - pattern: 3 digits or Dewey-like
        3. PENGARANG (author) - text name(s)
        4. TAJUK BUKU (title) - longer text
        5. PENERBIT (publisher) - location + publisher name
        6. TARIKH PENERBIT (pub year) - 4-digit year
        7. PUNCA (source) - text
        """
        text = row.raw_text
        
        # ===== FIELD 1: NO PEROLEHAN (Accession Number) =====
        # Pattern: Numbers with optional dots/dashes (e.g., "40.21", "401.3")
        perolehan_match = re.search(self.no_perolehan_pattern, text)
        if perolehan_match:
            row.no_perolehan = perolehan_match.group()
            row.confidence_details['no_perolehan'] = 0.85
        
        # ===== FIELD 2: NO PANGGILAN (Call Number) =====
        # Remove the accession number to avoid duplication
        remaining = text
        if row.no_perolehan:
            # Find and skip the accession number
            remaining = text.replace(row.no_perolehan, '', 1).strip()
        
        # Look for call numbers (typically 3 digits, can have dots)
        panggilan_matches = re.findall(self.no_panggilan_pattern, remaining)
        if panggilan_matches:
            row.no_panggilan = panggilan_matches[0]
            row.confidence_details['no_panggilan'] = 0.8
            # Remove this from remaining text
            remaining = remaining.replace(row.no_panggilan, '', 1).strip()
        
        # ===== FIELD 6: TARIKH PENERBIT (Publication Year) =====
        # Extract years early (they help segment the row)
        year_patterns = re.findall(r'\b(19\d{2}|20\d{2})\b', text)
        if year_patterns:
            row.tarikh_penerbit = year_patterns[0]
            row.confidence_details['tarikh_penerbit'] = 0.9
            # If there are multiple years, second might be acquisition date
            if len(year_patterns) >= 2:
                row.tarikh_perolehan = year_patterns[1]
        
        # ===== FIELD 7: PUNCA (Source) =====
        # Common sources in Malaysian libraries: Pembelian, Derma, Sumbangan, etc.
        source_keywords = ['pembelian', 'derma', 'sumbangan', 'hadiah', 'tukar', 'daftar', 
                          'purchase', 'donation', 'gift', 'book', 'received', 'acquired']
        for kw in source_keywords:
            if kw in text.lower():
                row.punca = kw.capitalize()
                row.confidence_details['punca'] = 0.7
                break
        
        # ===== FIELDS 3, 4, 5: Text fields (Author, Title, Publisher) =====
        # These occupy the middle section after numbers are removed
        self._extract_text_fields_structured(row, text, remaining)
        
        # ===== Additional fields from patterns =====
        # Price (Harga)
        price_match = re.search(r'RM?\s*(\d+)[,.]?(\d{0,2})', text, re.IGNORECASE)
        if price_match:
            row.harga_rm = price_match.group(1)
            row.harga_sen = price_match.group(2) if price_match.group(2) else '0'
            row.confidence_details['harga_rm'] = 0.8
        
        # Page count (Muka Surat)
        page_match = re.search(r'\b(\d{1,4})\s*(?:ms?|pages?|muka)?\s*$', text, re.IGNORECASE)
        if page_match:
            row.muka_surat = page_match.group(1)
            row.confidence_details['muka_surat'] = 0.75
        
        # Calculate overall confidence
        if row.confidence_details:
            confidences = list(row.confidence_details.values())
            row.confidence = sum(confidences) / len(confidences) if confidences else 0.5
        
        return row
    
    def _extract_text_fields_structured(self, row: LedgerRow, full_text: str, remaining_text: str) -> None:
        """
        Extract author, title, and publisher from the middle text portion.
        Uses position heuristics for Malaysian library ledgers.
        """
        # Work with remaining text (numbers already removed)
        text = remaining_text if remaining_text else full_text
        
        # Remove known publisher locations to make parsing easier
        publisher_locations = [
            'kuala lumpur', 'kl', 'selangor', 'petaling jaya', 'shah alam', 'cyberjaya',
            'penang', 'pulau pinang', 'johor', 'johor bahru', 'melaka', 'ipoh', 'perak',
            'kedah', 'perlis', 'terengganu', 'kelantan', 'pahang', 'singapore', 'sg',
            'london', 'new york', 'oxford', 'cambridge', 'cambridge university',
            'macmillan', 'penguin', 'oxford university', 'bloomsbury'
        ]
        
        publisher_end = -1
        text_lower = text.lower()
        
        # Find where publisher info likely starts
        for loc in publisher_locations:
            match = re.search(r'\b' + re.escape(loc) + r'\b', text_lower)
            if match:
                publisher_end = match.start()
                break
        
        if publisher_end > 0:
            # Extract publisher (from location onwards to end or next known delimiter)
            pub_text = text[publisher_end:].strip()
            # Clean up - take first 100 chars or until end punctuation
            pub_text = re.sub(r'\d{4}\s*$', '', pub_text).strip()  # Remove years at end
            if len(pub_text) > 150:
                pub_text = pub_text[:150]
            row.penerbit = pub_text
            row.confidence_details['penerbit'] = 0.7
            
            # Use text before publisher for author and title
            text = text[:publisher_end].strip()
        
        # Now split remaining text into author and title
        # Malaysian books often have: Author(s), Title, so look for commas
        parts = text.split(',')
        
        if len(parts) >= 2:
            # First part before comma = author
            author_candidate = parts[0].strip()
            # Second part and onwards = title
            title_candidate = ','.join(parts[1:]).strip()
            
            # Validate: author should be shorter, title should be longer
            if len(author_candidate) < 50 and len(title_candidate) > len(author_candidate):
                row.pengarang = author_candidate
                row.tajuk_buku = title_candidate
                row.confidence_details['pengarang'] = 0.75
                row.confidence_details['tajuk_buku'] = 0.75
            else:
                # If validation fails, try splitting by length
                word_list = text.split()
                if len(word_list) > 4:
                    # First 2-3 words = author, rest = title
                    author_end = min(3, len(word_list) // 2)
                    row.pengarang = ' '.join(word_list[:author_end])
                    row.tajuk_buku = ' '.join(word_list[author_end:])
                    row.confidence_details['pengarang'] = 0.65
                    row.confidence_details['tajuk_buku'] = 0.65
                elif len(word_list) > 0:
                    row.tajuk_buku = ' '.join(word_list)
                    row.confidence_details['tajuk_buku'] = 0.6
        else:
            # No comma - assume entire remaining text is title
            if text:
                row.tajuk_buku = text.strip()
                row.confidence_details['tajuk_buku'] = 0.5
    
    def _extract_text_fields(self, row: LedgerRow, text: str) -> None:
        """
        Extract text-based fields (author, title, publisher) from the middle of the row.
        This uses heuristics to split the text content.
        """
        # Remove known extracted values to get the text content
        remaining = text
        
        # Remove numbers we've identified
        for val in [row.no_perolehan, row.no_panggilan, row.tarikh_penerbit, 
                    row.tarikh_perolehan, row.harga_rm, row.muka_surat]:
            if val:
                remaining = remaining.replace(str(val), ' ', 1)
        
        # Clean up and split
        remaining = ' '.join(remaining.split())
        words = remaining.split()
        
        if not words:
            return
        
        # Heuristic: First 1-3 words that look like a name = Author
        # Longer phrase after = Title
        # Location + name at end = Publisher
        
        # Look for publisher indicators (city names commonly found in Malaysian books)
        publisher_keywords = ['kuala lumpur', 'selangor', 'petaling jaya', 'shah alam', 
                             'penang', 'johor', 'melaka', 'singapore', 'london', 'new york',
                             'oxford', 'cambridge', 'kl', 'dbp', 'dewan bahasa']
        
        text_lower = remaining.lower()
        publisher_start = -1
        for kw in publisher_keywords:
            idx = text_lower.find(kw)
            if idx != -1:
                publisher_start = idx
                break
        
        if publisher_start > 0:
            row.penerbit = remaining[publisher_start:].strip()
            remaining = remaining[:publisher_start].strip()
        
        # Split remaining into author and title
        # Common pattern: "LastName, FirstName" or single name, then title
        words = remaining.split()
        if len(words) >= 4:
            # First 2-3 words as author, rest as title
            author_words = []
            title_words = []
            
            # Look for comma which often separates author name
            comma_idx = remaining.find(',')
            if comma_idx > 0 and comma_idx < 50:
                author_end = remaining.find(' ', comma_idx)
                if author_end == -1:
                    author_end = len(remaining)
                row.pengarang = remaining[:author_end].strip()
                row.tajuk_buku = remaining[author_end:].strip()
            else:
                # Assume first 2 words are author
                row.pengarang = ' '.join(words[:2])
                row.tajuk_buku = ' '.join(words[2:])
        elif len(words) >= 2:
            row.pengarang = words[0]
            row.tajuk_buku = ' '.join(words[1:])
        elif words:
            row.tajuk_buku = ' '.join(words)
    
    def _extract_fields_by_columns(self, row: LedgerRow, words: List[dict], 
                                    line_num: int, column_boundaries: List[int]) -> LedgerRow:
        """
        Extract fields using detected column boundaries.
        """
        # Get words for this line
        line_words = [w for w in words if w.get('line_num') == line_num]
        if not line_words:
            return self._extract_fields_by_patterns(row, words)
        
        # Sort by x position
        line_words.sort(key=lambda w: w.get('x', 0))
        
        # Group words into columns based on boundaries
        # This would map words to specific ledger fields
        # For now, fall back to pattern extraction
        return self._extract_fields_by_patterns(row, words)
    
    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """
        Parse date string to datetime object.
        Handles common Malaysian date formats.
        """
        date_formats = [
            '%d/%m/%Y', '%d-%m-%Y',
            '%d/%m/%y', '%d-%m-%y',
            '%Y-%m-%d', '%Y/%m/%d',
            '%d %B %Y', '%d %b %Y',
            '%Y',  # Just year
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_text.strip(), fmt)
            except ValueError:
                continue
        
        return None
    
    def process_file(self, file_path: str) -> dict:
        """
        Process a file (image or PDF) and return structured results
        matching Malaysian library ledger format.
        
        Returns:
            Dict with keys: pages, total_rows, rows (list of LedgerRow dicts)
        """
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.pdf':
            page_results = self.process_pdf(file_path)
            all_rows = []
            for page_num, (text, words) in enumerate(page_results, 1):
                rows = self.extract_ledger_rows(text, words)
                for row in rows:
                    row_dict = self._row_to_dict(row, page_num)
                    all_rows.append(row_dict)
            
            return {
                'pages': len(page_results),
                'total_rows': len(all_rows),
                'rows': all_rows
            }
        else:
            # Image file
            text, words = self.process_image(file_path)
            rows = self.extract_ledger_rows(text, words)
            
            return {
                'pages': 1,
                'total_rows': len(rows),
                'rows': [self._row_to_dict(row, 1) for row in rows]
            }
    
    def _row_to_dict(self, row: LedgerRow, page_num: int) -> dict:
        """Convert a LedgerRow to dictionary for storage"""
        return {
            'page_number': page_num,
            'row_number': row.row_number,
            'raw_text': row.raw_text,
            # Malaysian ledger fields
            'no_perolehan': row.no_perolehan,
            'no_panggilan': row.no_panggilan,
            'pengarang': row.pengarang,
            'tajuk_buku': row.tajuk_buku,
            'penerbit': row.penerbit,
            'tarikh_penerbit': row.tarikh_penerbit,
            'tarikh_perolehan': row.tarikh_perolehan,
            'bil_no': row.bil_no,
            'punca': row.punca,
            'harga_rm': row.harga_rm,
            'harga_sen': row.harga_sen,
            'muka_surat': row.muka_surat,
            'catatan': row.catatan,
            # Confidence
            'confidence': row.confidence,
            'confidence_details': row.confidence_details
        }
