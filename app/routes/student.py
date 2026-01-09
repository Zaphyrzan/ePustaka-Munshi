"""
Student Portal routes - Student-facing interface for library access
"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from app import db
from app.models import Book, BookCopy, CopyStatus, Member, Loan, LoanStatus

student_bp = Blueprint('student', __name__)


@student_bp.route('/')
@login_required
def index():
    """Student portal dashboard"""
    # Get member record linked to current user (if exists)
    member = Member.query.filter_by(member_id=current_user.username).first()
    
    # Stats for dashboard
    total_books = Book.query.count()
    available_copies = BookCopy.query.filter_by(status=CopyStatus.AVAILABLE.value).count()
    
    # Member-specific data
    my_loans = []
    due_soon = []
    overdue = []
    books_read = 0
    
    if member:
        # Get active loans
        my_loans = Loan.query.filter_by(
            member_id=member.id,
            status=LoanStatus.ACTIVE.value
        ).order_by(Loan.due_date).all()
        
        # Due in next 3 days
        three_days = datetime.utcnow() + timedelta(days=3)
        due_soon = [l for l in my_loans if l.due_date and l.due_date <= three_days]
        
        # Overdue
        overdue = Loan.query.filter_by(
            member_id=member.id,
            status=LoanStatus.OVERDUE.value
        ).all()
        
        books_read = member.total_books_read
    
    return render_template('student/index.html',
                          member=member,
                          total_books=total_books,
                          available_copies=available_copies,
                          my_loans=my_loans,
                          due_soon=due_soon,
                          overdue=overdue,
                          books_read=books_read)


@student_bp.route('/search')
@login_required
def search_books():
    """Search available books"""
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    query = Book.query
    
    # Search filters
    search = request.args.get('search', '').strip()
    if search:
        search_term = f'%{search}%'
        query = query.filter(
            db.or_(
                Book.title.ilike(search_term),
                Book.author.ilike(search_term),
                Book.isbn.ilike(search_term),
                Book.call_number.ilike(search_term)
            )
        )
    
    category = request.args.get('category', '')
    if category:
        query = query.filter(Book.category == category)
    
    # Only show available toggle
    show_available = request.args.get('available', '') == '1'
    
    # Get categories for filter
    categories = db.session.query(Book.category).distinct().filter(Book.category.isnot(None)).all()
    categories = [c[0] for c in categories if c[0]]
    
    books = query.order_by(Book.title).paginate(page=page, per_page=per_page)
    
    # Add availability info
    for book in books.items:
        book.available_count = book.copies.filter(
            BookCopy.status == CopyStatus.AVAILABLE.value
        ).count()
    
    return render_template('student/search.html',
                          books=books,
                          search=search,
                          category=category,
                          categories=categories,
                          show_available=show_available)


@student_bp.route('/book/<int:book_id>')
@login_required
def view_book(book_id):
    """View book details with availability"""
    book = Book.query.get_or_404(book_id)
    
    # Get available copies with locations
    available_copies = book.copies.filter(
        BookCopy.status == CopyStatus.AVAILABLE.value
    ).all()
    
    # Get all copies for total count
    total_copies = book.copies.count()
    
    return render_template('student/view_book.html',
                          book=book,
                          available_copies=available_copies,
                          total_copies=total_copies)


@student_bp.route('/my-loans')
@login_required
def my_loans():
    """View my borrowed books"""
    member = Member.query.filter_by(member_id=current_user.username).first()
    
    if not member:
        return render_template('student/my_loans.html',
                              member=None,
                              active_loans=[],
                              history=[],
                              now=datetime.utcnow())
    
    # Active loans
    active_loans = Loan.query.filter(
        Loan.member_id == member.id,
        Loan.status.in_([LoanStatus.ACTIVE.value, LoanStatus.OVERDUE.value])
    ).order_by(Loan.due_date).all()
    
    # Loan history (returned books)
    history = Loan.query.filter_by(
        member_id=member.id,
        status=LoanStatus.RETURNED.value
    ).order_by(Loan.return_date.desc()).limit(20).all()
    
    return render_template('student/my_loans.html',
                          member=member,
                          active_loans=active_loans,
                          history=history,
                          now=datetime.utcnow())


@student_bp.route('/leaderboard')
@login_required
def leaderboard():
    """NILAM reading leaderboard by student year"""
    selected_year = request.args.get('year', type=int)
    
    # Get all years that have students
    years = db.session.query(Member.student_year).distinct().filter(
        Member.student_year.isnot(None),
        Member.member_type == 'Student'
    ).order_by(Member.student_year).all()
    years = [y[0] for y in years if y[0]]
    
    # Base query for leaderboard
    leaderboard_query = Member.query.filter(
        Member.member_type == 'Student',
        Member.is_active == True,
        Member.total_books_read > 0
    )
    
    if selected_year:
        leaderboard_query = leaderboard_query.filter(Member.student_year == selected_year)
    
    # Get top readers
    top_readers = leaderboard_query.order_by(
        desc(Member.total_books_read)
    ).limit(50).all()
    
    # Get stats by year
    year_stats = db.session.query(
        Member.student_year,
        func.count(Member.id).label('student_count'),
        func.sum(Member.total_books_read).label('total_read'),
        func.avg(Member.total_books_read).label('avg_read')
    ).filter(
        Member.member_type == 'Student',
        Member.student_year.isnot(None),
        Member.is_active == True
    ).group_by(Member.student_year).order_by(Member.student_year).all()
    
    return render_template('student/leaderboard.html',
                          years=years,
                          selected_year=selected_year,
                          top_readers=top_readers,
                          year_stats=year_stats)


# API for student portal
@student_bp.route('/api/book-availability/<int:book_id>')
@login_required
def api_book_availability(book_id):
    """Get real-time availability for a book"""
    book = Book.query.get_or_404(book_id)
    
    available = book.copies.filter(
        BookCopy.status == CopyStatus.AVAILABLE.value
    ).all()
    
    return jsonify({
        'book_id': book.id,
        'title': book.title,
        'total_copies': book.copies.count(),
        'available_count': len(available),
        'locations': [
            {
                'accession': c.accession_number,
                'location': c.location or 'General Section',
                'condition': c.condition
            }
            for c in available
        ]
    })
