"""
AI-Assisted OCR Correction Service for Malaysian Library Ledger
Uses fuzzy matching and database lookups to auto-correct and suggest fixes for OCR errors.

Supports Malaysian ledger fields:
No Perolehan | No Panggilan | Pengarang | Tajuk Buku | Penerbit | 
Tarikh Penerbit | Tarikh Perolehan | Bil. No. | Punca | Harga | Muka Surat | Catatan
"""
from difflib import SequenceMatcher, get_close_matches
from typing import List, Optional, Tuple, Dict
import re


class OCRCorrectionService:
    """
    AI-assisted correction for Malaysian library ledger OCR output.
    Uses fuzzy matching against known database records and common patterns.
    """
    
    def __init__(self):
        self.book_cache = {}          # accession_number -> BookCopy
        self.title_cache = {}         # title.lower() -> Book
        self.author_cache = {}        # author name patterns
        self.publisher_cache = set()  # Known publishers
        self.call_number_cache = {}   # call_number -> Book
        
        # Common Malaysian publisher locations
        self.publisher_locations = [
            'Kuala Lumpur', 'Selangor', 'Petaling Jaya', 'Shah Alam',
            'Penang', 'Pulau Pinang', 'Johor Bahru', 'Melaka', 'Ipoh',
            'Kuching', 'Kota Kinabalu', 'Singapore', 'London', 'New York',
            'Oxford', 'Cambridge', 'Jakarta', 'Bandung'
        ]
        
        # Common Malaysian publishers
        self.known_publishers = [
            'Dewan Bahasa dan Pustaka', 'DBP', 'PTS Publications', 
            'Penerbit UTM', 'Penerbit UM', 'Penerbit USM', 'Penerbit UKM',
            'Oxford Fajar', 'Pearson', 'McGraw-Hill', 'Longman',
            'Institut Terjemahan', 'ITNM', 'Utusan Publications',
            'Kementerian Pendidikan', 'Pustaka Cipta'
        ]
    
    def load_database_cache(self):
        """Load books and related data from database for matching"""
        from app.models import Book, BookCopy
        
        # Cache book copies by accession number
        copies = BookCopy.query.all()
        self.book_cache = {c.accession_number: c for c in copies}
        
        # Cache books by title and call number
        books = Book.query.all()
        for book in books:
            self.title_cache[book.title.lower()] = book
            if book.call_number:
                self.call_number_cache[book.call_number] = book
            if book.author:
                self.author_cache[book.author.lower()] = book.author
            if book.publisher:
                self.publisher_cache.add(book.publisher)
    
    def correct_no_perolehan(self, ocr_text: str) -> Dict:
        """
        Correct accession number (No Perolehan) from OCR text.
        Format typically: XX.YY (e.g., 40.21, 401.3)
        """
        ocr_text = ocr_text.strip()
        result = {
            'original': ocr_text,
            'corrected': None,
            'confidence': 0.0,
            'matched': False
        }
        
        # Clean up common OCR errors
        cleaned = ocr_text.replace('O', '0').replace('l', '1').replace('I', '1')
        cleaned = re.sub(r'[,;:]', '.', cleaned)  # Common period substitutions
        
        # Check if it matches the expected pattern
        if re.match(r'^\d{2,3}\.\d{1,3}$', cleaned):
            result['corrected'] = cleaned
            result['confidence'] = 0.9
            result['matched'] = True
        elif re.match(r'^\d{2,5}$', cleaned):
            # Try to add decimal point
            if len(cleaned) >= 4:
                result['corrected'] = f"{cleaned[:-2]}.{cleaned[-2:]}"
                result['confidence'] = 0.7
                result['matched'] = True
        
        return result
    
    def correct_no_panggilan(self, ocr_text: str) -> Dict:
        """
        Correct call number (No Panggilan) from OCR text.
        Common Dewey formats: 400.233, 500, 600, etc.
        """
        if not self.call_number_cache:
            self.load_database_cache()
        
        ocr_text = ocr_text.strip().upper()
        result = {
            'original': ocr_text,
            'corrected': None,
            'confidence': 0.0,
            'suggestions': [],
            'matched': False
        }
        
        # Clean common OCR errors
        cleaned = ocr_text.replace('O', '0').replace('l', '1').replace('I', '1')
        
        # Direct match in database
        if cleaned in self.call_number_cache:
            result['corrected'] = cleaned
            result['confidence'] = 1.0
            result['matched'] = True
            result['book_title'] = self.call_number_cache[cleaned].title
            return result
        
        # Fuzzy match
        close_matches = get_close_matches(cleaned, list(self.call_number_cache.keys()), n=3, cutoff=0.6)
        if close_matches:
            best = close_matches[0]
            similarity = SequenceMatcher(None, cleaned, best).ratio()
            result['corrected'] = best
            result['confidence'] = similarity
            result['matched'] = similarity > 0.8
            result['book_title'] = self.call_number_cache[best].title
            result['suggestions'] = [
                {'call_number': cn, 'title': self.call_number_cache[cn].title,
                 'similarity': SequenceMatcher(None, cleaned, cn).ratio()}
                for cn in close_matches
            ]
        
        return result
    
    def correct_pengarang(self, ocr_text: str) -> Dict:
        """
        Correct author name (Pengarang) from OCR text.
        Uses fuzzy matching against known authors.
        """
        if not self.author_cache:
            self.load_database_cache()
        
        ocr_text = ocr_text.strip()
        result = {
            'original': ocr_text,
            'corrected': None,
            'confidence': 0.0,
            'suggestions': [],
            'matched': False
        }
        
        if not ocr_text:
            return result
        
        # Fuzzy match against known authors
        close_matches = get_close_matches(ocr_text.lower(), list(self.author_cache.keys()), n=5, cutoff=0.5)
        
        if close_matches:
            best_match = close_matches[0]
            similarity = SequenceMatcher(None, ocr_text.lower(), best_match).ratio()
            
            result['corrected'] = self.author_cache[best_match]  # Get properly cased version
            result['confidence'] = similarity
            result['matched'] = similarity > 0.7
            result['suggestions'] = [
                {'author': self.author_cache[a], 
                 'similarity': SequenceMatcher(None, ocr_text.lower(), a).ratio()}
                for a in close_matches
            ]
        
        return result
    
    def correct_tajuk_buku(self, ocr_text: str) -> Dict:
        """
        Correct book title (Tajuk Buku) from OCR text.
        Uses fuzzy matching against known titles.
        """
        if not self.title_cache:
            self.load_database_cache()
        
        ocr_text = ocr_text.strip()
        result = {
            'original': ocr_text,
            'corrected': None,
            'confidence': 0.0,
            'suggestions': [],
            'matched': False,
            'book_id': None
        }
        
        if not ocr_text or len(ocr_text) < 3:
            return result
        
        # Fuzzy match against known titles
        close_matches = get_close_matches(ocr_text.lower(), list(self.title_cache.keys()), n=5, cutoff=0.4)
        
        if close_matches:
            best_match = close_matches[0]
            similarity = SequenceMatcher(None, ocr_text.lower(), best_match).ratio()
            book = self.title_cache[best_match]
            
            result['corrected'] = book.title
            result['confidence'] = similarity
            result['matched'] = similarity > 0.6
            result['book_id'] = book.id
            result['author'] = book.author
            result['suggestions'] = [
                {'title': self.title_cache[t].title,
                 'author': self.title_cache[t].author,
                 'similarity': SequenceMatcher(None, ocr_text.lower(), t).ratio()}
                for t in close_matches
            ]
        
        return result
    
    def correct_penerbit(self, ocr_text: str) -> Dict:
        """
        Correct publisher (Penerbit) from OCR text.
        Matches against known publishers and locations.
        """
        ocr_text = ocr_text.strip()
        result = {
            'original': ocr_text,
            'corrected': None,
            'confidence': 0.0,
            'suggestions': [],
            'matched': False
        }
        
        if not ocr_text:
            return result
        
        # Try matching known publishers
        all_publishers = list(self.publisher_cache) + self.known_publishers
        close_matches = get_close_matches(ocr_text.lower(), [p.lower() for p in all_publishers], n=3, cutoff=0.5)
        
        if close_matches:
            # Find the original cased version
            for pub in all_publishers:
                if pub.lower() == close_matches[0]:
                    similarity = SequenceMatcher(None, ocr_text.lower(), pub.lower()).ratio()
                    result['corrected'] = pub
                    result['confidence'] = similarity
                    result['matched'] = similarity > 0.7
                    break
            
            result['suggestions'] = close_matches[:3]
        
        # Also try to identify location
        for loc in self.publisher_locations:
            if loc.lower() in ocr_text.lower():
                result['location'] = loc
                if not result['matched']:
                    result['confidence'] = max(result['confidence'], 0.5)
                break
        
        return result
    
    def auto_correct_row(self, row_data: Dict) -> Dict:
        """
        Auto-correct an entire OCR row using AI matching for Malaysian ledger format.
        
        Args:
            row_data: Dict with ledger fields (no_perolehan, pengarang, tajuk_buku, etc.)
        
        Returns:
            Enhanced row_data with corrections and suggestions
        """
        if not self.title_cache:
            self.load_database_cache()
        
        enhanced = row_data.copy()
        enhanced['ai_corrections'] = {}
        
        # Correct No Perolehan (Accession Number)
        if row_data.get('no_perolehan'):
            result = self.correct_no_perolehan(row_data['no_perolehan'])
            enhanced['ai_corrections']['no_perolehan'] = result
            if result['matched']:
                enhanced['suggested_no_perolehan'] = result['corrected']
        
        # Correct No Panggilan (Call Number)
        if row_data.get('no_panggilan'):
            result = self.correct_no_panggilan(row_data['no_panggilan'])
            enhanced['ai_corrections']['no_panggilan'] = result
            if result['matched']:
                enhanced['suggested_no_panggilan'] = result['corrected']
                if result.get('book_title'):
                    enhanced['suggested_tajuk_buku'] = result['book_title']
        
        # Correct Pengarang (Author)
        if row_data.get('pengarang'):
            result = self.correct_pengarang(row_data['pengarang'])
            enhanced['ai_corrections']['pengarang'] = result
            if result['matched']:
                enhanced['suggested_pengarang'] = result['corrected']
        
        # Correct Tajuk Buku (Title)
        if row_data.get('tajuk_buku'):
            result = self.correct_tajuk_buku(row_data['tajuk_buku'])
            enhanced['ai_corrections']['tajuk_buku'] = result
            if result['matched']:
                enhanced['suggested_tajuk_buku'] = result['corrected']
                if result.get('author') and not enhanced.get('suggested_pengarang'):
                    enhanced['suggested_pengarang'] = result['author']
        
        # Correct Penerbit (Publisher)
        if row_data.get('penerbit'):
            result = self.correct_penerbit(row_data['penerbit'])
            enhanced['ai_corrections']['penerbit'] = result
            if result['matched']:
                enhanced['suggested_penerbit'] = result['corrected']
        
        # Clean up date fields
        if row_data.get('tarikh_penerbit'):
            cleaned = self._clean_year(row_data['tarikh_penerbit'])
            if cleaned:
                enhanced['suggested_tarikh_penerbit'] = cleaned
        
        if row_data.get('tarikh_perolehan'):
            cleaned = self._clean_date(row_data['tarikh_perolehan'])
            if cleaned:
                enhanced['suggested_tarikh_perolehan'] = cleaned
        
        # Clean up numeric fields
        if row_data.get('harga_rm') or row_data.get('harga_sen'):
            rm, sen = self._clean_price(row_data.get('harga_rm', ''), row_data.get('harga_sen', ''))
            enhanced['suggested_harga_rm'] = rm
            enhanced['suggested_harga_sen'] = sen
        
        if row_data.get('muka_surat'):
            pages = self._clean_number(row_data['muka_surat'])
            if pages:
                enhanced['suggested_muka_surat'] = pages
        
        # Calculate overall AI confidence
        confidences = []
        for field in ['no_perolehan', 'no_panggilan', 'pengarang', 'tajuk_buku', 'penerbit']:
            if enhanced['ai_corrections'].get(field, {}).get('confidence'):
                confidences.append(enhanced['ai_corrections'][field]['confidence'])
        
        enhanced['ai_confidence'] = sum(confidences) / len(confidences) if confidences else 0.0
        enhanced['ai_auto_fill'] = enhanced['ai_confidence'] > 0.75
        
        return enhanced
    
    def _clean_year(self, text: str) -> Optional[str]:
        """Extract and clean year from text"""
        match = re.search(r'(19\d{2}|20\d{2})', str(text))
        return match.group(1) if match else None
    
    def _clean_date(self, text: str) -> Optional[str]:
        """Clean and normalize date string"""
        text = str(text).strip()
        # Try to extract just the year if that's all we have
        year_match = re.search(r'(19\d{2}|20\d{2})', text)
        if year_match:
            return year_match.group(1)
        return text if text else None
    
    def _clean_price(self, rm: str, sen: str) -> Tuple[str, str]:
        """Clean price values"""
        rm_clean = re.sub(r'[^\d.]', '', str(rm))
        sen_clean = re.sub(r'[^\d]', '', str(sen))
        return rm_clean or '0', sen_clean or '00'
    
    def _clean_number(self, text: str) -> Optional[str]:
        """Extract number from text"""
        match = re.search(r'(\d+)', str(text))
        return match.group(1) if match else None
    
    def get_all_suggestions(self, partial_text: str, field_type: str = 'title') -> List[Dict]:
        """
        Get all suggestions for autocomplete in the ledger review interface.
        
        Args:
            partial_text: Partial text to match
            field_type: 'title', 'author', 'publisher', 'call_number'
        
        Returns:
            List of suggestions with relevant fields and similarity score
        """
        if not self.title_cache:
            self.load_database_cache()
        
        partial = partial_text.strip()
        partial_lower = partial.lower()
        suggestions = []
        
        if field_type == 'title':
            for title_lower, book in self.title_cache.items():
                if partial_lower in title_lower or title_lower.startswith(partial_lower):
                    similarity = SequenceMatcher(None, partial_lower, title_lower).ratio()
                    suggestions.append({
                        'value': book.title,
                        'display': f"{book.title} - {book.author or 'Unknown'}",
                        'author': book.author,
                        'publisher': book.publisher,
                        'call_number': book.call_number,
                        'similarity': similarity if not title_lower.startswith(partial_lower) else 1.0
                    })
        
        elif field_type == 'author':
            for author_lower, author in self.author_cache.items():
                if partial_lower in author_lower or author_lower.startswith(partial_lower):
                    similarity = SequenceMatcher(None, partial_lower, author_lower).ratio()
                    suggestions.append({
                        'value': author,
                        'display': author,
                        'similarity': similarity if not author_lower.startswith(partial_lower) else 1.0
                    })
        
        elif field_type == 'publisher':
            all_publishers = list(self.publisher_cache) + self.known_publishers
            seen = set()
            for pub in all_publishers:
                if pub.lower() not in seen:
                    seen.add(pub.lower())
                    if partial_lower in pub.lower():
                        similarity = SequenceMatcher(None, partial_lower, pub.lower()).ratio()
                        suggestions.append({
                            'value': pub,
                            'display': pub,
                            'similarity': similarity if not pub.lower().startswith(partial_lower) else 1.0
                        })
        
        elif field_type == 'call_number':
            for cn, book in self.call_number_cache.items():
                if partial in cn or cn.startswith(partial):
                    similarity = SequenceMatcher(None, partial, cn).ratio()
                    suggestions.append({
                        'value': cn,
                        'display': f"{cn} - {book.title[:40]}",
                        'title': book.title,
                        'similarity': similarity if not cn.startswith(partial) else 1.0
                    })
        
        # Sort by similarity
        suggestions.sort(key=lambda x: x['similarity'], reverse=True)
        return suggestions[:10]
    
    def suggest_from_partial(self, field: str, value: str) -> Dict:
        """
        Get AI suggestion for a specific field based on partial input.
        Used for real-time autocomplete in the review interface.
        """
        result = {
            'original': value,
            'suggestions': [],
            'best_match': None,
            'confidence': 0.0
        }
        
        if not value or len(value) < 2:
            return result
        
        if field == 'pengarang':
            correction = self.correct_pengarang(value)
            result['suggestions'] = correction.get('suggestions', [])
            if correction['matched']:
                result['best_match'] = correction['corrected']
                result['confidence'] = correction['confidence']
        
        elif field == 'tajuk_buku':
            correction = self.correct_tajuk_buku(value)
            result['suggestions'] = correction.get('suggestions', [])
            if correction['matched']:
                result['best_match'] = correction['corrected']
                result['confidence'] = correction['confidence']
                result['related_author'] = correction.get('author')
        
        elif field == 'penerbit':
            correction = self.correct_penerbit(value)
            result['suggestions'] = correction.get('suggestions', [])
            if correction['matched']:
                result['best_match'] = correction['corrected']
                result['confidence'] = correction['confidence']
        
        elif field == 'no_panggilan':
            correction = self.correct_no_panggilan(value)
            result['suggestions'] = correction.get('suggestions', [])
            if correction['matched']:
                result['best_match'] = correction['corrected']
                result['confidence'] = correction['confidence']
                result['related_title'] = correction.get('book_title')
        
        return result


# Singleton instance
_correction_service = None

def get_correction_service() -> OCRCorrectionService:
    """Get singleton correction service instance"""
    global _correction_service
    if _correction_service is None:
        _correction_service = OCRCorrectionService()
    return _correction_service
