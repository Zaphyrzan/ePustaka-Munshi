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
    'student_portal': {
        'en': 'Student Portal',
        'ms': 'Portal Pelajar'
    },
    'home': {
        'en': 'Home',
        'ms': 'Portal Utama'
    },
    'digitization': {
        'en': 'Digitization',
        'ms': 'Pendigitalan'
    },
    'management': {
        'en': 'Management',
        'ms': 'Pengurusan'
    },
    # ========== Student Portal ==========
    'welcome_to_epustaka': {
        'en': 'Welcome to ePustaka!',
        'ms': 'Selamat Datang ke ePustaka!'
    },
    'books_read': {
        'en': 'books read',
        'ms': 'buku dibaca'
    },
    'attention': {
        'en': 'Attention!',
        'ms': 'Perhatian!'
    },
    'overdue_warning': {
        'en': 'You have overdue books that must be returned immediately.',
        'ms': 'Anda mempunyai buku yang telah tamat tempoh. Sila pulangkan segera.'
    },
    'view_books': {
        'en': 'View books',
        'ms': 'Lihat buku'
    },
    'warning': {
        'en': 'Warning:',
        'ms': 'Peringatan:'
    },
    'due_in_3_days': {
        'en': 'books need to be returned in 3 days',
        'ms': 'buku perlu dipulangkan dalam 3 hari'
    },
    'total_books': {
        'en': 'Total Books',
        'ms': 'Jumlah Buku'
    },
    'available': {
        'en': 'Available',
        'ms': 'Tersedia'
    },
    'books_borrowed': {
        'en': 'Books Borrowed',
        'ms': 'Buku Dipinjam'
    },
    'quick_access': {
        'en': 'Quick Access',
        'ms': 'Akses Pantas'
    },
    'search_books': {
        'en': 'Search Books',
        'ms': 'Cari Buku'
    },
    'my_loans': {
        'en': 'My Loans',
        'ms': 'Pinjaman Saya'
    },
    'borrowing_leaderboard': {
        'en': 'Borrowing Leaderboard',
        'ms': 'Papan Peminjam'
    },
    'available_books': {
        'en': 'Available Books',
        'ms': 'Buku Tersedia'
    },
    'books_borrowed_now': {
        'en': 'Books Borrowed Now',
        'ms': 'Buku Dipinjam Sekarang'
    },
    'book': {
        'en': 'Book',
        'ms': 'Buku'
    },
    'loan_date': {
        'en': 'Loan Date',
        'ms': 'Tarikh Pinjam'
    },
    'return_date': {
        'en': 'Return Date',
        'ms': 'Tarikh Pulang'
    },
    'status': {
        'en': 'Status',
        'ms': 'Status'
    },
    'overdue': {
        'en': 'Overdue',
        'ms': 'Tamat Tempoh'
    },
    'due_soon': {
        'en': 'Due Soon',
        'ms': 'Hampir Tamat'
    },
    'active': {
        'en': 'Active',
        'ms': 'Aktif'
    },
    'all_forms': {
        'en': 'All Forms',
        'ms': 'Semua Tingkatan'
    },
    'form': {
        'en': 'Form',
        'ms': 'Tingkatan'
    },
    'best_borrowers': {
        'en': 'Best Borrowers by Form',
        'ms': 'Peminjam Terbaik Mengikut Tingkatan'
    },
    'class': {
        'en': 'Class',
        'ms': 'Kelas'
    },
    'books_borrowed_count': {
        'en': 'Books Borrowed',
        'ms': 'Buku Dipinjam'
    },
    'no_borrowing_data': {
        'en': 'No borrowing data',
        'ms': 'Tiada data peminjaman'
    },
    'be_first_borrower': {
        'en': 'Be among the top borrowers!',
        'ms': 'Jadilah peminjam utama!'
    },
    'statistics_by_form': {
        'en': 'Statistics by Form',
        'ms': 'Statistik Mengikut Tingkatan'
    },
    'students': {
        'en': 'students',
        'ms': 'pelajar'
    },
    'average': {
        'en': 'Average',
        'ms': 'Purata'
    },
    'no_statistics': {
        'en': 'No statistics',
        'ms': 'Tiada statistik'
    },
    'view_current_loans': {
        'en': 'View current loans and loan history',
        'ms': 'Lihat buku yang sedang dipinjam dan sejarah pinjaman'
    },
    'not_linked_to_member': {
        'en': 'Your account is not linked to a library member record',
        'ms': 'Akaun anda tidak dikaitkan dengan rekod ahli perpustakaan'
    },
    'contact_librarian': {
        'en': 'Please contact the librarian for registration',
        'ms': 'Sila hubungi pustakawan untuk pendaftaran'
    },
    'currently_borrowed': {
        'en': 'Currently Borrowed',
        'ms': 'Sedang Dipinjam'
    },
    'accession_number': {
        'en': 'Accession Number',
        'ms': 'No. Akses'
    },
    'days_remaining': {
        'en': 'Days Remaining',
        'ms': 'Baki Hari'
    },
    'no_books_borrowed': {
        'en': 'No books borrowed',
        'ms': 'Tiada buku dipinjam'
    },
    'borrow_books_now': {
        'en': 'Borrow books from the library!',
        'ms': 'Jom pinjam buku dari perpustakaan!'
    },
    'loan_history': {
        'en': 'Loan History',
        'ms': 'Sejarah Pinjaman'
    },
    'last_20_loans': {
        'en': 'Last 20 loans',
        'ms': '20 pinjaman terakhir'
    },
    'returned': {
        'en': 'Returned',
        'ms': 'Dipulangkan'
    },
    'no_loan_history': {
        'en': 'No loan history',
        'ms': 'Tiada sejarah pinjaman'
    },
    'search_for_books': {
        'en': 'Search for books you want from the library collection',
        'ms': 'Cari buku yang anda inginkan dari koleksi perpustakaan'
    },
    'search_title_author': {
        'en': 'Search title, author, ISBN...',
        'ms': 'Cari tajuk, penulis, ISBN...'
    },
    'all_categories': {
        'en': 'All Categories',
        'ms': 'Semua Kategori'
    },
    'available_only': {
        'en': 'Available only',
        'ms': 'Tersedia sahaja'
    },
    'not_available': {
        'en': 'Not available',
        'ms': 'Tiada'
    },
    'view_details': {
        'en': 'View Details',
        'ms': 'Lihat Butiran'
    },
    'no_books_found': {
        'en': 'No books found',
        'ms': 'Tiada buku dijumpai'
    },
    'try_different_search': {
        'en': 'Try searching with different keywords',
        'ms': 'Cuba cari dengan kata kunci yang lain'
    },
    'previous': {
        'en': 'Previous',
        'ms': 'Sebelum'
    },
    'next': {
        'en': 'Next',
        'ms': 'Seterusnya'
    },
    'category': {
        'en': 'Category',
        'ms': 'Kategori'
    },
    'language': {
        'en': 'Language',
        'ms': 'Bahasa'
    },
    'publisher': {
        'en': 'Publisher',
        'ms': 'Penerbit'
    },
    'year': {
        'en': 'Year',
        'ms': 'Tahun'
    },
    'call_number': {
        'en': 'Call Number',
        'ms': 'No. Panggilan'
    },
    'synopsis': {
        'en': 'Synopsis',
        'ms': 'Sinopsis'
    },
    'availability': {
        'en': 'Availability',
        'ms': 'Ketersediaan'
    },
    'out_of_copies': {
        'en': 'out of copies available',
        'ms': 'daripada naskhah tersedia'
    },
    'available_to_borrow': {
        'en': 'This book is available to borrow!',
        'ms': 'Buku ini tersedia untuk dipinjam!'
    },
    'copy_location': {
        'en': 'Copy Location:',
        'ms': 'Lokasi Naskhah:'
    },
    'general_shelf': {
        'en': 'General Shelf',
        'ms': 'Rak Umum'
    },
    'all_copies_borrowed': {
        'en': 'All copies are currently borrowed. Please check later.',
        'ms': 'Semua naskhah sedang dipinjam. Sila semak kemudian.'
    },
    'how_to_borrow': {
        'en': 'How to Borrow',
        'ms': 'Cara Meminjam'
    },
    'find_book_by_call_number': {
        'en': 'Find book on shelf by Call Number',
        'ms': 'Cari buku di rak mengikut No. Panggilan'
    },
    'bring_to_counter': {
        'en': 'Bring to library counter',
        'ms': 'Bawa ke kaunter perpustakaan'
    },
    'show_student_card': {
        'en': 'Show student card',
        'ms': 'Tunjukkan kad pelajar'
    },
    'librarian_will_process': {
        'en': 'Librarian will process the loan',
        'ms': 'Pustakawan akan proses pinjaman'
    },
    'filter_by_form': {
        'en': 'Filter by Form',
        'ms': 'Tapis mengikut Tingkatan'
    },
    'filter_by_class': {
        'en': 'Filter by Class',
        'ms': 'Tapis mengikut Kelas'
    },
    'all_classes': {
        'en': 'All Classes',
        'ms': 'Semua Kelas'
    },
    'clear_filters': {
        'en': 'Clear Filters',
        'ms': 'Padam Penapis'
    },
    'name': {
        'en': 'Name',
        'ms': 'Nama'
    },
    'total': {
        'en': 'Total',
        'ms': 'Jumlah'
    },
    'view_all': {
        'en': 'View All',
        'ms': 'Lihat Semua'
    },
    'filters': {
        'en': 'Filters',
        'ms': 'Penapis'
    },
    'books': {
        'en': 'books',
        'ms': 'buku'
    },
    'synopsis': {
        'en': 'Synopsis',
        'ms': 'Sinopsis'
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
    
    @app.before_request
    def init_language():
        """Initialize language to English if not set in session."""
        if 'language' not in session:
            session['language'] = DEFAULT_LANGUAGE
    
    @app.context_processor
    def inject_i18n():
        """Make translation functions available in all templates."""
        from flask_login import current_user
        from app.models import Member

        linked_member = None
        if current_user.is_authenticated:
            if current_user.__class__.__name__ == 'Member':
                linked_member = current_user
            elif current_user.__class__.__name__ == 'User':
                # For User (staff) accounts, only try to find a linked member
                # by member_id (username), NOT by id. This prevents matching
                # unrelated Member records that happen to have the same id.
                if getattr(current_user, 'username', None):
                    linked_member = Member.query.filter_by(member_id=current_user.username).first()

        return {
            't': get_text,
            'get_text': get_text,
            'current_language': get_language(),
            'languages': LANGUAGES,
            'linked_member': linked_member,
        }
    
    @app.route('/set-language/<lang_code>')
    def set_lang(lang_code):
        """Route to change language."""
        from flask import redirect, request
        set_language(lang_code)
        # Redirect back to the previous page
        return redirect(request.referrer or '/')
