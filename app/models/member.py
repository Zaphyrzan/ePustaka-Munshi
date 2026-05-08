"""
Member model - Library members (students/borrowers)
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db


def generate_member_id():
    """
    Generate a unique member ID (auto-increment style).
    Queries all existing member_ids to find the highest numeric value,
    then increments it. This ensures no duplicate IDs even if records are deleted.
    Format: STU0001, STU0002, STU0003, etc.
    """
    try:
        # Fetch all members and their IDs from the database
        all_members = Member.query.with_entities(Member.member_id).all()
        
        if not all_members:
            # If no members exist, start with 1
            next_number = 1
        else:
            # Extract numeric part from all member_ids and find the maximum
            max_number = 0
            for (member_id,) in all_members:
                try:
                    # Remove 'STU' prefix and convert to integer
                    numeric_part = int(member_id.replace('STU', ''))
                    max_number = max(max_number, numeric_part)
                except (ValueError, AttributeError, TypeError):
                    # Skip invalid member_ids and continue
                    continue
            
            # Increment the maximum found number
            next_number = max_number + 1
    except Exception as e:
        # Fallback: if any error occurs during lookup, start from 1
        print(f"Error generating member ID: {e}")
        next_number = 1
    
    # Format the ID as STU followed by 4-digit zero-padded number
    return f'STU{next_number:04d}'


class Member(UserMixin, db.Model):
    """Library members who can borrow books"""
    __tablename__ = 'members'
    
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.String(32), unique=True, nullable=False, index=True)  # Auto-generated, e.g., STU0001
    full_name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(120), index=True)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(256))  # Password for member login
    
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
        return (self.form_level or 0) >= 6
    
    @property
    def form_name(self):
        """Get human-readable form name"""
        if not self.form_level:
            return 'Unknown'

        if self.form_level == 6:
            return 'Graduated'
        return f'Form {self.form_level}' if self.form_level <= 5 else 'Unknown'
    
    @property
    def can_borrow(self):
        """Check if member can borrow more books"""
        from flask import current_app
        max_loans = current_app.config.get('MAX_LOANS_PER_MEMBER', 5)
        return self.is_active and self.active_loans_count < max_loans and self.overdue_loans_count == 0
    
    def set_password(self, password):
        """Hash and set the password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password against hash"""
        return check_password_hash(self.password_hash, password) if self.password_hash else False
    
    def get_id(self):
        """Return user ID for Flask-Login (prefixed with 'member_')"""
        return f'member_{self.id}'
    
    def can(self, perm):
        """Check if member can perform an action"""
        from app.models.user import Permission
        # Regular students have no special permissions
        if self.member_type == 'Student':
            return False
        # Staff members can do checkout/return/view catalog/search
        # Student Assistants also manage the catalog.
        if self.member_type in ['Staff', 'Student Assistant', 'Librarian', 'Teacher']:
            allowed = [Permission.CHECKOUT, Permission.RETURN, Permission.VIEW_CATALOG, Permission.SEARCH]
            if self.member_type == 'Student Assistant':
                allowed.append(Permission.MANAGE_CATALOG)
            return perm in allowed
        return False
    
    @property
    def role(self):
        """Return dummy role object for sidebar compatibility"""
        class DummyRole:
            def __init__(self, member_type):
                # Map common member_type values to role names used by
                # the staff `Role` model so templates and permission
                # checks behave consistently for staff-like members.
                staff_like = ['Librarian', 'Admin', 'Staff', 'Teacher', 'Student Assistant']
                if member_type == 'Student' or not member_type:
                    self.name = 'Student'
                elif member_type in staff_like:
                    # Preserve the explicit staff type when possible
                    # (e.g., 'Librarian' -> 'Librarian') so UI/permissions
                    # match expectations.
                    self.name = member_type
                else:
                    # Fallback: treat unknown types as student assistant
                    self.name = 'Student Assistant'
        
        return DummyRole(self.member_type)
    
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
