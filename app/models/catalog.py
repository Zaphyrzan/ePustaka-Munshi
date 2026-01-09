"""
Catalog models - Book and BookCopy (inventory)
"""
from datetime import datetime
from enum import Enum
from app import db


class CopyStatus(Enum):
    """Status of a physical book copy"""
    AVAILABLE = 'available'
    ON_LOAN = 'on_loan'
    RESERVED = 'reserved'
    LOST = 'lost'
    DAMAGED = 'damaged'
    PROCESSING = 'processing'
    WITHDRAWN = 'withdrawn'


class Book(db.Model):
    """Bibliographic record (title-level)"""
    __tablename__ = 'books'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Core bibliographic data
    title = db.Column(db.String(256), nullable=False, index=True)
    author = db.Column(db.String(256), index=True)
    isbn = db.Column(db.String(20), index=True)
    publisher = db.Column(db.String(128))
    publication_year = db.Column(db.Integer)
    edition = db.Column(db.String(32))
    
    # Classification
    category = db.Column(db.String(64), index=True)  # e.g., Fiction, Science, History
    call_number = db.Column(db.String(32), index=True)  # Library classification
    subject = db.Column(db.String(128))
    language = db.Column(db.String(32), default='Malay')
    
    # Additional info
    description = db.Column(db.Text)
    page_count = db.Column(db.Integer)
    cover_image = db.Column(db.String(256))  # Path to cover image
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    copies = db.relationship('BookCopy', backref='book', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Book {self.id}: {self.title[:50]}>'
    
    @property
    def total_copies(self):
        """Total number of copies"""
        return self.copies.count()
    
    @property
    def available_copies(self):
        """Number of available copies"""
        return self.copies.filter(BookCopy.status == CopyStatus.AVAILABLE.value).count()
    
    @property
    def is_available(self):
        """Check if any copy is available"""
        return self.available_copies > 0
    
    def to_dict(self, include_copies=False):
        """Convert to dictionary for API responses"""
        data = {
            'id': self.id,
            'title': self.title,
            'author': self.author,
            'isbn': self.isbn,
            'publisher': self.publisher,
            'publication_year': self.publication_year,
            'category': self.category,
            'call_number': self.call_number,
            'language': self.language,
            'total_copies': self.total_copies,
            'available_copies': self.available_copies,
            'is_available': self.is_available
        }
        if include_copies:
            data['copies'] = [copy.to_dict() for copy in self.copies.all()]
        return data


class BookCopy(db.Model):
    """Physical copy of a book (item-level)"""
    __tablename__ = 'book_copies'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Identification
    accession_number = db.Column(db.String(32), unique=True, nullable=False, index=True)
    barcode = db.Column(db.String(32), unique=True, index=True)
    
    # Status
    status = db.Column(db.String(20), default=CopyStatus.AVAILABLE.value, index=True)
    condition = db.Column(db.String(32), default='Good')  # Good, Fair, Poor
    location = db.Column(db.String(64))  # Shelf location
    
    # Acquisition info
    acquisition_date = db.Column(db.Date)
    acquisition_source = db.Column(db.String(64))  # Purchase, Donation, etc.
    price = db.Column(db.Float)
    
    notes = db.Column(db.Text)
    
    # Foreign key
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    loans = db.relationship('Loan', backref='copy', lazy='dynamic')
    
    def __repr__(self):
        return f'<BookCopy {self.accession_number}>'
    
    @property
    def is_available(self):
        """Check if copy is available for loan"""
        return self.status == CopyStatus.AVAILABLE.value
    
    @property
    def current_loan(self):
        """Get current active loan if any"""
        from app.models.circulation import Loan, LoanStatus
        return self.loans.filter(
            Loan.status.in_([LoanStatus.ACTIVE.value, LoanStatus.OVERDUE.value])
        ).first()
    
    def set_status(self, status):
        """Update copy status"""
        if isinstance(status, CopyStatus):
            self.status = status.value
        else:
            self.status = status
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'accession_number': self.accession_number,
            'barcode': self.barcode,
            'status': self.status,
            'condition': self.condition,
            'location': self.location,
            'book_id': self.book_id,
            'book_title': self.book.title if self.book else None,
            'is_available': self.is_available
        }
