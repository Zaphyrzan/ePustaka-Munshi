"""
Internationalization (i18n) utilities for ePustaka-Munshi.
Supports English and Malay language switching.
"""
from flask import session, current_app

# Supported languages
LANGUAGES = {
    'en': 'English',
    'ms': 'Bahasa Melayu'
}

# Default language
DEFAULT_LANGUAGE = 'en'

# Translation dictionary
TRANSLATIONS = {
    # ========== Common / Navigation ==========
    'app_name': {
        'en': 'ePustaka Munshi',
        'ms': 'ePustaka Munshi'
    },
    'dashboard': {
        'en': 'Dashboard',
        'ms': 'Papan Pemuka'
    },
    'catalog': {
        'en': 'Catalog',
        'ms': 'Katalog'
    },
    'circulation': {
        'en': 'Circulation',
        'ms': 'Peredaran'
    },
    'users': {
        'en': 'Users',
        'ms': 'Pengguna'
    },
    'ocr_digitization': {
        'en': 'OCR Digitization',
        'ms': 'Digitalisasi OCR'
    },
    'logout': {
        'en': 'Logout',
        'ms': 'Log Keluar'
    },
    'login': {
        'en': 'Login',
        'ms': 'Log Masuk'
    },
    'profile': {
        'en': 'Profile',
        'ms': 'Profil'
    },
    'settings': {
        'en': 'Settings',
        'ms': 'Tetapan'
    },
    'language': {
        'en': 'Language',
        'ms': 'Bahasa'
    },
    
    # ========== Actions ==========
    'add': {
        'en': 'Add',
        'ms': 'Tambah'
    },
    'edit': {
        'en': 'Edit',
        'ms': 'Sunting'
    },
    'delete': {
        'en': 'Delete',
        'ms': 'Padam'
    },
    'save': {
        'en': 'Save',
        'ms': 'Simpan'
    },
    'cancel': {
        'en': 'Cancel',
        'ms': 'Batal'
    },
    'search': {
        'en': 'Search',
        'ms': 'Cari'
    },
    'view': {
        'en': 'View',
        'ms': 'Lihat'
    },
    'back': {
        'en': 'Back',
        'ms': 'Kembali'
    },
    'submit': {
        'en': 'Submit',
        'ms': 'Hantar'
    },
    'upload': {
        'en': 'Upload',
        'ms': 'Muat Naik'
    },
    'download': {
        'en': 'Download',
        'ms': 'Muat Turun'
    },
    'confirm': {
        'en': 'Confirm',
        'ms': 'Sahkan'
    },
    'actions': {
        'en': 'Actions',
        'ms': 'Tindakan'
    },
    
    # ========== OCR Module ==========
    'ocr_ledger_digitization': {
        'en': 'Library Ledger Digitization',
        'ms': 'Pendigitalan Lejar Perpustakaan'
    },
    'upload_ledger': {
        'en': 'Upload Ledger Image',
        'ms': 'Muat Naik Imej Lejar'
    },
    'ocr_jobs': {
        'en': 'OCR Jobs',
        'ms': 'Kerja-kerja OCR'
    },
    'new_job': {
        'en': 'New Job',
        'ms': 'Kerja Baru'
    },
    'job_name': {
        'en': 'Job Name',
        'ms': 'Nama Kerja'
    },
    'status': {
        'en': 'Status',
        'ms': 'Status'
    },
    'pending': {
        'en': 'Pending',
        'ms': 'Menunggu'
    },
    'processing': {
        'en': 'Processing',
        'ms': 'Memproses'
    },
    'completed': {
        'en': 'Completed',
        'ms': 'Selesai'
    },
    'failed': {
        'en': 'Failed',
        'ms': 'Gagal'
    },
    'review': {
        'en': 'Review',
        'ms': 'Semak'
    },
    'review_results': {
        'en': 'Review Results',
        'ms': 'Semak Keputusan'
    },
    'extracted_data': {
        'en': 'Extracted Data',
        'ms': 'Data Diekstrak'
    },
    
    # ========== Ledger Fields ==========
    'no_perolehan': {
        'en': 'Accession No.',
        'ms': 'No Perolehan'
    },
    'no_panggilan': {
        'en': 'Call No.',
        'ms': 'No Panggilan'
    },
    'pengarang': {
        'en': 'Author',
        'ms': 'Pengarang'
    },
    'tajuk_buku': {
        'en': 'Book Title',
        'ms': 'Tajuk Buku'
    },
    'penerbit': {
        'en': 'Publisher',
        'ms': 'Tempat & Nama Penerbit'
    },
    'tarikh_penerbit': {
        'en': 'Publication Date',
        'ms': 'Tarikh Penerbit'
    },
    'tarikh_perolehan': {
        'en': 'Acquisition Date',
        'ms': 'Tarikh Perolehan'
    },
    'bil_no': {
        'en': 'Bill No.',
        'ms': 'Bil. No.'
    },
    'punca': {
        'en': 'Source',
        'ms': 'Punca'
    },
    'harga_rm': {
        'en': 'Price (RM)',
        'ms': 'Harga (RM)'
    },
    'harga_sen': {
        'en': 'Price (Sen)',
        'ms': 'Harga (Sen)'
    },
    'muka_surat': {
        'en': 'Page Count',
        'ms': 'Muka Surat'
    },
    'catatan': {
        'en': 'Notes',
        'ms': 'Catatan'
    },
    'raw_text': {
        'en': 'Raw Text',
        'ms': 'Teks Asal'
    },
    'confidence': {
        'en': 'Confidence',
        'ms': 'Keyakinan'
    },
    
    # ========== OCR Actions & Messages ==========
    'ai_suggest': {
        'en': 'AI Suggest',
        'ms': 'Cadangan AI'
    },
    'apply_all': {
        'en': 'Apply All Suggestions',
        'ms': 'Guna Semua Cadangan'
    },
    'save_continue': {
        'en': 'Save & Continue',
        'ms': 'Simpan & Teruskan'
    },
    'finalize': {
        'en': 'Finalize',
        'ms': 'Muktamadkan'
    },
    'discard': {
        'en': 'Discard',
        'ms': 'Buang'
    },
    'select_file': {
        'en': 'Select file to upload',
        'ms': 'Pilih fail untuk dimuat naik'
    },
    'drag_drop': {
        'en': 'Drag and drop file here, or click to select',
        'ms': 'Seret dan lepas fail di sini, atau klik untuk memilih'
    },
    'supported_formats': {
        'en': 'Supported formats: JPEG, PNG, PDF',
        'ms': 'Format disokong: JPEG, PNG, PDF'
    },
    'no_jobs': {
        'en': 'No OCR jobs found. Upload a ledger image to start.',
        'ms': 'Tiada kerja OCR ditemui. Muat naik imej lejar untuk bermula.'
    },
    'job_created': {
        'en': 'OCR job created successfully!',
        'ms': 'Kerja OCR berjaya dicipta!'
    },
    'job_processing': {
        'en': 'Processing OCR...',
        'ms': 'Memproses OCR...'
    },
    'results_saved': {
        'en': 'Results saved successfully!',
        'ms': 'Keputusan berjaya disimpan!'
    },
    'results_finalized': {
        'en': 'Results finalized and committed to catalog.',
        'ms': 'Keputusan dimuktamadkan dan dikomitkan ke katalog.'
    },
    'row': {
        'en': 'Row',
        'ms': 'Baris'
    },
    'page': {
        'en': 'Page',
        'ms': 'Muka Surat'
    },
    'total_rows': {
        'en': 'Total Rows',
        'ms': 'Jumlah Baris'
    },
    'created_at': {
        'en': 'Created',
        'ms': 'Dicipta'
    },
    'updated_at': {
        'en': 'Updated',
        'ms': 'Dikemas kini'
    },
    'original_image': {
        'en': 'Original Image',
        'ms': 'Imej Asal'
    },
    'view_image': {
        'en': 'View Image',
        'ms': 'Lihat Imej'
    },
    
    # ========== Catalog ==========
    'books': {
        'en': 'Books',
        'ms': 'Buku'
    },
    'add_book': {
        'en': 'Add Book',
        'ms': 'Tambah Buku'
    },
    'edit_book': {
        'en': 'Edit Book',
        'ms': 'Sunting Buku'
    },
    'book_details': {
        'en': 'Book Details',
        'ms': 'Butiran Buku'
    },
    'isbn': {
        'en': 'ISBN',
        'ms': 'ISBN'
    },
    'title': {
        'en': 'Title',
        'ms': 'Tajuk'
    },
    'author': {
        'en': 'Author',
        'ms': 'Pengarang'
    },
    'publisher': {
        'en': 'Publisher',
        'ms': 'Penerbit'
    },
    'year': {
        'en': 'Year',
        'ms': 'Tahun'
    },
    'category': {
        'en': 'Category',
        'ms': 'Kategori'
    },
    'copies': {
        'en': 'Copies',
        'ms': 'Salinan'
    },
    'available': {
        'en': 'Available',
        'ms': 'Tersedia'
    },
    
    # ========== Circulation ==========
    'checkout': {
        'en': 'Checkout',
        'ms': 'Pinjam'
    },
    'return': {
        'en': 'Return',
        'ms': 'Pulang'
    },
    'active_loans': {
        'en': 'Active Loans',
        'ms': 'Pinjaman Aktif'
    },
    'loan_history': {
        'en': 'Loan History',
        'ms': 'Sejarah Pinjaman'
    },
    'borrower': {
        'en': 'Borrower',
        'ms': 'Peminjam'
    },
    'due_date': {
        'en': 'Due Date',
        'ms': 'Tarikh Tamat'
    },
    'overdue': {
        'en': 'Overdue',
        'ms': 'Lewat Tempoh'
    },
    
    # ========== Users ==========
    'members': {
        'en': 'Members',
        'ms': 'Ahli'
    },
    'staff': {
        'en': 'Staff',
        'ms': 'Kakitangan'
    },
    'add_member': {
        'en': 'Add Member',
        'ms': 'Tambah Ahli'
    },
    'member_id': {
        'en': 'Member ID',
        'ms': 'ID Ahli'
    },
    'name': {
        'en': 'Name',
        'ms': 'Nama'
    },
    'email': {
        'en': 'Email',
        'ms': 'E-mel'
    },
    'phone': {
        'en': 'Phone',
        'ms': 'Telefon'
    },
    'class': {
        'en': 'Class',
        'ms': 'Kelas'
    },
    
    # ========== Messages ==========
    'success': {
        'en': 'Success',
        'ms': 'Berjaya'
    },
    'error': {
        'en': 'Error',
        'ms': 'Ralat'
    },
    'warning': {
        'en': 'Warning',
        'ms': 'Amaran'
    },
    'info': {
        'en': 'Info',
        'ms': 'Maklumat'
    },
    'confirm_delete': {
        'en': 'Are you sure you want to delete this?',
        'ms': 'Adakah anda pasti mahu memadamkan ini?'
    },
    'no_results': {
        'en': 'No results found.',
        'ms': 'Tiada keputusan ditemui.'
    },
    'loading': {
        'en': 'Loading...',
        'ms': 'Memuatkan...'
    },
    
    # ========== Student Module ==========
    'my_loans': {
        'en': 'My Loans',
        'ms': 'Pinjaman Saya'
    },
    'leaderboard': {
        'en': 'Leaderboard',
        'ms': 'Papan Pemimpin'
    },
    'search_books': {
        'en': 'Search Books',
        'ms': 'Cari Buku'
    },
    
    # ========== Excel Import ==========
    'import_students': {
        'en': 'Import Students',
        'ms': 'Import Pelajar'
    },
    'import_ledger': {
        'en': 'Import Ledger',
        'ms': 'Import Lejar'
    },
    'upload_excel': {
        'en': 'Upload Excel File',
        'ms': 'Muat Naik Fail Excel'
    },
    'choose_file': {
        'en': 'Choose File',
        'ms': 'Pilih Fail'
    },
    'supported_formats': {
        'en': 'Supported: XLSX, XLS, CSV',
        'ms': 'Disokong: XLSX, XLS, CSV'
    },
    'file_size_limit': {
        'en': 'Max file size: 10MB',
        'ms': 'Saiz fail maksimum: 10MB'
    },
    'import_preview': {
        'en': 'Import Preview',
        'ms': 'Pratonton Import'
    },
    'rows_to_import': {
        'en': 'Rows to Import',
        'ms': 'Baris untuk Import'
    },
    'import_complete': {
        'en': 'Import Complete',
        'ms': 'Import Selesai'
    },
    'rows_imported': {
        'en': 'Rows Imported',
        'ms': 'Baris Diimport'
    },
    'import_errors': {
        'en': 'Import Errors',
        'ms': 'Ralat Import'
    },
    'no_errors': {
        'en': 'No errors',
        'ms': 'Tiada ralat'
    },
    'download_template': {
        'en': 'Download Template',
        'ms': 'Muat Turun Templat'
    },
    'form_level': {
        'en': 'Form Level',
        'ms': 'Tahap Tingkatan'
    },
    'class_group': {
        'en': 'Class Group',
        'ms': 'Kumpulan Kelas'
    },
    'form1': {
        'en': 'Form 1',
        'ms': 'Tingkatan 1'
    },
    'form2': {
        'en': 'Form 2',
        'ms': 'Tingkatan 2'
    },
    'form3': {
        'en': 'Form 3',
        'ms': 'Tingkatan 3'
    },
    'form4': {
        'en': 'Form 4',
        'ms': 'Tingkatan 4'
    },
    'form5': {
        'en': 'Form 5',
        'ms': 'Tingkatan 5'
    },
    'graduated': {
        'en': 'Graduated',
        'ms': 'Tamat Belajar'
    },
    'student_management': {
        'en': 'Student Management',
        'ms': 'Pengurusan Pelajar'
    },
    'active_students': {
        'en': 'Active Students',
        'ms': 'Pelajar Aktif'
    },
    'graduation_management': {
        'en': 'Graduation Management',
        'ms': 'Pengurusan Kelulusan'
    },
    'mark_for_deletion': {
        'en': 'Mark for Deletion',
        'ms': 'Tandakan untuk Pemadaman'
    },
    'last_login': {
        'en': 'Last Login',
        'ms': 'Log Masuk Terakhir'
    },
    'never_logged_in': {
        'en': 'Never logged in',
        'ms': 'Tidak pernah log masuk'
    },
    'inactive_warning': {
        'en': 'No login activity',
        'ms': 'Tiada aktiviti log masuk'
    },
    'instructions': {
        'en': 'Instructions',
        'ms': 'Arahan'
    },
    'notes': {
        'en': 'Notes',
        'ms': 'Catatan'
    },
}


def get_language() -> str:
    """Get current language from session, default to English."""
    try:
        return session.get('language', DEFAULT_LANGUAGE)
    except RuntimeError:
        # Outside request context
        return DEFAULT_LANGUAGE


def set_language(lang_code: str) -> bool:
    """Set the language in session."""
    if lang_code in LANGUAGES:
        session['language'] = lang_code
        return True
    return False


def get_text(key: str, lang: str = None) -> str:
    """
    Get translated text for a key.
    
    Args:
        key: Translation key
        lang: Language code (default: from session)
    
    Returns:
        Translated text, or key if not found
    """
    if lang is None:
        lang = get_language()
    
    if key in TRANSLATIONS:
        trans = TRANSLATIONS[key]
        if lang in trans:
            return trans[lang]
        elif DEFAULT_LANGUAGE in trans:
            return trans[DEFAULT_LANGUAGE]
    
    # Return the key with underscores replaced by spaces as fallback
    return key.replace('_', ' ').title()


# Shorthand alias
t = get_text


def register_i18n(app):
    """Register i18n functions with Flask app for use in templates."""
    
    @app.context_processor
    def inject_i18n():
        """Make translation functions available in all templates."""
        return {
            't': get_text,
            'get_text': get_text,
            'current_language': get_language(),
            'languages': LANGUAGES
        }
    
    @app.route('/set-language/<lang_code>')
    def set_lang(lang_code):
        """Route to change language."""
        from flask import redirect, request
        set_language(lang_code)
        # Redirect back to the previous page
        return redirect(request.referrer or '/')
