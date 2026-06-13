"""
Student Portal routes - Student-facing interface for library access
"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from sqlalchemy.orm import joinedload
from app import db
from app.models import Book, BookCopy, CopyStatus, Member, Loan, LoanStatus
from app.utils.cache_utils import cache_query
from app.utils.api_utils import OffsetPagination, ResponseFilter, ApiResponse

student_bp = Blueprint('student', __name__)


@cache_query(ttl_seconds=3600)
def get_book_categories():
    """
    Get all distinct book categories, cached for 1 hour.
    This is called on every page load in the UI, so caching is critical.
    """
    categories = db.session.query(Book.category).distinct().filter(
        Book.category.isnot(None)
    ).order_by(Book.category).all()
    return [c[0] for c in categories if c[0]]


def get_linked_member():
    """Resolve the member record for the current login."""
    if current_user.__class__.__name__ == 'Member':
        return current_user

    if getattr(current_user, 'id', None):
        member = Member.query.get(current_user.id)
        if member:
            return member

    if getattr(current_user, 'username', None):
        return Member.query.filter_by(member_id=current_user.username).first()

    return None


@student_bp.route('/')
@login_required
def index():
    """Student portal dashboard"""
    # Get member record - handle both Member and User logins
    member = get_linked_member()
    
    # Stats for dashboard - use cached function
    total_books = Book.query.count()
    available_copies = BookCopy.query.filter_by(status=CopyStatus.AVAILABLE.value).count()
    
    # Member-specific data
    my_loans = []
    due_soon = []
    overdue = []
    books_read = 0
    
    if member:
        # Get active loans with eager loading to avoid N+1
        my_loans = (
            Loan.query
            .filter_by(member_id=member.id, status=LoanStatus.ACTIVE.value)
            .options(joinedload(Loan.copy).joinedload(BookCopy.book))
            .order_by(Loan.due_date)
            .all()
        )
        
        # Due in next 3 days - already loaded from above. Excludes loans that
        # are already past due (those belong in overdue, not "due soon").
        three_days = datetime.utcnow() + timedelta(days=3)
        due_soon = [l for l in my_loans if l.due_date and not l.is_overdue and l.due_date <= three_days]
        
        # Overdue - separate query with eager loading
        overdue = (
            Loan.query
            .filter_by(member_id=member.id, status=LoanStatus.OVERDUE.value)
            .options(joinedload(Loan.copy).joinedload(BookCopy.book))
            .all()
        )
        
        books_read = member.total_books_read
    
    return render_template('student/index.html',
                          member=member,
                          total_books=total_books,
                          available_copies=available_copies,
                          my_loans=my_loans,
                          due_soon=due_soon,
                          overdue=overdue,
                          books_read=books_read,
                          now=datetime.utcnow())


@student_bp.route('/search')
@login_required
def search_books():
    """Search available books with pagination and filtering"""
    # per_page: 12-50 books, optimal for the UI grid
    page = request.args.get('page', 1, type=int)
    per_page = min(max(request.args.get('per_page', 12, type=int), 12), 50)

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
    
    # Use cached categories (no database query on every page load!)
    categories = get_book_categories()
    
    query = query.order_by(Book.title)
    # Native SQLAlchemy pagination: the template uses both books['items'] and
    # books.iter_pages()/has_next; a Pagination object satisfies both (Jinja
    # falls back from getitem to getattr for ['items']).
    books = query.paginate(page=page, per_page=per_page, error_out=False)

    # Get availability counts in a single query instead of N+1
    # Build a mapping of book_id -> available_count
    book_ids = [book.id for book in books.items]
    availability = db.session.query(
        BookCopy.book_id,
        func.count(BookCopy.id).label('available_count')
    ).filter(
        BookCopy.book_id.in_(book_ids),
        BookCopy.status == CopyStatus.AVAILABLE.value
    ).group_by(BookCopy.book_id).all()
    
    availability_map = {book_id: count for book_id, count in availability}
    
    # Attach availability info to books (no database queries!)
    for book in books.items:
        book.available_count = availability_map.get(book.id, 0)
    
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
    """View my borrowed books with pagination"""
    # Get member - handle both Member and User logins
    member = get_linked_member()
    
    if not member:
        return render_template('student/my_loans.html',
                              member=None,
                              active_loans={'items': [], 'total': 0, 'pages': 0, 'current_page': 1},
                              history={'items': [], 'total': 0, 'pages': 0, 'current_page': 1},
                              now=datetime.utcnow())
    
    # Parse pagination for active loans and history separately
    active_page = request.args.get('active_page', 1, type=int)
    history_page = request.args.get('history_page', 1, type=int)
    
    # Active loans pagination (per_page: 10 optimal for list view)
    active_pagination = OffsetPagination(active_page, 10)
    active_query = (
        Loan.query
        .filter(
            Loan.member_id == member.id,
            Loan.status.in_([LoanStatus.ACTIVE.value, LoanStatus.OVERDUE.value])
        )
        .options(joinedload(Loan.copy).joinedload(BookCopy.book))
        .order_by(Loan.due_date)
    )
    active_loans = active_pagination.paginate(active_query)
    
    # Loan history pagination (per_page: 10 optimal for list view)
    history_pagination = OffsetPagination(history_page, 10)
    history_query = (
        Loan.query
        .filter_by(member_id=member.id, status=LoanStatus.RETURNED.value)
        .options(joinedload(Loan.copy).joinedload(BookCopy.book))
        .order_by(Loan.return_date.desc())
    )
    history = history_pagination.paginate(history_query)
    
    # OffsetPagination.paginate() returns a dict; the template iterates plain
    # lists, so hand it the items (iterating the dict would yield string keys).
    return render_template('student/my_loans.html',
                          member=member,
                          active_loans=active_loans['items'],
                          history=history['items'],
                          now=datetime.utcnow())


@student_bp.route('/leaderboard')
@login_required
def leaderboard():
    """Borrowing leaderboard grouped by Form/Tingkatan and Class"""
    selected_form = request.args.get('form', type=int)
    selected_class = request.args.get('class', '')
    
    # Get all forms that have students
    forms = db.session.query(Member.form_level).distinct().filter(
        Member.form_level.isnot(None),
        Member.member_type.in_(['Student', 'Student Assistant']),
        Member.is_active == True
    ).order_by(Member.form_level).all()
    forms = [f[0] for f in forms if f[0]]
    
    # Get classes for selected form
    classes_in_form = []
    if selected_form:
        classes_in_form = db.session.query(Member.class_group).distinct().filter(
            Member.form_level == selected_form,
            Member.member_type.in_(['Student', 'Student Assistant']),
            Member.is_active == True,
            Member.class_group.isnot(None)
        ).order_by(Member.class_group).all()
        classes_in_form = [c[0] for c in classes_in_form if c[0]]
    
    # Build leaderboard query - count loans per member
    member_borrow_counts = db.session.query(
        Member.id,
        Member.member_id,
        Member.full_name,
        Member.form_level,
        Member.class_group,
        func.count(Loan.id).label('borrow_count')
    ).outerjoin(Loan, 
        db.and_(Loan.member_id == Member.id, Loan.status.in_([LoanStatus.ACTIVE.value, LoanStatus.RETURNED.value, LoanStatus.OVERDUE.value]))
    ).filter(
        Member.member_type.in_(['Student', 'Student Assistant']),
        Member.is_active == True
    )
    
    # Apply filters
    if selected_form:
        member_borrow_counts = member_borrow_counts.filter(Member.form_level == selected_form)
        if selected_class:
            member_borrow_counts = member_borrow_counts.filter(Member.class_group == selected_class)
    
    member_borrow_counts = member_borrow_counts.group_by(
        Member.id, Member.member_id, Member.full_name, Member.form_level, Member.class_group
    ).order_by(func.count(Loan.id).desc(), Member.full_name).limit(100).all()
    
    # Top 3 students for the current leaderboard filter
    top_three_students = member_borrow_counts[:3]

    # Top 3 classes by total borrowed books
    # Class ranking follows selected_form filter (if any), but not selected_class,
    # so users can still compare classes.
    class_borrow_counts = db.session.query(
        Member.form_level,
        Member.class_group,
        func.count(Loan.id).label('borrow_count')
    ).outerjoin(
        Loan,
        db.and_(Loan.member_id == Member.id, Loan.status.in_([
            LoanStatus.ACTIVE.value,
            LoanStatus.RETURNED.value,
            LoanStatus.OVERDUE.value
        ]))
    ).filter(
        Member.member_type.in_(['Student', 'Student Assistant']),
        Member.is_active == True,
        Member.class_group.isnot(None)
    )

    if selected_form:
        class_borrow_counts = class_borrow_counts.filter(Member.form_level == selected_form)

    top_three_classes = class_borrow_counts.group_by(
        Member.form_level,
        Member.class_group
    ).order_by(
        func.count(Loan.id).desc(),
        Member.class_group.asc()
    ).limit(3).all()

    # Get stats by form - simplified to avoid nested aggregates
    form_stats = db.session.query(
        Member.form_level,
        func.count(Member.id).label('student_count'),
        func.count(Loan.id).label('total_borrowed')
    ).outerjoin(Loan,
        db.and_(Loan.member_id == Member.id, Loan.status.in_([LoanStatus.ACTIVE.value, LoanStatus.RETURNED.value, LoanStatus.OVERDUE.value]))
    ).filter(
        Member.member_type.in_(['Student', 'Student Assistant']),
        Member.form_level.isnot(None),
        Member.is_active == True
    ).group_by(Member.form_level).order_by(Member.form_level).all()
    
    # Calculate average in Python
    form_stats_with_avg = []
    for form_level, student_count, total_borrowed in form_stats:
        avg_borrowed = total_borrowed / student_count if student_count > 0 else 0
        form_stats_with_avg.append((form_level, student_count, total_borrowed, avg_borrowed))
    
    # Top student and top class for selected form (if any)
    top_student = None
    top_class = None
    if selected_form:
        top_student_q = db.session.query(
            Member.full_name,
            Member.class_group,
            func.count(Loan.id).label('borrow_count')
        ).outerjoin(Loan,
            db.and_(Loan.member_id == Member.id, Loan.status.in_([LoanStatus.ACTIVE.value, LoanStatus.RETURNED.value, LoanStatus.OVERDUE.value]))
        ).filter(
            Member.member_type.in_(['Student', 'Student Assistant']),
            Member.form_level == selected_form,
            Member.is_active == True
        ).group_by(Member.id, Member.full_name, Member.class_group).order_by(func.count(Loan.id).desc()).first()

        if top_student_q:
            top_student = (top_student_q[0], top_student_q[1], top_student_q[2])

        top_class_q = db.session.query(
            Member.class_group,
            func.count(Loan.id).label('borrow_count')
        ).outerjoin(Loan,
            db.and_(Loan.member_id == Member.id, Loan.status.in_([LoanStatus.ACTIVE.value, LoanStatus.RETURNED.value, LoanStatus.OVERDUE.value]))
        ).filter(
            Member.member_type.in_(['Student', 'Student Assistant']),
            Member.form_level == selected_form,
            Member.is_active == True,
            Member.class_group.isnot(None)
        ).group_by(Member.class_group).order_by(func.count(Loan.id).desc()).first()

        if top_class_q:
            top_class = (top_class_q[0], top_class_q[1])

    return render_template('student/leaderboard.html',
                          forms=forms,
                          selected_form=selected_form,
                          classes_in_form=classes_in_form,
                          selected_class=selected_class,
                          leaderboard=member_borrow_counts,
                          top_three_students=top_three_students,
                          top_three_classes=top_three_classes,
                          form_stats=form_stats_with_avg,
                          top_student=top_student,
                          top_class=top_class)


# API for student portal
@student_bp.route('/api/book-availability/<int:book_id>')
@login_required
def api_book_availability(book_id):
    """Get real-time availability for a book"""
    book = Book.query.options(joinedload(Book.copies)).get_or_404(book_id)
    
    available = [c for c in book.copies if c.status == CopyStatus.AVAILABLE.value]
    
    return jsonify({
        'book_id': book.id,
        'title': book.title,
        'total_copies': len(book.copies),
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
