"""
Circulation models - Loan (borrow/return transactions)
"""
from datetime import datetime, timedelta
from enum import Enum
from flask import current_app
from app import db


class LoanStatus(Enum):
    """Status of a loan transaction"""
    ACTIVE = 'active'
    RETURNED = 'returned'
    OVERDUE = 'overdue'
    LOST = 'lost'
    RENEWED = 'renewed'


class Loan(db.Model):
    """Loan transaction (checkout/return record)"""
    __tablename__ = 'loans'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Core transaction data
    checkout_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=False)
    return_date = db.Column(db.DateTime)
    
    # Status tracking
    status = db.Column(db.String(20), default=LoanStatus.ACTIVE.value, index=True)
    renewal_count = db.Column(db.Integer, default=0)
    
    # Fine handling (future expansion)
    fine_amount = db.Column(db.Float, default=0.0)
    fine_paid = db.Column(db.Boolean, default=False)
    
    notes = db.Column(db.Text)
    
    # Foreign keys
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    copy_id = db.Column(db.Integer, db.ForeignKey('book_copies.id'), nullable=False)
    
    # Staff who processed the transaction
    checkout_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    return_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    checkout_staff = db.relationship('User', foreign_keys=[checkout_by])
    return_staff = db.relationship('User', foreign_keys=[return_by])
    
    def __repr__(self):
        return f'<Loan {self.id}: {self.copy.accession_number} -> {self.member.member_id}>'
    
    @property
    def is_overdue(self):
        """Check if loan is overdue"""
        if self.status == LoanStatus.RETURNED.value:
            return False
        return datetime.utcnow() > self.due_date
    
    @property
    def days_overdue(self):
        """Calculate days overdue (0 if not overdue)"""
        if not self.is_overdue:
            return 0
        delta = datetime.utcnow() - self.due_date
        return delta.days
    
    @property
    def can_renew(self):
        """Check if loan can be renewed"""
        max_renewals = current_app.config.get('MAX_RENEWALS', 2)
        return (
            self.status == LoanStatus.ACTIVE.value and
            self.renewal_count < max_renewals
        )

    def renew(self, days=None):
        """Renew the loan"""
        if not self.can_renew:
            return False

        if days is None:
            days = current_app.config.get('RENEWAL_LOAN_DAYS', 7)

        # Overdue loans extend from today so the member gets the full period
        base = datetime.utcnow() if self.is_overdue else self.due_date
        self.due_date = base + timedelta(days=days)
        self.renewal_count += 1
        self.updated_at = datetime.utcnow()
        return True
    
    def process_return(self, user_id=None):
        """Process book return"""
        from app.models.catalog import BookCopy, CopyStatus
        
        self.return_date = datetime.utcnow()
        self.status = LoanStatus.RETURNED.value
        self.return_by = user_id
        
        # Update copy status
        copy = BookCopy.query.get(self.copy_id)
        if copy:
            copy.set_status(CopyStatus.AVAILABLE)
        
        self.updated_at = datetime.utcnow()
        return True
    
    @staticmethod
    def create_checkout(member_id, copy_id, user_id=None, loan_days=None):
        """Create a new checkout transaction"""
        from app.models.catalog import BookCopy, CopyStatus
        
        if loan_days is None:
            loan_days = current_app.config.get('DEFAULT_LOAN_DAYS', 7)
        
        checkout_date = datetime.utcnow()
        due_date = checkout_date + timedelta(days=loan_days)
        
        loan = Loan(
            member_id=member_id,
            copy_id=copy_id,
            checkout_date=checkout_date,
            due_date=due_date,
            status=LoanStatus.ACTIVE.value,
            checkout_by=user_id
        )
        
        # Update copy status
        copy = BookCopy.query.get(copy_id)
        if copy:
            copy.set_status(CopyStatus.ON_LOAN)
        
        db.session.add(loan)
        return loan
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'member_id': self.member_id,
            'member_name': self.member.full_name if self.member else None,
            'member_card': self.member.member_id if self.member else None,
            'copy_id': self.copy_id,
            'accession_number': self.copy.accession_number if self.copy else None,
            'book_title': self.copy.book.title if self.copy and self.copy.book else None,
            'checkout_date': self.checkout_date.isoformat() if self.checkout_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'return_date': self.return_date.isoformat() if self.return_date else None,
            'status': self.status,
            'is_overdue': self.is_overdue,
            'days_overdue': self.days_overdue,
            'renewal_count': self.renewal_count,
            'can_renew': self.can_renew
        }
