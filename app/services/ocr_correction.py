"""
AI-Assisted OCR Correction Service
Uses fuzzy matching and database lookups to auto-correct and suggest fixes for OCR errors.
"""
from difflib import SequenceMatcher, get_close_matches
from typing import List, Optional, Tuple, Dict
import re


class OCRCorrectionService:
    """
    AI-assisted correction for OCR output.
    Uses fuzzy matching against known database records to suggest corrections.
    """
    
    def __init__(self):
        self.member_cache = {}
        self.book_cache = {}
        self.name_cache = {}
    
    def load_database_cache(self):
        """Load members and books from database for matching"""
        from app.models import Member, BookCopy, Book
        
        # Cache member IDs and names
        members = Member.query.filter_by(is_active=True).all()
        self.member_cache = {m.member_id: m for m in members}
        self.name_cache = {m.full_name.lower(): m.member_id for m in members}
        
        # Cache book accession numbers and titles
        copies = BookCopy.query.all()
        self.book_cache = {c.accession_number: c for c in copies}
        
        # Also cache by title for fuzzy matching
        books = Book.query.all()
        self.title_cache = {b.title.lower(): [c.accession_number for c in b.copies] for b in books}
    
    def correct_member_id(self, ocr_text: str, confidence: float = 0.0) -> Dict:
        """
        Attempt to correct/match a member ID from OCR text.
        
        Returns:
            Dict with keys: original, corrected, confidence, suggestions, matched
        """
        if not self.member_cache:
            self.load_database_cache()
        
        ocr_text = ocr_text.strip().upper()
        result = {
            'original': ocr_text,
            'corrected': None,
            'confidence': confidence,
            'suggestions': [],
            'matched': False,
            'member_name': None
        }
        
        # Direct match
        if ocr_text in self.member_cache:
            member = self.member_cache[ocr_text]
            result['corrected'] = ocr_text
            result['confidence'] = 1.0
            result['matched'] = True
            result['member_name'] = member.full_name
            return result
        
        # Fuzzy match on member IDs
        all_ids = list(self.member_cache.keys())
        close_matches = get_close_matches(ocr_text, all_ids, n=3, cutoff=0.6)
        
        if close_matches:
            best_match = close_matches[0]
            similarity = SequenceMatcher(None, ocr_text, best_match).ratio()
            
            result['corrected'] = best_match
            result['confidence'] = similarity
            result['matched'] = similarity > 0.8
            result['member_name'] = self.member_cache[best_match].full_name
            result['suggestions'] = [
                {'id': m, 'name': self.member_cache[m].full_name, 
                 'similarity': SequenceMatcher(None, ocr_text, m).ratio()}
                for m in close_matches
            ]
        
        # Try matching by name if ID didn't work well
        if not result['matched'] and len(ocr_text) > 3:
            name_matches = get_close_matches(ocr_text.lower(), list(self.name_cache.keys()), n=3, cutoff=0.5)
            if name_matches:
                for name in name_matches:
                    member_id = self.name_cache[name]
                    similarity = SequenceMatcher(None, ocr_text.lower(), name).ratio()
                    result['suggestions'].append({
                        'id': member_id,
                        'name': self.member_cache[member_id].full_name,
                        'similarity': similarity,
                        'match_type': 'name'
                    })
        
        return result
    
    def correct_book_id(self, ocr_text: str, confidence: float = 0.0) -> Dict:
        """
        Attempt to correct/match a book accession number from OCR text.
        
        Returns:
            Dict with keys: original, corrected, confidence, suggestions, matched
        """
        if not self.book_cache:
            self.load_database_cache()
        
        ocr_text = ocr_text.strip().upper()
        result = {
            'original': ocr_text,
            'corrected': None,
            'confidence': confidence,
            'suggestions': [],
            'matched': False,
            'book_title': None
        }
        
        # Direct match
        if ocr_text in self.book_cache:
            copy = self.book_cache[ocr_text]
            result['corrected'] = ocr_text
            result['confidence'] = 1.0
            result['matched'] = True
            result['book_title'] = copy.book.title
            return result
        
        # Fuzzy match on accession numbers
        all_ids = list(self.book_cache.keys())
        close_matches = get_close_matches(ocr_text, all_ids, n=3, cutoff=0.6)
        
        if close_matches:
            best_match = close_matches[0]
            similarity = SequenceMatcher(None, ocr_text, best_match).ratio()
            
            result['corrected'] = best_match
            result['confidence'] = similarity
            result['matched'] = similarity > 0.8
            result['book_title'] = self.book_cache[best_match].book.title
            result['suggestions'] = [
                {'id': m, 'title': self.book_cache[m].book.title,
                 'similarity': SequenceMatcher(None, ocr_text, m).ratio()}
                for m in close_matches
            ]
        
        return result
    
    def auto_correct_row(self, row_data: Dict) -> Dict:
        """
        Auto-correct an entire OCR row using AI matching.
        
        Args:
            row_data: Dict with member_id, book_id, raw_text, etc.
        
        Returns:
            Enhanced row_data with corrections and suggestions
        """
        if not self.member_cache:
            self.load_database_cache()
        
        enhanced = row_data.copy()
        enhanced['ai_corrections'] = {}
        
        # Correct member ID
        if row_data.get('member_id'):
            member_result = self.correct_member_id(
                row_data['member_id'], 
                row_data.get('confidence', 0)
            )
            enhanced['ai_corrections']['member'] = member_result
            
            if member_result['matched']:
                enhanced['suggested_member_id'] = member_result['corrected']
                enhanced['suggested_member_name'] = member_result['member_name']
        
        # Correct book ID
        if row_data.get('book_id'):
            book_result = self.correct_book_id(
                row_data['book_id'],
                row_data.get('confidence', 0)
            )
            enhanced['ai_corrections']['book'] = book_result
            
            if book_result['matched']:
                enhanced['suggested_book_id'] = book_result['corrected']
                enhanced['suggested_book_title'] = book_result['book_title']
        
        # Try to extract from raw text if fields are missing
        if not row_data.get('member_id') and row_data.get('raw_text'):
            extracted = self._extract_from_raw_text(row_data['raw_text'])
            if extracted.get('member_id'):
                member_result = self.correct_member_id(extracted['member_id'])
                enhanced['ai_corrections']['member_from_text'] = member_result
                if member_result['matched']:
                    enhanced['suggested_member_id'] = member_result['corrected']
                    enhanced['suggested_member_name'] = member_result['member_name']
        
        # Calculate overall AI confidence
        confidences = []
        if enhanced['ai_corrections'].get('member', {}).get('confidence'):
            confidences.append(enhanced['ai_corrections']['member']['confidence'])
        if enhanced['ai_corrections'].get('book', {}).get('confidence'):
            confidences.append(enhanced['ai_corrections']['book']['confidence'])
        
        enhanced['ai_confidence'] = sum(confidences) / len(confidences) if confidences else 0.0
        enhanced['ai_auto_fill'] = enhanced['ai_confidence'] > 0.85
        
        return enhanced
    
    def _extract_from_raw_text(self, raw_text: str) -> Dict:
        """Extract potential IDs from raw OCR text using patterns"""
        result = {}
        
        # Student ID patterns
        patterns = [
            r'\b(STU\d{3,})\b',           # STU001, STU002, etc.
            r'\b([A-Z]{2,3}\d{3,})\b',    # ABC123, AB1234
            r'\b(\d{4,})\b',               # Pure numbers
        ]
        
        for pattern in patterns:
            match = re.search(pattern, raw_text.upper())
            if match:
                result['member_id'] = match.group(1)
                break
        
        # Book accession patterns
        book_patterns = [
            r'\b(ACC[-/]?\d+)\b',
            r'\b(B\d{4,})\b',
            r'\b(\d{4,6})\b',
        ]
        
        for pattern in book_patterns:
            match = re.search(pattern, raw_text.upper())
            if match and match.group(1) != result.get('member_id'):
                result['book_id'] = match.group(1)
                break
        
        return result
    
    def get_all_suggestions(self, partial_text: str, field_type: str = 'member') -> List[Dict]:
        """
        Get all suggestions for autocomplete.
        
        Args:
            partial_text: Partial text to match
            field_type: 'member' or 'book'
        
        Returns:
            List of suggestions with id, name/title, and similarity score
        """
        if not self.member_cache:
            self.load_database_cache()
        
        partial = partial_text.strip().upper()
        suggestions = []
        
        if field_type == 'member':
            # Match by ID prefix
            for member_id, member in self.member_cache.items():
                if member_id.startswith(partial) or partial in member_id:
                    suggestions.append({
                        'id': member_id,
                        'name': member.full_name,
                        'class': member.class_group,
                        'similarity': 1.0 if member_id.startswith(partial) else 0.8
                    })
            
            # Also match by name
            for name, member_id in self.name_cache.items():
                if partial.lower() in name:
                    member = self.member_cache[member_id]
                    if not any(s['id'] == member_id for s in suggestions):
                        suggestions.append({
                            'id': member_id,
                            'name': member.full_name,
                            'class': member.class_group,
                            'similarity': 0.7
                        })
        
        elif field_type == 'book':
            for accession, copy in self.book_cache.items():
                if accession.startswith(partial) or partial in accession:
                    suggestions.append({
                        'id': accession,
                        'title': copy.book.title,
                        'author': copy.book.author,
                        'similarity': 1.0 if accession.startswith(partial) else 0.8
                    })
        
        # Sort by similarity
        suggestions.sort(key=lambda x: x['similarity'], reverse=True)
        return suggestions[:10]


# Singleton instance
_correction_service = None

def get_correction_service() -> OCRCorrectionService:
    """Get singleton correction service instance"""
    global _correction_service
    if _correction_service is None:
        _correction_service = OCRCorrectionService()
    return _correction_service
