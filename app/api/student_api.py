"""
Student Portal API Routes - JSON endpoints for student features
Dashboard, book search, my loans, and the NILAM leaderboard
"""
from datetime import datetime, timedelta

from flask import Blueprint, request, current_app
from flask_login import login_required, current_user
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app import db
from app.models import Book, BookCopy, CopyStatus, Member, Loan, LoanStatus
from app.utils.serializers import (
    BookSerializer,
    BookCopySerializer,
    LoanSerializer,
    MemberSerializer,
    ApiResponse,
)

bp = Blueprint('api_student', __name__, url_prefix='/api/student')

BORROWED_STATUSES = [
    LoanStatus.ACTIVE.value,
    LoanStatus.RETURNED.value,
    LoanStatus.OVERDUE.value,
]


def _get_linked_member():
    """Resolve the member record for the current login (Member or staff User)."""
    if current_user.__class__.__name__ == 'Member':
        return current_user

    if getattr(current_user, 'username', None):
        return Member.query.filter_by(member_id=current_user.username).first()

    return None


def _loan_options():
    return (
        joinedload(Loan.copy).joinedload(BookCopy.book),
        joinedload(Loan.member),
        joinedload(Loan.checkout_staff),
        joinedload(Loan.return_staff),
    )


def _attach_book_copy_counts(books):
    """Batch copy counts so BookSerializer runs no per-book COUNT queries."""
    book_ids = [book.id for book in books]
    if not book_ids:
        return

    total_counts = dict(
        db.session.query(BookCopy.book_id, func.count(BookCopy.id))
        .filter(BookCopy.book_id.in_(book_ids))
        .group_by(BookCopy.book_id)
        .all()
    )
    available_counts = dict(
        db.session.query(BookCopy.book_id, func.count(BookCopy.id))
        .filter(
            BookCopy.book_id.in_(book_ids),
            BookCopy.status == CopyStatus.AVAILABLE.value,
        )
        .group_by(BookCopy.book_id)
        .all()
    )

    for book in books:
        book._total_copies = total_counts.get(book.id, 0)
        book._available_copies = available_counts.get(book.id, 0)


def _paginate(query, page, per_page):
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    total_pages = (total + per_page - 1) // per_page
    return items, {
        'page': page,
        'per_page': per_page,
        'total': total,
        'total_pages': total_pages,
        'has_next': page < total_pages,
        'has_prev': page > 1,
    }


@bp.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    """Student dashboard: library stats plus the member's current loans."""
    try:
        member = _get_linked_member()

        total_books = Book.query.count()
        available_copies = BookCopy.query.filter_by(
            status=CopyStatus.AVAILABLE.value
        ).count()

        my_loans = []
        due_soon = []
        overdue = []

        if member:
            active_loans = (
                Loan.query
                .filter_by(member_id=member.id, status=LoanStatus.ACTIVE.value)
                .options(*_loan_options())
                .order_by(Loan.due_date)
                .all()
            )
            overdue_loans = (
                Loan.query
                .filter_by(member_id=member.id, status=LoanStatus.OVERDUE.value)
                .options(*_loan_options())
                .all()
            )

            member._active_loans = len(active_loans)
            member._overdue_loans = len(overdue_loans)

            three_days = datetime.utcnow() + timedelta(days=3)
            my_loans = [LoanSerializer.to_dict(loan) for loan in active_loans]
            # Due soon = due within 3 days but NOT yet overdue. Loans whose
            # stored status is stale-active but past due count as overdue.
            due_soon = [
                LoanSerializer.to_dict(loan)
                for loan in active_loans
                if loan.due_date and not loan.is_overdue and loan.due_date <= three_days
            ]
            overdue = [LoanSerializer.to_dict(loan) for loan in overdue_loans] + [
                LoanSerializer.to_dict(loan)
                for loan in active_loans
                if loan.is_overdue
            ]

        return ApiResponse.success({
            'member': MemberSerializer.to_dict(member),
            'stats': {
                'total_books': total_books,
                'available_copies': available_copies,
                'books_read': member.total_books_read if member else 0,
            },
            'my_loans': my_loans,
            'due_soon': due_soon,
            'overdue': overdue,
        })

    except Exception as e:
        current_app.logger.error(f'Student dashboard error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/search', methods=['GET'])
@login_required
def search():
    """
    Search the catalog (student view)

    Query parameters:
    - search: Match title, author, ISBN, or call number
    - category: Filter by category
    - available: '1' to only show books with available copies
    - page, per_page (12-50)
    """
    try:
        page = max(request.args.get('page', 1, type=int), 1)
        per_page = min(max(request.args.get('per_page', 12, type=int), 1), 50)

        query = Book.query

        search_term = request.args.get('search', '').strip()
        if search_term:
            like = f'%{search_term}%'
            query = query.filter(
                db.or_(
                    Book.title.ilike(like),
                    Book.author.ilike(like),
                    Book.isbn.ilike(like),
                    Book.call_number.ilike(like),
                )
            )

        category = request.args.get('category', '').strip()
        if category:
            query = query.filter(Book.category == category)

        if request.args.get('available', '') == '1':
            query = query.filter(
                Book.copies.any(BookCopy.status == CopyStatus.AVAILABLE.value)
            )

        query = query.order_by(Book.title)
        books, pagination = _paginate(query, page, per_page)

        _attach_book_copy_counts(books)
        items = [BookSerializer.to_dict(book) for book in books]

        categories = [
            row[0]
            for row in db.session.query(Book.category).distinct()
            .filter(Book.category.isnot(None))
            .order_by(Book.category)
            .all()
            if row[0]
        ]

        return ApiResponse.success({
            'items': items,
            'pagination': pagination,
            'categories': categories,
        })

    except Exception as e:
        current_app.logger.error(f'Student search error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/books/<int:book_id>', methods=['GET'])
@login_required
def book_detail(book_id):
    """Book details with available copy locations."""
    try:
        book = Book.query.get(book_id)
        if not book:
            return ApiResponse.error('Book not found', status_code=404)

        _attach_book_copy_counts([book])
        available_copies = book.copies.filter(
            BookCopy.status == CopyStatus.AVAILABLE.value
        ).all()

        return ApiResponse.success({
            'book': BookSerializer.to_dict(book),
            'available_copies': [
                BookCopySerializer.to_dict(copy, include_book=False)
                for copy in available_copies
            ],
        })

    except Exception as e:
        current_app.logger.error(f'Student book detail error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/loans', methods=['GET'])
@login_required
def my_loans():
    """
    The current member's loans

    Query parameters:
    - active_page: Page of active/overdue loans (default: 1)
    - history_page: Page of returned loans (default: 1)
    - per_page: Items per page (default: 10, max: 50)
    """
    try:
        member = _get_linked_member()
        if not member:
            return ApiResponse.error('No member record linked to this account', status_code=404)

        active_page = max(request.args.get('active_page', 1, type=int), 1)
        history_page = max(request.args.get('history_page', 1, type=int), 1)
        per_page = min(max(request.args.get('per_page', 10, type=int), 1), 50)

        active_query = (
            Loan.query
            .filter(
                Loan.member_id == member.id,
                Loan.status.in_([LoanStatus.ACTIVE.value, LoanStatus.OVERDUE.value]),
            )
            .options(*_loan_options())
            .order_by(Loan.due_date)
        )
        active_loans, active_pagination = _paginate(active_query, active_page, per_page)

        history_query = (
            Loan.query
            .filter_by(member_id=member.id, status=LoanStatus.RETURNED.value)
            .options(*_loan_options())
            .order_by(Loan.return_date.desc())
        )
        history, history_pagination = _paginate(history_query, history_page, per_page)

        return ApiResponse.success({
            'active': {
                'items': [LoanSerializer.to_dict(loan) for loan in active_loans],
                'pagination': active_pagination,
            },
            'history': {
                'items': [LoanSerializer.to_dict(loan) for loan in history],
                'pagination': history_pagination,
            },
        })

    except Exception as e:
        current_app.logger.error(f'Student loans error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/leaderboard', methods=['GET'])
@login_required
def leaderboard():
    """
    NILAM borrowing leaderboard

    Query parameters:
    - form: Filter by form level (1-5)
    - class: Filter by class group (requires form)
    - limit: Max students returned (default: 100)
    """
    try:
        selected_form = request.args.get('form', type=int)
        selected_class = request.args.get('class', '').strip()
        limit = min(max(request.args.get('limit', 100, type=int), 1), 200)

        student_filter = [
            Member.member_type.in_(['Student', 'Student Assistant']),
            Member.is_active == True,  # noqa: E712 (SQLAlchemy comparison)
        ]
        loan_join = db.and_(
            Loan.member_id == Member.id,
            Loan.status.in_(BORROWED_STATUSES),
        )

        # Available filter values
        forms = [
            row[0]
            for row in db.session.query(Member.form_level).distinct()
            .filter(Member.form_level.isnot(None), *student_filter)
            .order_by(Member.form_level)
            .all()
            if row[0]
        ]

        classes_in_form = []
        if selected_form:
            classes_in_form = [
                row[0]
                for row in db.session.query(Member.class_group).distinct()
                .filter(
                    Member.form_level == selected_form,
                    Member.class_group.isnot(None),
                    *student_filter,
                )
                .order_by(Member.class_group)
                .all()
                if row[0]
            ]

        # Student ranking
        ranking_query = db.session.query(
            Member.id,
            Member.member_id,
            Member.full_name,
            Member.form_level,
            Member.class_group,
            func.count(Loan.id).label('borrow_count'),
        ).outerjoin(Loan, loan_join).filter(*student_filter)

        if selected_form:
            ranking_query = ranking_query.filter(Member.form_level == selected_form)
            if selected_class:
                ranking_query = ranking_query.filter(Member.class_group == selected_class)

        ranking = ranking_query.group_by(
            Member.id, Member.member_id, Member.full_name,
            Member.form_level, Member.class_group,
        ).order_by(func.count(Loan.id).desc(), Member.full_name).limit(limit).all()

        students = [
            {
                'rank': index + 1,
                'id': row.id,
                'member_id': row.member_id,
                'full_name': row.full_name,
                'form_level': row.form_level,
                'class_group': row.class_group,
                'borrow_count': row.borrow_count,
            }
            for index, row in enumerate(ranking)
        ]

        # Class ranking (follows form filter, not class filter)
        class_query = db.session.query(
            Member.form_level,
            Member.class_group,
            func.count(Loan.id).label('borrow_count'),
        ).outerjoin(Loan, loan_join).filter(
            Member.class_group.isnot(None), *student_filter
        )
        if selected_form:
            class_query = class_query.filter(Member.form_level == selected_form)

        top_classes = [
            {
                'form_level': row.form_level,
                'class_group': row.class_group,
                'borrow_count': row.borrow_count,
            }
            for row in class_query.group_by(Member.form_level, Member.class_group)
            .order_by(func.count(Loan.id).desc(), Member.class_group.asc())
            .limit(3)
            .all()
        ]

        # Per-form stats
        form_stats = [
            {
                'form_level': row.form_level,
                'student_count': row.student_count,
                'total_borrowed': row.total_borrowed,
                'avg_borrowed': (
                    row.total_borrowed / row.student_count
                    if row.student_count else 0
                ),
            }
            for row in db.session.query(
                Member.form_level,
                func.count(func.distinct(Member.id)).label('student_count'),
                func.count(Loan.id).label('total_borrowed'),
            ).outerjoin(Loan, loan_join).filter(
                Member.form_level.isnot(None), *student_filter
            ).group_by(Member.form_level).order_by(Member.form_level).all()
        ]

        return ApiResponse.success({
            'forms': forms,
            'selected_form': selected_form,
            'classes_in_form': classes_in_form,
            'selected_class': selected_class or None,
            'students': students,
            'top_students': students[:3],
            'top_classes': top_classes,
            'form_stats': form_stats,
        })

    except Exception as e:
        current_app.logger.error(f'Student leaderboard error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)
