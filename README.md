# ePustaka Munshi - Library Management System

A prototype library management system with OCR-based ledger digitization for Malaysian school libraries.

## Features

### ✅ Implemented (Prototype)
- **Authentication & RBAC**: Login, role-based permissions (Administrator, Librarian, Student Assistant, Student)
- **Book Catalog**: Add/edit/delete books, manage bibliographic data
- **Inventory Management**: Track physical copies with accession numbers, barcodes, status, location
- **Circulation**: Book checkout, return, loan tracking, due dates, overdue detection
- **Member Management**: Student/staff records, borrowing eligibility
- **OCR Digitization**: Upload scanned ledger images/PDFs, extract data using Tesseract OCR, review & commit
- **Scanner Abstraction**: Interface for future USB scanner integration (WIA/TWAIN)

### 🔮 Future Expansion
- USB Scanner Integration (WIA/TWAIN)
- Renewals & Reservations
- Fine Management
- Email/SMS Reminders
- Reports & Analytics
- Multi-site/LAN Mode

## Quick Start

### Prerequisites
- Python 3.10+
- (Optional) Tesseract OCR for ledger digitization

### Installation

```powershell
# 1. Navigate to project folder
cd "c:\Users\wanza\Documents\Github Folder\ePustaka-Munshi"

# 2. Create virtual environment (first time only)
python -m venv venv

# 3. Activate virtual environment
.\venv\Scripts\Activate

# 4. Install dependencies (first time only)
pip install -r requirements.txt

# 5. Initialize database and seed demo data (first time only)
$env:FLASK_APP = "run.py"
flask init-db
flask seed-demo

# 6. Run the application
python run.py
```

### Running the Server (After Setup)

```powershell
# Quick start (after initial setup)
cd "c:\Users\wanza\Documents\Github Folder\ePustaka-Munshi"
.\venv\Scripts\Activate
python run.py
```

The server will start at **http://localhost:5000**

### Access
Open http://localhost:5000 in your browser.

**Demo Accounts:**
| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | Administrator |
| librarian | lib123 | Librarian |
| STU0001 | student123 | Student |

### Customization

**Add Your School Logo:**
1. Save your logo as `school_logo.png`
2. Place it in: `app/static/images/school_logo.png`
3. Recommended size: 200x200 pixels, PNG with transparency

## Project Structure

```
ePustaka-Munshi/
├── app/
│   ├── __init__.py          # App factory
│   ├── models/               # Database models
│   │   ├── user.py           # User, Role, Permission
│   │   ├── member.py         # Library members
│   │   ├── catalog.py        # Book, BookCopy
│   │   ├── circulation.py    # Loan
│   │   └── ocr.py            # OCRJob, OCRResult
│   ├── routes/               # Flask blueprints
│   │   ├── auth.py           # Login/logout
│   │   ├── catalog.py        # Book management
│   │   ├── circulation.py    # Checkout/return
│   │   ├── ocr.py            # OCR digitization
│   │   ├── student.py        # Student portal
│   │   └── users.py          # User/member management
│   ├── services/             # Business logic
│   │   ├── scanner_service.py  # Scanner abstraction (future USB)
│   │   └── ocr_service.py      # Tesseract OCR processing
│   ├── static/               # Static files
│   │   ├── css/              # Custom CSS
│   │   ├── js/               # JavaScript files
│   │   └── images/           # ⬅️ PUT YOUR SCHOOL LOGO HERE (school_logo.png)
│   └── templates/            # HTML templates
├── config.py                 # Configuration
├── run.py                    # Entry point + CLI commands
├── requirements.txt          # Dependencies
└── instance/                 # SQLite database (auto-created)
```

## OCR Setup (Optional)

To enable ledger digitization:

1. **Install Tesseract OCR**
   - Download from: https://github.com/UB-Mannheim/tesseract/wiki
   - Install to default location or update `TESSERACT_CMD` in config.py

2. **Install Poppler** (for PDF support)
   - Download from: https://github.com/oschwartz10612/poppler-windows/releases
   - Add `bin` folder to system PATH

## Scanner Integration (Future)

The prototype includes a scanner abstraction layer (`app/services/scanner_service.py`) with:

- `IScannerService` - Abstract interface for any scanner
- `FileImportScanSource` - Current implementation (file upload)
- `WIAScanSource` - Placeholder for Windows Image Acquisition
- `TWAINScanSource` - Placeholder for TWAIN protocol

**To add USB scanner support later:**
1. Install scanner driver
2. Implement `WIAScanSource` or `TWAINScanSource` using pywin32/pytwain
3. Scanner will automatically appear in the OCR upload interface

## Development

### CLI Commands

```powershell
# Initialize database
flask init-db

# Create admin user
flask create-admin

# Seed demo data
flask seed-demo
```

### Environment Variables

Create a `.env` file (optional):

```
SECRET_KEY=your-secret-key
FLASK_CONFIG=development
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

## Tech Stack

- **Backend**: Flask, SQLAlchemy, Flask-Login
- **Database**: SQLite (upgradeable to PostgreSQL/MySQL)
- **Frontend**: Bootstrap 5, Bootstrap Icons
- **OCR**: Tesseract (pytesseract)
- **PDF**: pdf2image, Pillow

## License

This project is part of a thesis/PSM at UTM.

---

**ePustaka Munshi** - Digitizing Malaysian School Libraries 📚
