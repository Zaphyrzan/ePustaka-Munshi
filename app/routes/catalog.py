"""
Catalog routes - Book and BookCopy management
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_required, current_user
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from app import db
from app.models import Book, BookCopy, CopyStatus, Permission
from app.utils.barcode_utils import generate_accession_number, generate_barcode
from app.utils.cache_utils import cache_query
import io
import barcode
from barcode.writer import ImageWriter

catalog_bp = Blueprint('catalog', __name__)


@cache_query(ttl_seconds=3600)
def get_catalog_categories():
    """Get all distinct book categories for catalog, cached for 1 hour"""
    categories = db.session.query(Book.category).distinct().filter(
        Book.category.isnot(None)
    ).order_by(Book.category).all()
    return [c[0] for c in categories if c[0]]


def permission_required(perm):
    """Decorator to check permission"""
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.can(perm):
                flash('You do not have permission to access this page', 'error')
                return redirect(url_for('main.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@catalog_bp.route('/')
@login_required
def index():
    """Book catalog listing with search"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
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
    
    # Use cached categories (no database query on every page load!)
    categories = get_catalog_categories()
    
    books = query.order_by(Book.title).paginate(page=page, per_page=per_page)
    
    return render_template('catalog/index.html', 
                          books=books, 
                          search=search,
                          category=category,
                          categories=categories)


@catalog_bp.route('/book/<int:book_id>')
@login_required
def view_book(book_id):
    """View book details"""
    book = Book.query.get_or_404(book_id)
    return render_template('catalog/view_book.html', book=book)


@catalog_bp.route('/book/add', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_CATALOG)
def add_book():
    """Add a new book"""
    if request.method == 'POST':
        book = Book(
            title=request.form.get('title', '').strip(),
            author=request.form.get('author', '').strip(),
            isbn=request.form.get('isbn', '').strip() or None,
            publisher=request.form.get('publisher', '').strip() or None,
            publication_year=request.form.get('publication_year', type=int),
            category=request.form.get('category', '').strip() or None,
            call_number=request.form.get('call_number', '').strip() or None,
            language=request.form.get('language', 'Malay'),
            description=request.form.get('description', '').strip() or None,
            price=request.form.get('price', type=float) or None
        )
        
        db.session.add(book)
        db.session.commit()
        
        flash(f'Book "{book.title}" added successfully', 'success')
        return redirect(url_for('catalog.view_book', book_id=book.id))
    
    return render_template('catalog/add_book.html')


@catalog_bp.route('/book/<int:book_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_CATALOG)
def edit_book(book_id):
    """Edit a book"""
    book = Book.query.get_or_404(book_id)
    
    if request.method == 'POST':
        book.title = request.form.get('title', '').strip()
        book.author = request.form.get('author', '').strip()
        book.isbn = request.form.get('isbn', '').strip() or None
        book.publisher = request.form.get('publisher', '').strip() or None
        book.publication_year = request.form.get('publication_year', type=int)
        book.category = request.form.get('category', '').strip() or None
        book.call_number = request.form.get('call_number', '').strip() or None
        book.language = request.form.get('language', 'Malay')
        book.description = request.form.get('description', '').strip() or None
        book.price = request.form.get('price', type=float) or None
        
        db.session.commit()
        
        flash(f'Book "{book.title}" updated successfully', 'success')
        return redirect(url_for('catalog.view_book', book_id=book.id))
    
    return render_template('catalog/edit_book.html', book=book)


@catalog_bp.route('/book/<int:book_id>/delete', methods=['POST'])
@login_required
@permission_required(Permission.MANAGE_CATALOG)
def delete_book(book_id):
    """Delete a book"""
    book = Book.query.get_or_404(book_id)
    
    # Check if any copies are on loan
    on_loan = book.copies.filter(BookCopy.status == CopyStatus.ON_LOAN.value).count()
    if on_loan > 0:
        flash(f'Cannot delete: {on_loan} copies are currently on loan', 'error')
        return redirect(url_for('catalog.view_book', book_id=book.id))
    
    title = book.title
    db.session.delete(book)
    db.session.commit()
    
    flash(f'Book "{title}" deleted successfully', 'success')
    return redirect(url_for('catalog.index'))


@catalog_bp.route('/book/<int:book_id>/copy/add', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_COPIES)
def add_copy(book_id):
    """Add a copy to a book"""
    book = Book.query.get_or_404(book_id)
    
    if request.method == 'POST':
        # Auto-generate accession number and barcode
        accession = generate_accession_number()
        barcode_value = generate_barcode(accession)
        
        copy = BookCopy(
            book_id=book.id,
            accession_number=accession,
            barcode=barcode_value,
            status=CopyStatus.AVAILABLE.value,
            condition=request.form.get('condition', 'Good'),
            location=request.form.get('location', '').strip() or None,
            notes=request.form.get('notes', '').strip() or None
        )
        
        db.session.add(copy)
        db.session.commit()
        
        flash(f'Copy {copy.accession_number} added successfully (Barcode: {copy.barcode})', 'success')
        return redirect(url_for('catalog.view_book', book_id=book.id))
    
    return render_template('catalog/add_copy.html', book=book)


@catalog_bp.route('/copy/<int:copy_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_COPIES)
def edit_copy(copy_id):
    """Edit a copy"""
    copy = BookCopy.query.get_or_404(copy_id)
    
    if request.method == 'POST':
        # Barcode is read-only and cannot be changed
        copy.condition = request.form.get('condition', 'Good')
        copy.location = request.form.get('location', '').strip() or None
        copy.notes = request.form.get('notes', '').strip() or None
        
        # Only allow status change if not on loan
        if copy.status != CopyStatus.ON_LOAN.value:
            copy.status = request.form.get('status', CopyStatus.AVAILABLE.value)
        
        db.session.commit()
        
        flash(f'Copy {copy.accession_number} updated successfully', 'success')
        return redirect(url_for('catalog.view_book', book_id=copy.book_id))
    
    return render_template('catalog/edit_copy.html', copy=copy)


@catalog_bp.route('/book/<int:book_id>/print-barcodes', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_COPIES)
def print_barcodes(book_id):
    """Print barcodes for selected copies"""
    book = Book.query.get_or_404(book_id)
    
    if request.method == 'POST':
        copy_ids = request.form.getlist('copy_ids')
        
        if not copy_ids:
            flash('No copies selected for printing', 'warning')
            return redirect(url_for('catalog.view_book', book_id=book_id))
        
        # Get selected copies
        copies = BookCopy.query.filter(BookCopy.id.in_(copy_ids)).all()
        
        return render_template('catalog/print_barcodes.html', 
                             book=book, 
                             copies=copies)
    
    # GET request - show selection form
    copies = book.copies.all()
    return render_template('catalog/select_barcodes.html', 
                          book=book, 
                          copies=copies)


@catalog_bp.route('/api/barcode/<barcode_value>')
@login_required
def api_barcode_image(barcode_value):
    """Generate and return barcode image as PNG"""
    try:
        # Create barcode object
        ean = barcode.get_barcode_class('code128')
        ean_instance = ean(barcode_value, writer=ImageWriter())
        
        # Generate to bytes buffer
        buffer = io.BytesIO()
        ean_instance.write(buffer)
        buffer.seek(0)
        
        return send_file(buffer, mimetype='image/png')
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# API endpoints for AJAX
@catalog_bp.route('/api/search')
@login_required
def api_search():
    """Search books via API (for autocomplete)"""
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    
    search_term = f'%{q}%'
    books = Book.query.filter(
        db.or_(
            Book.title.ilike(search_term),
            Book.author.ilike(search_term),
            Book.isbn.ilike(search_term)
        )
    ).limit(10).all()
    
    return jsonify([book.to_dict() for book in books])


@catalog_bp.route('/api/copy/<barcode>')
@login_required
def api_get_copy(barcode):
    """Get copy by barcode (scanner input)"""
    copy = BookCopy.query.filter_by(barcode=barcode).first()
    if copy:
        return jsonify(copy.to_dict())
    return jsonify({'error': 'Copy not found'}), 404
