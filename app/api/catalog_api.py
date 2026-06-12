"""
Catalog API Routes - JSON endpoints for books and copies
Handles book management, searching, and availability tracking
"""
from flask import Blueprint, request, current_app
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.models import Book, BookCopy, CopyStatus, Permission
from app.utils.serializers import BookSerializer, BookCopySerializer, ApiResponse

bp = Blueprint('api_catalog', __name__, url_prefix='/api/catalog')


def _attach_book_copy_counts(books):
    """Attach batched copy counts to avoid per-book count queries."""
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


@bp.route('/books', methods=['GET'])
def list_books():
    """
    Get paginated list of books with optional filtering
    
    Query parameters:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20, max: 100)
    - search: Search by title, author, ISBN
    - category: Filter by category
    - available_only: Only show books with available copies (true/false)
    
    Response:
    {
        "success": true,
        "data": {
            "items": [...],
            "pagination": {
                "page": 1,
                "per_page": 20,
                "total": 150,
                "total_pages": 8,
                "has_next": true,
                "has_prev": false
            }
        }
    }
    """
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        # Validate pagination
        if page < 1:
            page = 1
        if per_page < 1:
            per_page = 20
        
        # Build query
        query = Book.query
        
        # Apply filters
        search = request.args.get('search', '').strip()
        if search:
            # Search in title, author, ISBN
            search_term = f'%{search}%'
            query = query.filter(
                (Book.title.ilike(search_term)) |
                (Book.author.ilike(search_term)) |
                (Book.isbn.ilike(search_term))
            )
        
        # Filter by category
        category = request.args.get('category', '').strip()
        if category:
            query = query.filter(Book.category == category)
        
        # Filter by availability
        available_only = request.args.get('available_only', '').lower() == 'true'
        if available_only:
            # Join with BookCopy and filter for available copies
            query = query.join(BookCopy).filter(
                BookCopy.status == CopyStatus.AVAILABLE.value
            ).distinct()
        
        # Sort by title
        query = query.order_by(Book.title)
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * per_page
        books = query.offset(offset).limit(per_page).all()
        _attach_book_copy_counts(books)
        
        # Serialize response
        items = [BookSerializer.to_dict(book) for book in books]
        total_pages = (total + per_page - 1) // per_page
        
        return ApiResponse.success({
            'items': items,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1,
            }
        })
    
    except Exception as e:
        current_app.logger.error(f'List books error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """
    Get detailed information about a specific book
    
    Response:
    {
        "success": true,
        "data": {
            "book": {...},
            "copies": [...]  // All copies of this book
        }
    }
    """
    try:
        book = Book.query.filter_by(id=book_id).first()
        
        if not book:
            return ApiResponse.error('Book not found', status_code=404)
        
        _attach_book_copy_counts([book])
        copies = book.copies.order_by(BookCopy.accession_number).all()
        book_data = BookSerializer.to_dict(book, include_copies=False)
        
        return ApiResponse.success({
            'book': book_data,
            'copies': [BookCopySerializer.to_dict(copy, include_book=False) for copy in copies]
        })
    
    except Exception as e:
        current_app.logger.error(f'Get book error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/books', methods=['POST'])
@login_required
def create_book():
    """
    Create a new book record (admin/librarian only)
    
    Request JSON:
    {
        "title": "Book Title",
        "author": "Author Name",
        "isbn": "978-0-1234567-8-9",
        "publisher": "Publisher",
        "publication_year": 2023,
        "category": "Fiction",
        "call_number": "FIC BOO",
        "language": "English",
        "page_count": 300,
        "price": 25.99
    }
    
    Response:
    {
        "success": true,
        "data": {"id": 123, ...}
    }
    """
    try:
        # Check permissions
        if not (hasattr(current_user, 'can') and current_user.can(Permission.MANAGE_CATALOG)):
            return ApiResponse.error('Insufficient permissions', status_code=403)
        
        data = request.get_json()
        if not data:
            return ApiResponse.error('Request body required', status_code=400)
        
        # Validate required fields
        title = data.get('title', '').strip()
        if not title:
            return ApiResponse.error('Title is required', status_code=400)
        
        # Check for duplicate ISBN
        if data.get('isbn'):
            existing = Book.query.filter_by(isbn=data['isbn']).first()
            if existing:
                return ApiResponse.error('ISBN already exists', status_code=409)
        
        # Create book
        book = Book(
            title=title,
            author=data.get('author', '').strip(),
            isbn=data.get('isbn', '').strip() or None,
            publisher=data.get('publisher', '').strip(),
            publication_year=data.get('publication_year'),
            category=data.get('category', '').strip(),
            call_number=data.get('call_number', '').strip(),
            language=data.get('language', 'English'),
            page_count=data.get('page_count'),
            price=data.get('price'),
            description=data.get('description', '').strip()
        )
        
        db.session.add(book)
        db.session.commit()
        
        return ApiResponse.success(
            BookSerializer.to_dict(book),
            message='Book created successfully',
            status_code=201
        )
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Create book error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/books/<int:book_id>', methods=['PUT'])
@login_required
def update_book(book_id):
    """
    Update an existing book (admin/librarian only)
    
    Request JSON: Same fields as create_book (all optional)
    
    Response:
    {
        "success": true,
        "data": {...}  // Updated book
    }
    """
    try:
        # Check permissions
        if not (hasattr(current_user, 'can') and current_user.can(Permission.MANAGE_CATALOG)):
            return ApiResponse.error('Insufficient permissions', status_code=403)
        
        book = Book.query.get(book_id)
        if not book:
            return ApiResponse.error('Book not found', status_code=404)
        
        data = request.get_json()
        if not data:
            return ApiResponse.error('Request body required', status_code=400)
        
        # Update fields if provided
        if 'title' in data:
            title = data['title'].strip()
            if not title:
                return ApiResponse.error('Title cannot be empty', status_code=400)
            book.title = title
        
        if 'author' in data:
            book.author = data['author'].strip() or None
        
        if 'isbn' in data and data['isbn']:
            # Check for duplicate ISBN
            existing = Book.query.filter(
                Book.isbn == data['isbn'],
                Book.id != book_id
            ).first()
            if existing:
                return ApiResponse.error('ISBN already exists', status_code=409)
            book.isbn = data['isbn'].strip()
        
        if 'publisher' in data:
            book.publisher = data['publisher'].strip() or None
        
        if 'publication_year' in data:
            book.publication_year = data.get('publication_year')
        
        if 'category' in data:
            book.category = data['category'].strip() or None
        
        if 'call_number' in data:
            book.call_number = data['call_number'].strip() or None
        
        if 'language' in data:
            book.language = data['language'].strip() or 'English'
        
        if 'page_count' in data:
            book.page_count = data.get('page_count')
        
        if 'price' in data:
            book.price = data.get('price')
        
        if 'description' in data:
            book.description = data['description'].strip() or None
        
        db.session.commit()
        
        return ApiResponse.success(
            BookSerializer.to_dict(book),
            message='Book updated successfully'
        )
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Update book error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/books/<int:book_id>', methods=['DELETE'])
@login_required
def delete_book(book_id):
    """
    Delete a book and all its copies (admin only)
    
    Response:
    {
        "success": true,
        "message": "Book deleted successfully"
    }
    """
    try:
        # Check permissions
        if not (hasattr(current_user, 'can') and current_user.can(Permission.ADMIN)):
            return ApiResponse.error('Admin access required', status_code=403)
        
        book = Book.query.get(book_id)
        if not book:
            return ApiResponse.error('Book not found', status_code=404)
        
        # Check if book has active loans
        from app.models import Loan, LoanStatus
        active_loans = Loan.query.join(BookCopy).filter(
            BookCopy.book_id == book_id,
            Loan.status == LoanStatus.ACTIVE.value
        ).count()
        
        if active_loans > 0:
            return ApiResponse.error(
                f'Cannot delete book with {active_loans} active loans',
                status_code=409
            )
        
        db.session.delete(book)
        db.session.commit()
        
        return ApiResponse.success(message='Book deleted successfully')
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Delete book error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/categories', methods=['GET'])
def get_categories():
    """
    Get all distinct book categories
    
    Response:
    {
        "success": true,
        "data": ["Fiction", "Science", "History", ...]
    }
    """
    try:
        categories = db.session.query(Book.category).distinct().filter(
            Book.category.isnot(None)
        ).order_by(Book.category).all()
        
        categories = [c[0] for c in categories if c[0]]
        
        return ApiResponse.success(categories)
    
    except Exception as e:
        current_app.logger.error(f'Get categories error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)



@bp.route('/books/<int:book_id>/copies', methods=['POST'])
@login_required
def add_copy(book_id):
    """Add a physical copy with auto-generated accession number + barcode.

    Mirrors the web add_copy flow (catalog.add_copy).

    Request JSON (all optional): {"condition": "Good", "location": "Shelf A", "notes": "..."}
    """
    try:
        if not (hasattr(current_user, 'can') and current_user.can(Permission.MANAGE_COPIES)):
            return ApiResponse.error('Insufficient permissions', status_code=403)

        book = Book.query.get(book_id)
        if not book:
            return ApiResponse.error('Book not found', status_code=404)

        from app.utils.barcode_utils import generate_accession_number, generate_barcode
        data = request.get_json(silent=True) or {}

        accession = generate_accession_number()
        copy = BookCopy(
            book_id=book.id,
            accession_number=accession,
            barcode=generate_barcode(accession),
            status=CopyStatus.AVAILABLE.value,
            condition=(data.get('condition') or 'Good').strip(),
            location=(data.get('location') or '').strip() or None,
            notes=(data.get('notes') or '').strip() or None,
        )
        db.session.add(copy)
        db.session.commit()

        return ApiResponse.success(
            BookCopySerializer.to_dict(copy, include_book=False),
            message=f'Copy {copy.accession_number} added',
            status_code=201,
        )
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Add copy error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/copies/<int:copy_id>', methods=['PUT'])
@login_required
def update_copy(copy_id):
    """Update a copy's status/condition/location/notes. Barcode and accession are read-only."""
    try:
        if not (hasattr(current_user, 'can') and current_user.can(Permission.MANAGE_COPIES)):
            return ApiResponse.error('Insufficient permissions', status_code=403)

        copy = BookCopy.query.get(copy_id)
        if not copy:
            return ApiResponse.error('Copy not found', status_code=404)

        data = request.get_json(silent=True) or {}
        if 'status' in data:
            valid = [s.value for s in CopyStatus]
            if data['status'] not in valid:
                return ApiResponse.error(f'Invalid status. Valid: {valid}', status_code=400)
            copy.status = data['status']
        if 'condition' in data:
            copy.condition = (data['condition'] or '').strip() or copy.condition
        if 'location' in data:
            copy.location = (data['location'] or '').strip() or None
        if 'notes' in data:
            copy.notes = (data['notes'] or '').strip() or None

        db.session.commit()
        return ApiResponse.success(
            BookCopySerializer.to_dict(copy, include_book=False),
            message='Copy updated',
        )
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Update copy error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)
