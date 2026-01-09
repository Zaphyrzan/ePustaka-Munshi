"""
OCR models - Job queue and staged results for ledger digitization
"""
from datetime import datetime
from enum import Enum
from app import db


class OCRJobStatus(Enum):
    """Status of an OCR processing job"""
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    REVIEWED = 'reviewed'
    COMMITTED = 'committed'


class OCRJob(db.Model):
    """OCR processing job for scanned documents"""
    __tablename__ = 'ocr_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Job identification
    job_name = db.Column(db.String(128), nullable=False)
    source_type = db.Column(db.String(32), default='file_upload')  # file_upload, scanner, watched_folder
    
    # Source file(s)
    source_path = db.Column(db.String(512), nullable=False)
    original_filename = db.Column(db.String(256))
    page_count = db.Column(db.Integer, default=1)
    
    # Processing status
    status = db.Column(db.String(20), default=OCRJobStatus.PENDING.value, index=True)
    progress = db.Column(db.Integer, default=0)  # 0-100%
    error_message = db.Column(db.Text)
    
    # OCR settings used
    ocr_language = db.Column(db.String(32), default='eng+msa')  # Tesseract language codes
    ocr_config = db.Column(db.Text)  # JSON config
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    reviewed_at = db.Column(db.DateTime)
    committed_at = db.Column(db.DateTime)
    
    # User tracking
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    results = db.relationship('OCRResult', backref='job', lazy='dynamic', cascade='all, delete-orphan')
    creator = db.relationship('User', foreign_keys=[created_by])
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])
    
    def __repr__(self):
        return f'<OCRJob {self.id}: {self.job_name}>'
    
    @property
    def result_count(self):
        """Number of extracted results"""
        return self.results.count()
    
    @property
    def reviewed_count(self):
        """Number of reviewed/validated results"""
        return self.results.filter(OCRResult.is_reviewed == True).count()
    
    @property
    def pending_review_count(self):
        """Number of results pending review"""
        return self.results.filter(OCRResult.is_reviewed == False).count()
    
    def mark_processing(self):
        """Mark job as processing"""
        self.status = OCRJobStatus.PROCESSING.value
        self.started_at = datetime.utcnow()
    
    def mark_completed(self):
        """Mark job as completed"""
        self.status = OCRJobStatus.COMPLETED.value
        self.completed_at = datetime.utcnow()
        self.progress = 100
    
    def mark_failed(self, error_message):
        """Mark job as failed"""
        self.status = OCRJobStatus.FAILED.value
        self.error_message = error_message
    
    def mark_reviewed(self, user_id):
        """Mark job as reviewed"""
        self.status = OCRJobStatus.REVIEWED.value
        self.reviewed_at = datetime.utcnow()
        self.reviewed_by = user_id
    
    def mark_committed(self):
        """Mark job as committed to main records"""
        self.status = OCRJobStatus.COMMITTED.value
        self.committed_at = datetime.utcnow()
    
    def to_dict(self, include_results=False):
        """Convert to dictionary for API responses"""
        data = {
            'id': self.id,
            'job_name': self.job_name,
            'source_type': self.source_type,
            'original_filename': self.original_filename,
            'page_count': self.page_count,
            'status': self.status,
            'progress': self.progress,
            'result_count': self.result_count,
            'reviewed_count': self.reviewed_count,
            'pending_review_count': self.pending_review_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
        if include_results:
            data['results'] = [r.to_dict() for r in self.results.all()]
        return data


class OCRResult(db.Model):
    """Extracted record from OCR (staged for review before commit)"""
    __tablename__ = 'ocr_results'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Source reference
    job_id = db.Column(db.Integer, db.ForeignKey('ocr_jobs.id'), nullable=False)
    page_number = db.Column(db.Integer, default=1)
    row_number = db.Column(db.Integer)  # Row in the ledger table
    
    # Raw extracted text
    raw_text = db.Column(db.Text)
    
    # Parsed fields (ledger columns)
    member_id_extracted = db.Column(db.String(64))
    member_name_extracted = db.Column(db.String(128))
    book_id_extracted = db.Column(db.String(64))  # Accession number
    book_title_extracted = db.Column(db.String(256))
    transaction_type = db.Column(db.String(32))  # borrow, return
    date_extracted = db.Column(db.String(64))  # Raw date string
    parsed_date = db.Column(db.Date)  # Parsed date
    
    # Confidence scores (0.0 - 1.0)
    confidence_overall = db.Column(db.Float, default=0.0)
    confidence_member = db.Column(db.Float)
    confidence_book = db.Column(db.Float)
    confidence_date = db.Column(db.Float)
    
    # Bounding box (for UI highlighting)
    bbox_json = db.Column(db.Text)  # JSON: {x, y, width, height}
    
    # Review status
    is_reviewed = db.Column(db.Boolean, default=False)
    is_valid = db.Column(db.Boolean)  # True=valid, False=invalid/skip, None=pending
    correction_notes = db.Column(db.Text)
    
    # Corrected values (after human review)
    member_id_corrected = db.Column(db.String(64))
    book_id_corrected = db.Column(db.String(64))
    date_corrected = db.Column(db.Date)
    
    # Link to committed record (after commit)
    committed_loan_id = db.Column(db.Integer, db.ForeignKey('loans.id'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<OCRResult {self.id}: Job {self.job_id} Row {self.row_number}>'
    
    @property
    def final_member_id(self):
        """Get the final member ID (corrected or extracted)"""
        return self.member_id_corrected or self.member_id_extracted
    
    @property
    def final_book_id(self):
        """Get the final book ID (corrected or extracted)"""
        return self.book_id_corrected or self.book_id_extracted
    
    @property
    def final_date(self):
        """Get the final date (corrected or parsed)"""
        return self.date_corrected or self.parsed_date
    
    def mark_reviewed(self, is_valid, corrections=None, notes=None):
        """Mark result as reviewed with optional corrections"""
        self.is_reviewed = True
        self.is_valid = is_valid
        self.reviewed_at = datetime.utcnow()
        
        if corrections:
            if 'member_id' in corrections:
                self.member_id_corrected = corrections['member_id']
            if 'book_id' in corrections:
                self.book_id_corrected = corrections['book_id']
            if 'date' in corrections:
                self.date_corrected = corrections['date']
        
        if notes:
            self.correction_notes = notes
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'page_number': self.page_number,
            'row_number': self.row_number,
            'raw_text': self.raw_text,
            'member_id_extracted': self.member_id_extracted,
            'member_name_extracted': self.member_name_extracted,
            'book_id_extracted': self.book_id_extracted,
            'book_title_extracted': self.book_title_extracted,
            'transaction_type': self.transaction_type,
            'date_extracted': self.date_extracted,
            'confidence_overall': self.confidence_overall,
            'is_reviewed': self.is_reviewed,
            'is_valid': self.is_valid,
            'final_member_id': self.final_member_id,
            'final_book_id': self.final_book_id,
            'final_date': self.final_date.isoformat() if self.final_date else None
        }
