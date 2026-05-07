"""
Main routes - Dashboard and home
"""
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models import Book, BookCopy, Member, Loan, LoanStatus, OCRJob

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Landing page - redirect to dashboard if logged in"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard with statistics - Staff/Librarian only"""
    # Redirect member (student) accounts to their portal only when
    # the logged-in identity is an actual Member record. This avoids
    # mis-classifying staff User objects that may have an unexpected
    # role name value.
    # If the logged-in identity is a Member record (has `member_id`) and
    # their `member_type` is a Student, send them to the student portal.
    # This avoids relying on role name strings for staff `User` objects.
    if hasattr(current_user, 'member_id'):
        if getattr(current_user, 'member_type', 'Student') == 'Student':
            return redirect(url_for('student.index'))
    
    stats = {
        'total_books': Book.query.count(),
        'total_copies': BookCopy.query.count(),
        'available_copies': BookCopy.query.filter_by(status='available').count(),
        'total_members': Member.query.filter_by(is_active=True).count(),
        'active_loans': Loan.query.filter_by(status=LoanStatus.ACTIVE.value).count(),
        'overdue_loans': Loan.query.filter_by(status=LoanStatus.OVERDUE.value).count(),
        'pending_ocr_jobs': OCRJob.query.filter_by(status='pending').count()
    }
    
    # Recent loans
    recent_loans = Loan.query.order_by(Loan.checkout_date.desc()).limit(10).all()
    
    # Overdue items
    overdue_loans = Loan.query.filter_by(status=LoanStatus.OVERDUE.value).limit(10).all()
    
    return render_template('dashboard.html', 
                          stats=stats, 
                          recent_loans=recent_loans,
                          overdue_loans=overdue_loans)
