"""
ePustaka-Munshi Models Package
All database models for the library management system
"""
from app.models.user import User, Role, Permission
from app.models.member import Member, ClassGroup
from app.models.catalog import Book, BookCopy, CopyStatus
from app.models.circulation import Loan, LoanStatus
from app.models.ocr import OCRJob, OCRResult, OCRJobStatus, DigitizedLedger

__all__ = [
    'User', 'Role', 'Permission',
    'Member', 'ClassGroup',
    'Book', 'BookCopy', 'CopyStatus',
    'Loan', 'LoanStatus',
    'OCRJob', 'OCRResult', 'OCRJobStatus', 'DigitizedLedger'
]
