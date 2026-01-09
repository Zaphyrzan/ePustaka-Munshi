"""
Member model - Library members (students/borrowers)
"""
from datetime import datetime
from app import db


class Member(db.Model):
    """Library members who can borrow books"""
    __tablename__ = 'members'
    
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.String(32), unique=True, nullable=False, index=True)  # Student ID / Card No.
    full_name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(120), index=True)
    phone = db.Column(db.String(20))
    
    # Member classification
    member_type = db.Column(db.String(32), default='Student')  # Student, Staff, External
    class_group = db.Column(db.String(64))  # e.g., "Form 5 Science 1"
    student_year = db.Column(db.Integer)  # 1-6 for Form 1-6 / Year 1-6
    
    # NILAM tracking
    total_books_read = db.Column(db.Integer, default=0)  # For NILAM leaderboard
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    loans = db.relationship('Loan', backref='member', lazy='dynamic')
    
    def __repr__(self):
        return f'<Member {self.member_id}: {self.full_name}>'
    
    @property
    def active_loans_count(self):
        """Count of currently active loans"""
        from app.models.circulation import Loan, LoanStatus
        return self.loans.filter(Loan.status == LoanStatus.ACTIVE.value).count()
    
    @property
    def overdue_loans_count(self):
        """Count of overdue loans"""
        from app.models.circulation import Loan, LoanStatus
        return self.loans.filter(Loan.status == LoanStatus.OVERDUE.value).count()
    
    @property
    def is_staff(self):
        """Check if member is staff (Staff, Teacher, Librarian, etc.) - cannot borrow"""
        staff_types = ['Staff', 'Teacher', 'Librarian', 'Admin', 'Student Assistant']
        return self.member_type in staff_types
    
    @property
    def can_borrow(self):
        """Check if member can borrow more books. Staff cannot borrow."""
        from flask import current_app
        # Staff members cannot borrow
        if self.is_staff:
            return False
        max_loans = current_app.config.get('MAX_LOANS_PER_MEMBER', 5)
        return self.is_active and self.active_loans_count < max_loans and self.overdue_loans_count == 0
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'member_id': self.member_id,
            'full_name': self.full_name,
            'email': self.email,
            'phone': self.phone,
            'member_type': self.member_type,
            'class_group': self.class_group,
            'student_year': self.student_year,
            'total_books_read': self.total_books_read,
            'is_active': self.is_active,
            'active_loans': self.active_loans_count,
            'overdue_loans': self.overdue_loans_count,
            'can_borrow': self.can_borrow
        }
