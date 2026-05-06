"""
Excel import utilities for data import operations.
Provides reusable functions for importing student data and OCR ledger data.
"""
import os
import re
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
    Maps the 7-column Malaysian ledger format to book records.
    
    7 Main Columns (from Malaysian library ledgers):
    1. NO PEROLEHAN (Accession Number) - unique identifier
    2. NO PANGGILAN (Call Number) - library classification
    3. PENGARANG (Author) - book author(s)
    4. TAJUK BUKU (Title) - book title
    5. TEMPAT DAN NAMA PENERBIT (Place & Publisher) - publication location & publisher
    6. TARIKH PENERBIT (Publication Date/Year) - year of publication
    7. PUNCA (Source/Acquisition) - how book was acquired
    
    Optional fields: TARIKH PEROLEHAN (Acquisition Date), BIL NO, HARGA RM/SEN (Price),
    MUKA SURAT (Page Count), CATATAN (Notes)
    
    Expected column names (case-insensitive, supports English and Malay):
    - title, tajuk_buku, tajuk (required)
    - author, pengarang (optional)
    - publisher, penerbit, tempat_dan_nama_penerbit (optional)
    - year, tarikh_penerbit, publication_year, tahun_penerbit (optional)
    - isbn (optional)
    - accession_number, no_perolehan (optional - used for book copy)
    - call_number, no_panggilan (optional)
    - acquisition_date, tarikh_perolehan (optional)
    - source, punca (optional)
    - notes, catatan (optional)
    - price_rm, harga_rm, price (optional)
    - page_count, muka_surat (optional)
    
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
            
            # ===== REQUIRED: Book Title =====
            # Check multiple column name variations
            title = (row.get('title') or row.get('tajuk_buku') or 
                    row.get('tajuk') or row.get('book title'))
            if not title:
                errors.append(f"Row {row_number}: Missing book title (title/tajuk_buku/tajuk)")
                continue
            
            # Check for duplicate title
            existing_book = Book.query.filter_by(title=title.strip()).first()
            if existing_book:
                # Could update existing, but for now skip to prevent duplicates
                errors.append(f"Row {row_number}: Book title '{title[:50]}' already exists")
                continue
            
            # ===== Create new book record =====
            book = Book()
            book.title = title.strip()
            
            # ===== COLUMN 3: PENGARANG (Author) =====
            book.author = (row.get('author') or row.get('pengarang') or 
                          row.get('authorname') or '').strip() or None
            
            # ===== COLUMN 5: PENERBIT (Publisher - Place & Name) =====
            # Try multiple column name variations
            publisher = (row.get('publisher') or row.get('penerbit') or
                        row.get('tempat_dan_nama_penerbit') or row.get('publisher_name') or '').strip()
            if publisher:
                book.publisher = publisher
            
            # ===== COLUMN 6: TARIKH PENERBIT (Publication Year/Date) =====
            year_str = (row.get('year') or row.get('tarikh_penerbit') or 
                       row.get('publication_year') or row.get('tahun_penerbit') or
                       row.get('pub_year') or '')
            if year_str:
                try:
                    # Try to extract just the year if it's part of a larger date
                    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', str(year_str))
                    if year_match:
                        book.publication_year = int(year_match.group(1))
                    else:
                        book.publication_year = int(year_str)
                except (ValueError, TypeError, AttributeError):
                    # Year parsing failed, skip it
                    pass
            
            # ISBN (optional)
            book.isbn = (row.get('isbn') or row.get('isbn_number') or '').strip() or None
            
            # Page count (optional)
            pages_str = row.get('page_count') or row.get('muka_surat') or row.get('pages')
            if pages_str:
                try:
                    book.page_count = int(pages_str)
                except (ValueError, TypeError):
                    pass
            
            # Category (default to 'General' if not provided)
            book.category = (row.get('category') or row.get('kategori') or 
                            row.get('subject') or 'General').strip()
            
            # Notes/Remarks (optional)
            description = (row.get('notes') or row.get('catatan') or 
                          row.get('remarks') or row.get('description') or '').strip()
            if description:
                book.description = description
            
            # Price (optional)
            price_str = row.get('price_rm') or row.get('harga_rm') or row.get('price')
            if price_str:
                try:
                    # Extract numeric price value
                    price_match = re.search(r'(\d+)[.,]?(\d{0,2})', str(price_str))
                    if price_match:
                        book.price = float(f"{price_match.group(1)}.{price_match.group(2) or '0'}")
                except (ValueError, TypeError, AttributeError):
                    pass
            
            db.session.add(book)
            db.session.flush()  # Get the book ID
            
            # ===== Create BookCopy with accession information =====
            # COLUMN 1: NO PEROLEHAN (Accession Number)
            accession_num = (row.get('accession_number') or row.get('no_perolehan') or 
                            row.get('accession_num') or '').strip()
            
            if accession_num:
                # COLUMN 2: NO PANGGILAN (Call Number)
                call_number = (row.get('call_number') or row.get('no_panggilan') or 
                              row.get('callnumber') or '').strip() or None
                
                # COLUMN 7: PUNCA (Source - how acquired)
                source = (row.get('source') or row.get('punca') or 
                         row.get('acquisition_source') or '').strip() or 'Purchase'
                
                # Tarikh Perolehan (Acquisition Date)
                acq_date_str = (row.get('acquisition_date') or row.get('tarikh_perolehan') or
                               row.get('acq_date') or '')
                acq_date = None
                if acq_date_str:
                    try:
                        # Try to parse various date formats
                        from datetime import datetime as dt
                        acq_date = dt.strptime(str(acq_date_str), '%Y-%m-%d').date()
                    except:
                        try:
                            acq_date = dt.strptime(str(acq_date_str), '%d/%m/%Y').date()
                        except:
                            pass  # Skip invalid dates
                
                copy = BookCopy(
                    book_id=book.id,
                    accession_number=accession_num,
                    call_number=call_number,
                    barcode=accession_num.replace('-', '').replace(' ', '').upper(),
                    status='available',
                    acquisition_source=source,
                    acquisition_date=acq_date,
                    condition='Good',  # Default condition
                    location='Main Stack'  # Default location
                )
                db.session.add(copy)
            
            success_count += 1
            imported_books.append({
                'title': title,
                'author': book.author,
                'publisher': book.publisher,
                'year': book.publication_year,
                'isbn': book.isbn,
                'accession': accession_num if accession_num else 'N/A',
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
