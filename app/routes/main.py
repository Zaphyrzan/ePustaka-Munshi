"""
Main routes - Dashboard and home
"""
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from sqlalchemy import func
from app import db
from app.models import Book, BookCopy, Member, Loan, LoanStatus, OCRJob
from app.utils.cache_utils import cache_query

main_bp = Blueprint('main', __name__)


@cache_query(ttl_seconds=300)
def get_dashboard_stats():
    """
    Get dashboard statistics using optimized queries.
    Results cached for 5 minutes.
    """
    return {
        'total_books': Book.query.count(),
        'total_copies': BookCopy.query.count(),
        'available_copies': BookCopy.query.filter_by(status='available').count(),
        'total_members': Member.query.filter_by(is_active=True).count(),
        'active_loans': Loan.query.filter_by(status=LoanStatus.ACTIVE.value).count(),
        'overdue_loans': Loan.query.filter_by(status=LoanStatus.OVERDUE.value).count(),
        'pending_ocr_jobs': OCRJob.query.filter_by(status='pending').count()
    }


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
    
    # Get cached stats
    stats = get_dashboard_stats()
    
    # Get recent loans with eager loading to avoid N+1 queries
    # joinedload() ensures copy, book, member, and staff are fetched in one query
    recent_loans = (
        Loan.query
        .options(
            joinedload(Loan.copy).joinedload(BookCopy.book),
            joinedload(Loan.member),
            joinedload(Loan.checkout_staff),
            joinedload(Loan.return_staff)
        )
        .order_by(Loan.checkout_date.desc())
        .limit(15)
        .all()
    )
    
    # Get overdue loans with eager loading
    overdue_loans = (
        Loan.query
        .options(
            joinedload(Loan.copy).joinedload(BookCopy.book),
            joinedload(Loan.member)
        )
        .filter_by(status=LoanStatus.OVERDUE.value)
        .limit(10)
        .all()
    )
    
    # Prepare activity data with staff handler information
    # No additional queries needed - all data already eager loaded
    activity = []
    for loan in recent_loans:
        activity.append({
            'type': 'checkout',
            'date': loan.checkout_date,
            'book': loan.copy.book.title,
            'member': loan.member.full_name,
            'staff_name': loan.checkout_staff.full_name if loan.checkout_staff else 'System',
            'status': loan.status,
            'is_overdue': loan.is_overdue
        })
        if loan.return_date:
            activity.append({
                'type': 'return',
                'date': loan.return_date,
                'book': loan.copy.book.title,
                'member': loan.member.full_name,
                'staff_name': loan.return_staff.full_name if loan.return_staff else 'System',
                'status': 'returned',
                'is_overdue': False
            })
    
    # Sort activity by date (most recent first) and limit to 15
    activity.sort(key=lambda x: x['date'], reverse=True)
    activity = activity[:15]
    
    return render_template('dashboard.html', 
                          stats=stats, 
                          recent_loans=recent_loans,
                          activity=activity,
                          overdue_loans=overdue_loans)
