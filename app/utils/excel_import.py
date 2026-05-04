"""
Excel import utilities for data import operations.
Provides reusable functions for importing student data and OCR ledger data.
"""
import os
from datetime import datetime
from werkzeug.utils import secure_filename
import openpyxl
from openpyxl.utils import get_column_letter
from app import db
from app.models import Member, Book, BookCopy
from app.models.member import generate_member_id


# Configuration
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
UPLOAD_FOLDER = 'uploads/imports'

# Default form levels
DEFAULT_FORM_LEVELS = {
    'Form 1': 1,
    'Form 2': 2,
    'Form 3': 3,
    'Form 4': 4,
    'Form 5': 5,
    'Graduated': 6,
}

# Default class groups (easily modifiable)
DEFAULT_CLASS_GROUPS = [
    'Science 1',
    'Science 2',
    'Arts 1',
    'Arts 2',
    'Commerce',
    'Technical',
]


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload_file(file):
    """Save uploaded file to uploads/imports folder"""
    if not file or file.filename == '':
        return None, "No file selected"
    
    if not allowed_file(file.filename):
        return None, "File type not allowed. Use Excel (.xlsx, .xls) or CSV"
    
    if len(file.read()) > MAX_FILE_SIZE:
        file.seek(0)
        return None, "File size exceeds 10MB limit"
    
    file.seek(0)
    
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
    filepath = os.path.join(UPLOAD_FOLDER, timestamp + filename)
    file.save(filepath)
    
    return filepath, None


def read_excel_file(filepath):
    """Read Excel file and return list of dictionaries"""
    try:
        workbook = openpyxl.load_workbook(filepath)
        sheet = workbook.active
        
        # Read header row (first row)
        headers = []
        for cell in sheet[1]:
            if cell.value:
                headers.append(str(cell.value).strip().lower())
        
        if not headers:
            return None, "Excel file has no headers in first row"
        
        # Read data rows
        rows = []
        for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=False), start=2):
            row_data = {}
            for col_idx, cell in enumerate(row):
                if col_idx < len(headers):
                    header = headers[col_idx]
                    # Preserve original value for non-string cells
                    value = cell.value
                    if value is not None:
                        row_data[header] = str(value).strip() if isinstance(value, str) else value
                    else:
                        row_data[header] = None
            
            if any(row_data.values()):  # Skip empty rows
                row_data['_row_number'] = row_idx
                rows.append(row_data)
        
        workbook.close()
        return rows, None
    
    except Exception as e:
        return None, f"Error reading Excel file: {str(e)}"


def import_student_data(filepath, class_mapping=None):
    """
    Import student data from Excel file.
    
    Expected columns (case-insensitive):
    - full_name or name (required)
    - member_id (optional - auto-generated if empty)
    - email (optional)
    - phone (optional)
    - form_level or form (optional, default: 1)
    - class_group or class (optional)
    - member_type (optional, default: 'Student')
    
    Returns: (success_count, error_list, imported_members)
    """
    rows, error = read_excel_file(filepath)
    if error:
        return 0, [error], []
    
    if not rows:
        return 0, ["Excel file contains no data rows"], []
    
    success_count = 0
    errors = []
    imported_members = []
    
    for row in rows:
        try:
            row_number = row.pop('_row_number')
            
            # Validate required fields
            full_name = row.get('full_name') or row.get('name')
            if not full_name:
                errors.append(f"Row {row_number}: Missing 'full_name' or 'name'")
                continue
            
            # Get or generate member_id
            member_id = row.get('member_id', '').strip()
            if not member_id:
                member_id = generate_member_id()
            
            # Check for duplicate member_id
            existing = Member.query.filter_by(member_id=member_id).first()
            if existing:
                errors.append(f"Row {row_number}: Member ID '{member_id}' already exists")
                continue
            
            # Parse form level
            form_level_str = row.get('form_level') or row.get('form', '1')
            form_level = 1
            if isinstance(form_level_str, str):
                if 'form' in form_level_str.lower():
                    try:
                        form_level = int(''.join(filter(str.isdigit, form_level_str)))
                    except ValueError:
                        form_level = 1
                else:
                    try:
                        form_level = int(form_level_str)
                    except ValueError:
                        form_level = 1
            else:
                try:
                    form_level = int(form_level_str)
                except (ValueError, TypeError):
                    form_level = 1
            
            form_level = max(1, min(6, form_level))  # Clamp 1-6
            
            # Get class group
            class_group = row.get('class_group') or row.get('class')
            
            # Create member
            member = Member(
                member_id=member_id,
                full_name=full_name.strip(),
                email=row.get('email', '').strip() or None,
                phone=row.get('phone', '').strip() or None,
                member_type=row.get('member_type', 'Student').strip(),
                form_level=form_level,
                class_group=class_group.strip() if class_group else None,
                student_year=datetime.now().year,
                is_active=True
            )
            
            db.session.add(member)
            db.session.flush()  # Flush to get the ID
            
            success_count += 1
            imported_members.append({
                'member_id': member_id,
                'full_name': full_name,
                'form_level': form_level,
                'class_group': class_group,
                'id': member.id
            })
        
        except Exception as e:
            errors.append(f"Row {row_number}: {str(e)}")
            db.session.rollback()
            continue
    
    if success_count > 0:
        try:
            db.session.commit()
        except Exception as e:
            errors.insert(0, f"Database commit error: {str(e)}")
            db.session.rollback()
            success_count = 0
            imported_members = []
    
    return success_count, errors, imported_members


def import_ocr_ledger_data(filepath, book_id=None):
    """
    Import OCR ledger data from Excel file.
    Creates/updates book records with ledger information.
    
    Expected columns (case-insensitive):
    - title or tajuk_buku (required)
    - author or pengarang (optional)
    - publisher or penerbit (optional)
    - year or tahun_penerbit (optional)
    - isbn (optional)
    - price_rm or harga_rm (optional)
    - accession_number or no_perolehan (optional)
    - call_number or no_panggilan (optional)
    - acquisition_date or tarikh_perolehan (optional)
    - notes or catatan (optional)
    
    Returns: (success_count, error_list, imported_books)
    """
    rows, error = read_excel_file(filepath)
    if error:
        return 0, [error], []
    
    if not rows:
        return 0, ["Excel file contains no data rows"], []
    
    success_count = 0
    errors = []
    imported_books = []
    
    for row in rows:
        try:
            row_number = row.pop('_row_number')
            
            # Validate required fields
            title = row.get('title') or row.get('tajuk_buku')
            if not title:
                errors.append(f"Row {row_number}: Missing 'title' or 'tajuk_buku'")
                continue
            
            # Check for duplicate title (per book)
            existing_book = Book.query.filter_by(title=title.strip()).first()
            if existing_book:
                # Update existing book
                book = existing_book
                is_new = False
            else:
                # Create new book
                book = Book()
                is_new = True
            
            # Set book fields
            book.title = title.strip()
            book.author = (row.get('author') or row.get('pengarang') or '').strip() or None
            book.publisher = (row.get('publisher') or row.get('penerbit') or '').strip() or None
            
            # Parse year
            year_str = row.get('year') or row.get('tahun_penerbit')
            if year_str:
                try:
                    book.year = int(year_str)
                except (ValueError, TypeError):
                    pass
            
            book.isbn = (row.get('isbn') or '').strip() or None
            
            # Parse price
            price_str = row.get('price_rm') or row.get('harga_rm')
            if price_str:
                try:
                    book.price = float(price_str)
                except (ValueError, TypeError):
                    pass
            
            book.category = (row.get('category') or row.get('kategori') or '').strip() or 'General'
            
            db.session.add(book)
            db.session.flush()  # Get the book ID
            
            # Create book copy with accession number
            accession_num = row.get('accession_number') or row.get('no_perolehan')
            if accession_num:
                copy = BookCopy(
                    book_id=book.id,
                    accession_number=accession_num.strip(),
                    barcode=(accession_num.strip()).replace('-', '').replace(' ', ''),
                    status='Available',
                    call_number=(row.get('call_number') or row.get('no_panggilan') or '').strip() or None,
                    location=row.get('location', 'Main Stack').strip() if row.get('location') else 'Main Stack'
                )
                db.session.add(copy)
            
            success_count += 1
            imported_books.append({
                'title': title,
                'author': book.author,
                'isbn': book.isbn,
                'price': book.price,
                'is_new': is_new,
                'book_id': book.id
            })
        
        except Exception as e:
            errors.append(f"Row {row_number}: {str(e)}")
            db.session.rollback()
            continue
    
    if success_count > 0:
        try:
            db.session.commit()
        except Exception as e:
            errors.insert(0, f"Database commit error: {str(e)}")
            db.session.rollback()
            success_count = 0
            imported_books = []
    
    return success_count, errors, imported_books


def get_class_groups():
    """Get list of available class groups (configurable)"""
    return DEFAULT_CLASS_GROUPS


def get_form_levels():
    """Get list of form levels"""
    return [
        {'value': 1, 'label': 'Form 1'},
        {'value': 2, 'label': 'Form 2'},
        {'value': 3, 'label': 'Form 3'},
        {'value': 4, 'label': 'Form 4'},
        {'value': 5, 'label': 'Form 5'},
        {'value': 6, 'label': 'Graduated'},
    ]
