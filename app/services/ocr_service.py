"""
OCR Service - Tesseract-based OCR processing for ledger digitization
"""
import os
import re
import json
from datetime import datetime
from typing import List, Optional, Tuple
from dataclasses import dataclass
from PIL import Image

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
class ExtractedRow:
    """A single row extracted from a ledger page"""
    row_number: int
    raw_text: str
    member_id: Optional[str] = None
    member_name: Optional[str] = None
    book_id: Optional[str] = None
    book_title: Optional[str] = None
    transaction_type: Optional[str] = None  # borrow/return
    date_text: Optional[str] = None
    parsed_date: Optional[datetime] = None
    confidence: float = 0.0
    bbox: Optional[dict] = None  # {x, y, width, height}


class OCRService:
    """
    OCR processing service for library ledger digitization.
    Uses Tesseract OCR with table detection and field extraction.
    """
    
    def __init__(self, tesseract_cmd: str = None, languages: str = 'eng+msa'):
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
        ]
    
    def is_available(self) -> bool:
        """Check if Tesseract is available"""
        if not TESSERACT_AVAILABLE:
            return False
        try:
            pytesseract.get_tesseract_version()
            return True
        except:
            return False
    
    def process_image(self, image_path: str) -> Tuple[str, List[dict]]:
        """
        Process a single image and extract text with bounding boxes.
        
        Returns:
            Tuple of (full_text, list of word data with positions)
        """
        if not self.is_available():
            raise RuntimeError("Tesseract OCR is not available")
        
        image = Image.open(image_path)
        
        # Get full text
        full_text = pytesseract.image_to_string(image, lang=self.languages)
        
        # Get detailed data with bounding boxes
        data = pytesseract.image_to_data(image, lang=self.languages, output_type=pytesseract.Output.DICT)
        
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
        
        images = convert_from_path(pdf_path, dpi=dpi)
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
    
    def extract_ledger_rows(self, text: str, words: List[dict]) -> List[ExtractedRow]:
        """
        Parse OCR output to extract ledger rows.
        Attempts to identify table structure and extract fields.
        
        This is a basic implementation that can be enhanced with:
        - Custom table detection
        - Machine learning for field classification
        - Template matching for specific ledger formats
        """
        rows = []
        lines = text.strip().split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line or len(line) < 5:  # Skip very short lines
                continue
            
            row = ExtractedRow(
                row_number=i,
                raw_text=line,
                confidence=0.5  # Default confidence
            )
            
            # Try to extract fields using patterns
            row = self._extract_fields(row, words)
            rows.append(row)
        
        return rows
    
    def _extract_fields(self, row: ExtractedRow, words: List[dict]) -> ExtractedRow:
        """
        Extract structured fields from a row of text.
        Uses pattern matching and heuristics.
        """
        text = row.raw_text
        
        # Extract date
        for pattern in self.date_patterns:
            match = re.search(pattern, text)
            if match:
                row.date_text = match.group()
                row.parsed_date = self._parse_date(row.date_text)
                break
        
        # Look for member ID patterns (e.g., student numbers)
        # Common formats: A12345, 2023001, IC number patterns
        member_patterns = [
            r'\b[A-Z]\d{5,8}\b',           # A12345678
            r'\b\d{4,8}\b',                 # 20230001
            r'\b\d{6}-\d{2}-\d{4}\b',       # IC format
        ]
        for pattern in member_patterns:
            match = re.search(pattern, text)
            if match:
                row.member_id = match.group()
                break
        
        # Look for book accession number patterns
        # Common: ACC-12345, B12345, numeric sequences
        book_patterns = [
            r'\bACC[-/]?\d{4,8}\b',         # ACC-12345
            r'\bB\d{4,8}\b',                 # B12345
            r'\b\d{4,6}\b',                  # 123456
        ]
        for pattern in book_patterns:
            matches = re.findall(pattern, text)
            if matches:
                # Take the one that's not the member ID
                for m in matches:
                    if m != row.member_id:
                        row.book_id = m
                        break
                break
        
        # Detect transaction type
        text_lower = text.lower()
        if any(word in text_lower for word in ['pinjam', 'borrow', 'checkout', 'keluar']):
            row.transaction_type = 'borrow'
        elif any(word in text_lower for word in ['pulang', 'return', 'checkin', 'masuk']):
            row.transaction_type = 'return'
        
        # Calculate average confidence from matching words
        line_words = [w for w in words if w.get('line_num') == row.row_number]
        if line_words:
            confidences = [w['confidence'] for w in line_words if w['confidence'] > 0]
            if confidences:
                row.confidence = sum(confidences) / len(confidences) / 100.0
        
        return row
    
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
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_text, fmt)
            except ValueError:
                continue
        
        return None
    
    def process_file(self, file_path: str) -> dict:
        """
        Process a file (image or PDF) and return structured results.
        
        Returns:
            Dict with keys: pages, total_rows, rows (list of ExtractedRow dicts)
        """
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.pdf':
            page_results = self.process_pdf(file_path)
            all_rows = []
            for page_num, (text, words) in enumerate(page_results, 1):
                rows = self.extract_ledger_rows(text, words)
                for row in rows:
                    row_dict = {
                        'page_number': page_num,
                        'row_number': row.row_number,
                        'raw_text': row.raw_text,
                        'member_id': row.member_id,
                        'member_name': row.member_name,
                        'book_id': row.book_id,
                        'book_title': row.book_title,
                        'transaction_type': row.transaction_type,
                        'date_text': row.date_text,
                        'parsed_date': row.parsed_date.isoformat() if row.parsed_date else None,
                        'confidence': row.confidence
                    }
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
                'rows': [{
                    'page_number': 1,
                    'row_number': row.row_number,
                    'raw_text': row.raw_text,
                    'member_id': row.member_id,
                    'member_name': row.member_name,
                    'book_id': row.book_id,
                    'book_title': row.book_title,
                    'transaction_type': row.transaction_type,
                    'date_text': row.date_text,
                    'parsed_date': row.parsed_date.isoformat() if row.parsed_date else None,
                    'confidence': row.confidence
                } for row in rows]
            }
