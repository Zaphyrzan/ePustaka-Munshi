"""
Member model - Library members (students/borrowers)
"""
from datetime import datetime
from app import db


def generate_member_id():
    """Generate a unique member ID (auto-increment style)"""
    last_member = Member.query.order_by(Member.id.desc()).first()
    if last_member:
        # Extract number from last member_id and increment
        try:
            last_number = int(last_member.member_id.replace('STU', ''))
            next_number = last_number + 1
        except (ValueError, AttributeError):
            next_number = 1
    else:
        next_number = 1
    return f'STU{next_number:04d}'  # Format: STU0001, STU0002, etc.


class Member(db.Model):
    """Library members who can borrow books"""
    __tablename__ = 'members'
    
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.String(32), unique=True, nullable=False, index=True)  # Auto-generated, e.g., STU0001
    full_name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(120), index=True)
    phone = db.Column(db.String(20))
    
    # Member classification
    member_type = db.Column(db.String(32), default='Student')  # Student, Staff, External
    form_level = db.Column(db.Integer, default=1)  # 1-5 for Forms 1-5, 6 for Graduated
    class_group = db.Column(db.String(64))  # e.g., "Science 1", "Arts 2"
    student_year = db.Column(db.Integer)  # Academic year (e.g., 2024-2025)
    
    # NILAM tracking
    total_books_read = db.Column(db.Integer, default=0)  # For NILAM leaderboard
    
    # Status & graduation tracking
    is_active = db.Column(db.Boolean, default=True)
    mark_for_deletion = db.Column(db.Boolean, default=False)  # Flag for admin deletion
    graduation_date = db.Column(db.DateTime)  # When student graduated
    last_login = db.Column(db.DateTime)  # Track active students by login
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
    def is_graduated(self):
        """Check if student has graduated (Form 5 completed or form_level >= 6)"""
        return self.form_level >= 6
    
    @property
    def form_name(self):
        """Get human-readable form name"""
        if self.form_level == 6:
            return 'Graduated'
        return f'Form {self.form_level}' if self.form_level <= 5 else 'Unknown'
    
    @property
    def can_borrow(self):
        """Check if member can borrow more books"""
        from flask import current_app
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
            'form_level': self.form_level,
            'form_name': self.form_name,
            'class_group': self.class_group,
            'student_year': self.student_year,
            'total_books_read': self.total_books_read,
            'is_active': self.is_active,
            'is_graduated': self.is_graduated,
            'mark_for_deletion': self.mark_for_deletion,
            'active_loans': self.active_loans_count,
            'overdue_loans': self.overdue_loans_count,
            'can_borrow': self.can_borrow
        }
