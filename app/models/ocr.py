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
    """Extracted record from OCR (staged for review before commit)
    
    Matches Malaysian library ledger format:
    No Perolehan | No Panggilan | Pengarang | Tajuk Buku | Tempat & Nama Penerbit | 
    Tarikh Penerbit | Tarikh Perolehan | Bil. No. | Punca | Harga RM Sen | Muka Surat | Catatan
    """
    __tablename__ = 'ocr_results'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Source reference
    job_id = db.Column(db.Integer, db.ForeignKey('ocr_jobs.id'), nullable=False)
    page_number = db.Column(db.Integer, default=1)
    row_number = db.Column(db.Integer)  # Row in the ledger table
    
    # Raw extracted text (full row)
    raw_text = db.Column(db.Text)
    
    # ============================================
    # Malaysian Ledger Fields - Extracted by OCR
    # ============================================
    
    # No Perolehan (Accession/Acquisition Number)
    no_perolehan_extracted = db.Column(db.String(64))
    no_perolehan_corrected = db.Column(db.String(64))
    
    # No Panggilan (Call Number)
    no_panggilan_extracted = db.Column(db.String(64))
    no_panggilan_corrected = db.Column(db.String(64))
    
    # Pengarang (Author)
    pengarang_extracted = db.Column(db.String(256))
    pengarang_corrected = db.Column(db.String(256))
    
    # Tajuk Buku (Book Title)
    tajuk_buku_extracted = db.Column(db.String(512))
    tajuk_buku_corrected = db.Column(db.String(512))
    
    # Tempat dan Nama Penerbit (Publisher Place & Name)
    penerbit_extracted = db.Column(db.String(256))
    penerbit_corrected = db.Column(db.String(256))
    
    # Tarikh Penerbit (Publication Date/Year)
    tarikh_penerbit_extracted = db.Column(db.String(64))
    tarikh_penerbit_corrected = db.Column(db.String(64))
    
    # Tarikh Perolehan (Acquisition Date)
    tarikh_perolehan_extracted = db.Column(db.String(64))
    tarikh_perolehan_corrected = db.Column(db.Date)
    
    # Bil. No. (Bill Number)
    bil_no_extracted = db.Column(db.String(64))
    bil_no_corrected = db.Column(db.String(64))
    
    # Punca (Source/Origin)
    punca_extracted = db.Column(db.String(128))
    punca_corrected = db.Column(db.String(128))
    
    # Harga (Price in RM and Sen)
    harga_rm_extracted = db.Column(db.String(32))
    harga_sen_extracted = db.Column(db.String(32))
    harga_rm_corrected = db.Column(db.Numeric(10, 2))
    
    # Muka Surat (Page Count)
    muka_surat_extracted = db.Column(db.String(32))
    muka_surat_corrected = db.Column(db.Integer)
    
    # Catatan (Notes/Remarks)
    catatan_extracted = db.Column(db.Text)
    catatan_corrected = db.Column(db.Text)
    
    # ============================================
    # Confidence scores (0.0 - 1.0)
    # ============================================
    confidence_overall = db.Column(db.Float, default=0.0)
    confidence_no_perolehan = db.Column(db.Float)
    confidence_tajuk = db.Column(db.Float)
    confidence_pengarang = db.Column(db.Float)
    
    # Bounding box (for UI highlighting)
    bbox_json = db.Column(db.Text)  # JSON: {x, y, width, height}
    
    # Review status
    is_reviewed = db.Column(db.Boolean, default=False)
    is_valid = db.Column(db.Boolean)  # True=valid, False=invalid/skip, None=pending
    review_notes = db.Column(db.Text)  # AI suggestions and corrections
    
    # Link to committed record (after commit to digitized ledger)
    committed_ledger_id = db.Column(db.Integer, db.ForeignKey('digitized_ledger.id'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<OCRResult {self.id}: Job {self.job_id} Row {self.row_number}>'
    
    # ============================================
    # Final value properties (corrected or extracted)
    # ============================================
    
    @property
    def final_no_perolehan(self):
        """Get the final accession number (corrected or extracted)"""
        return self.no_perolehan_corrected or self.no_perolehan_extracted
    
    @property
    def final_no_panggilan(self):
        """Get the final call number (corrected or extracted)"""
        return self.no_panggilan_corrected or self.no_panggilan_extracted
    
    @property
    def final_pengarang(self):
        """Get the final author (corrected or extracted)"""
        return self.pengarang_corrected or self.pengarang_extracted
    
    @property
    def final_tajuk_buku(self):
        """Get the final title (corrected or extracted)"""
        return self.tajuk_buku_corrected or self.tajuk_buku_extracted
    
    @property
    def final_penerbit(self):
        """Get the final publisher (corrected or extracted)"""
        return self.penerbit_corrected or self.penerbit_extracted
    
    @property
    def final_tarikh_penerbit(self):
        """Get the final publication date (corrected or extracted)"""
        return self.tarikh_penerbit_corrected or self.tarikh_penerbit_extracted
    
    @property
    def final_tarikh_perolehan(self):
        """Get the final acquisition date (corrected or extracted as date)"""
        if self.tarikh_perolehan_corrected:
            return self.tarikh_perolehan_corrected
        # Try to parse the extracted date
        if self.tarikh_perolehan_extracted:
            try:
                from datetime import datetime
                for fmt in ['%Y', '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']:
                    try:
                        return datetime.strptime(self.tarikh_perolehan_extracted.strip(), fmt).date()
                    except:
                        continue
            except:
                pass
        return None
    
    @property
    def final_bil_no(self):
        """Get the final bill number (corrected or extracted)"""
        return self.bil_no_corrected or self.bil_no_extracted
    
    @property
    def final_punca(self):
        """Get the final source (corrected or extracted)"""
        return self.punca_corrected or self.punca_extracted
    
    @property
    def final_harga(self):
        """Get the final price (corrected or calculated from extracted)"""
        if self.harga_rm_corrected:
            return float(self.harga_rm_corrected)
        try:
            rm = float(self.harga_rm_extracted or 0)
            sen = float(self.harga_sen_extracted or 0) / 100
            return rm + sen
        except:
            return None
    
    @property
    def final_muka_surat(self):
        """Get the final page count (corrected or extracted)"""
        if self.muka_surat_corrected:
            return self.muka_surat_corrected
        try:
            return int(self.muka_surat_extracted) if self.muka_surat_extracted else None
        except:
            return None
    
    @property
    def final_catatan(self):
        """Get the final notes (corrected or extracted)"""
        return self.catatan_corrected or self.catatan_extracted
    
    def mark_reviewed(self, is_valid, corrections=None, notes=None):
        """Mark result as reviewed with optional corrections"""
        self.is_reviewed = True
        self.is_valid = is_valid
        self.reviewed_at = datetime.utcnow()
        
        if corrections:
            # Map correction fields to model fields
            field_mapping = {
                'no_perolehan': 'no_perolehan_corrected',
                'no_panggilan': 'no_panggilan_corrected',
                'pengarang': 'pengarang_corrected',
                'tajuk_buku': 'tajuk_buku_corrected',
                'penerbit': 'penerbit_corrected',
                'tarikh_penerbit': 'tarikh_penerbit_corrected',
                'tarikh_perolehan': 'tarikh_perolehan_corrected',
                'bil_no': 'bil_no_corrected',
                'punca': 'punca_corrected',
                'harga': 'harga_rm_corrected',
                'muka_surat': 'muka_surat_corrected',
                'catatan': 'catatan_corrected',
            }
            
            for key, attr in field_mapping.items():
                if key in corrections and corrections[key]:
                    setattr(self, attr, corrections[key])
        
        if notes:
            self.review_notes = notes
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'page_number': self.page_number,
            'row_number': self.row_number,
            'raw_text': self.raw_text,
            # Extracted values
            'no_perolehan_extracted': self.no_perolehan_extracted,
            'no_panggilan_extracted': self.no_panggilan_extracted,
            'pengarang_extracted': self.pengarang_extracted,
            'tajuk_buku_extracted': self.tajuk_buku_extracted,
            'penerbit_extracted': self.penerbit_extracted,
            'tarikh_penerbit_extracted': self.tarikh_penerbit_extracted,
            'tarikh_perolehan_extracted': self.tarikh_perolehan_extracted,
            'bil_no_extracted': self.bil_no_extracted,
            'punca_extracted': self.punca_extracted,
            'harga_rm_extracted': self.harga_rm_extracted,
            'harga_sen_extracted': self.harga_sen_extracted,
            'muka_surat_extracted': self.muka_surat_extracted,
            'catatan_extracted': self.catatan_extracted,
            # Final values
            'no_perolehan': self.final_no_perolehan,
            'no_panggilan': self.final_no_panggilan,
            'pengarang': self.final_pengarang,
            'tajuk_buku': self.final_tajuk_buku,
            'penerbit': self.final_penerbit,
            'tarikh_penerbit': self.final_tarikh_penerbit,
            'tarikh_perolehan': self.final_tarikh_perolehan.isoformat() if self.final_tarikh_perolehan else None,
            'bil_no': self.final_bil_no,
            'punca': self.final_punca,
            'harga': self.final_harga,
            'muka_surat': self.final_muka_surat,
            'catatan': self.final_catatan,
            # Status
            'confidence_overall': self.confidence_overall,
            'is_reviewed': self.is_reviewed,
            'is_valid': self.is_valid,
            'review_notes': self.review_notes
        }


class DigitizedLedger(db.Model):
    """
    Final digitized ledger entries - committed from OCR results.
    
    This table stores the validated and committed book acquisition records
    matching the Malaysian library ledger format.
    """
    __tablename__ = 'digitized_ledger'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Source tracking
    source_job_id = db.Column(db.Integer, db.ForeignKey('ocr_jobs.id'))
    source_result_id = db.Column(db.Integer, db.ForeignKey('ocr_results.id'))
    
    # ============================================
    # Malaysian Ledger Fields
    # ============================================
    
    # No Perolehan (Accession/Acquisition Number) - Primary identifier
    no_perolehan = db.Column(db.String(64), unique=True, nullable=False, index=True)
    
    # No Panggilan (Call Number)
    no_panggilan = db.Column(db.String(64), index=True)
    
    # Pengarang (Author)
    pengarang = db.Column(db.String(256), index=True)
    
    # Tajuk Buku (Book Title)
    tajuk_buku = db.Column(db.String(512), nullable=False, index=True)
    
    # Tempat dan Nama Penerbit (Publisher Place & Name)
    penerbit = db.Column(db.String(256))
    
    # Tarikh Penerbit (Publication Date/Year)
    tarikh_penerbit = db.Column(db.String(64))
    
    # Tarikh Perolehan (Acquisition Date)
    tarikh_perolehan = db.Column(db.Date, index=True)
    
    # Bil. No. (Bill Number)
    bil_no = db.Column(db.String(64))
    
    # Punca (Source/Origin)
    punca = db.Column(db.String(128))
    
    # Harga (Price in RM)
    harga = db.Column(db.Numeric(10, 2))
    
    # Muka Surat (Page Count)
    muka_surat = db.Column(db.Integer)
    
    # Catatan (Notes/Remarks)
    catatan = db.Column(db.Text)
    
    # ============================================
    # Link to Book Catalog (optional)
    # ============================================
    linked_book_id = db.Column(db.Integer, db.ForeignKey('books.id'))
    linked_copy_id = db.Column(db.Integer, db.ForeignKey('book_copies.id'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    source_job = db.relationship('OCRJob', foreign_keys=[source_job_id])
    linked_book = db.relationship('Book', foreign_keys=[linked_book_id])
    linked_copy = db.relationship('BookCopy', foreign_keys=[linked_copy_id])
    creator = db.relationship('User', foreign_keys=[created_by])
    
    def __repr__(self):
        return f'<DigitizedLedger {self.no_perolehan}: {self.tajuk_buku[:30]}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'no_perolehan': self.no_perolehan,
            'no_panggilan': self.no_panggilan,
            'pengarang': self.pengarang,
            'tajuk_buku': self.tajuk_buku,
            'penerbit': self.penerbit,
            'tarikh_penerbit': self.tarikh_penerbit,
            'tarikh_perolehan': self.tarikh_perolehan.isoformat() if self.tarikh_perolehan else None,
            'bil_no': self.bil_no,
            'punca': self.punca,
            'harga': float(self.harga) if self.harga else None,
            'muka_surat': self.muka_surat,
            'catatan': self.catatan,
            'linked_book_id': self.linked_book_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
