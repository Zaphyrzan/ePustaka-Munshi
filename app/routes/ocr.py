"""
OCR routes - Ledger digitization
"""
import os
import json
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models import OCRJob, OCRResult, OCRJobStatus, Loan, Member, BookCopy, Permission
from app.services import ScannerServiceFactory, OCRService, OCRCorrectionService
from app.utils.excel_import import import_ocr_ledger_data, save_upload_file, read_excel_file

ocr_bp = Blueprint('ocr', __name__)


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


def allowed_file(filename):
    """Check if file extension is allowed"""
    allowed = current_app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'tiff', 'pdf'})
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed


@ocr_bp.route('/')
@login_required
@permission_required(Permission.OCR_DIGITIZE)
def index():
    """OCR jobs listing"""
    page = request.args.get('page', 1, type=int)
    
    jobs = OCRJob.query.order_by(OCRJob.created_at.desc()).paginate(page=page, per_page=20)
    
    return render_template('ocr/index.html', jobs=jobs)


@ocr_bp.route('/upload', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.OCR_DIGITIZE)
def upload():
    """Upload files for OCR processing"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return render_template('ocr/upload.html')
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return render_template('ocr/upload.html')
        
        if not allowed_file(file.filename):
            flash('File type not allowed', 'error')
            return render_template('ocr/upload.html')
        
        # Get scanner service for file import
        upload_folder = current_app.config['OCR_UPLOAD_FOLDER']
        scanner_factory = ScannerServiceFactory(upload_folder)
        file_service = scanner_factory.get_file_import_service()
        
        # Import uploaded file
        original_filename = secure_filename(file.filename)
        scanned_image = file_service.import_uploaded_file(file, original_filename)
        
        # Create OCR job
        job_name = request.form.get('job_name', '').strip() or f'Scan_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        
        job = OCRJob(
            job_name=job_name,
            source_type='file_upload',
            source_path=scanned_image.file_path,
            original_filename=original_filename,
            page_count=1,
            status=OCRJobStatus.PENDING.value,
            created_by=current_user.id
        )
        
        db.session.add(job)
        db.session.commit()
        
        flash('File uploaded successfully. Ready for OCR processing.', 'success')
        return redirect(url_for('ocr.view_job', job_id=job.id))
    
    return render_template('ocr/upload.html')


@ocr_bp.route('/job/<int:job_id>')
@login_required
@permission_required(Permission.OCR_DIGITIZE)
def view_job(job_id):
    """View OCR job details"""
    job = OCRJob.query.get_or_404(job_id)
    results = job.results.order_by(OCRResult.page_number, OCRResult.row_number).all()
    
    return render_template('ocr/view_job.html', job=job, results=results)


@ocr_bp.route('/job/<int:job_id>/process', methods=['POST'])
@login_required
@permission_required(Permission.OCR_DIGITIZE)
def process_job(job_id):
    """Run OCR processing on a job"""
    job = OCRJob.query.get_or_404(job_id)
    
    if job.status not in [OCRJobStatus.PENDING.value, OCRJobStatus.FAILED.value]:
        flash('Job cannot be processed in current state', 'error')
        return redirect(url_for('ocr.view_job', job_id=job.id))
    
    # Initialize OCR service
    tesseract_cmd = current_app.config.get('TESSERACT_CMD')
    ocr_service = OCRService(tesseract_cmd=tesseract_cmd)
    
    if not ocr_service.is_available():
        flash('OCR service (Tesseract) is not available. Please install Tesseract OCR.', 'error')
        return redirect(url_for('ocr.view_job', job_id=job.id))
    
    try:
        job.mark_processing()
        db.session.commit()
        
        # Process file
        result_data = ocr_service.process_file(job.source_path)
        
        # Initialize AI correction service
        correction_service = OCRCorrectionService()
        
        # Store results with AI-assisted correction
        for row in result_data.get('rows', []):
            # Apply AI correction to raw OCR results
            corrected = correction_service.auto_correct_row(row)
            
            ocr_result = OCRResult(
                job_id=job.id,
                page_number=row.get('page_number', 1),
                row_number=row.get('row_number'),
                raw_text=row.get('raw_text'),
                # Malaysian catalog ledger fields
                no_perolehan_extracted=row.get('no_perolehan'),
                no_panggilan_extracted=row.get('no_panggilan'),
                pengarang_extracted=row.get('pengarang'),
                tajuk_buku_extracted=row.get('tajuk_buku'),
                penerbit_extracted=row.get('penerbit'),
                tarikh_penerbit_extracted=row.get('tarikh_penerbit'),
                tarikh_perolehan_extracted=row.get('tarikh_perolehan'),
                bil_no_extracted=row.get('bil_no'),
                punca_extracted=row.get('punca'),
                harga_rm_extracted=row.get('harga_rm'),
                harga_sen_extracted=row.get('harga_sen'),
                muka_surat_extracted=row.get('muka_surat'),
                catatan_extracted=row.get('catatan'),
                confidence_overall=row.get('confidence', 0.0)
            )
            
            # Store AI suggestions in notes for review (for catalog ledger data)
            ai_notes = []
            confidence_details = row.get('confidence_details', {})
            
            if confidence_details:
                for field, conf in confidence_details.items():
                    if conf < 0.5:
                        ai_notes.append(f"Low confidence for {field}: {conf:.0%}")
            
            if ai_notes:
                ocr_result.review_notes = "; ".join(ai_notes)
            
            db.session.add(ocr_result)
        
        job.page_count = result_data.get('pages', 1)
        job.mark_completed()
        db.session.commit()
        
        flash(f'OCR processing completed. Extracted {len(result_data.get("rows", []))} rows.', 'success')
    
    except Exception as e:
        job.mark_failed(str(e))
        db.session.commit()
        flash(f'OCR processing failed: {str(e)}', 'error')
    
    return redirect(url_for('ocr.view_job', job_id=job.id))


@ocr_bp.route('/job/<int:job_id>/review')
@login_required
@permission_required(Permission.OCR_APPROVE)
def review_job(job_id):
    """Review Malaysian ledger extraction results"""
    job = OCRJob.query.get_or_404(job_id)
    
    if job.status not in [OCRJobStatus.COMPLETED.value, OCRJobStatus.REVIEWED.value]:
        flash('Job must be completed before review', 'error')
        return redirect(url_for('ocr.view_job', job_id=job.id))
    
    results = job.results.order_by(OCRResult.page_number, OCRResult.row_number).all()
    
    return render_template('ocr/review_job.html', job=job, results=results)


@ocr_bp.route('/result/<int:result_id>/update', methods=['POST'])
@login_required
@permission_required(Permission.OCR_APPROVE)
def update_result(result_id):
    """Update ledger extraction with corrections"""
    result = OCRResult.query.get_or_404(result_id)
    
    is_valid = request.form.get('is_valid') == 'true'
    corrections = {}
    
    # Ledger 7-column fields
    for field in ['no_perolehan', 'no_panggilan', 'pengarang', 'tajuk_buku', 
                  'penerbit', 'tarikh_penerbit', 'punca']:
        value = request.form.get(field, '').strip()
        if value:
            corrections[field] = value
    
    # Optional fields
    for field in ['tarikh_perolehan', 'bil_no', 'harga', 'muka_surat', 'catatan']:
        value = request.form.get(field, '').strip()
        if value:
            corrections[field] = value
    
    notes = request.form.get('notes', '').strip()
    result.mark_reviewed(is_valid, corrections, notes)
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})
    
    flash('Result updated', 'success')
    return redirect(url_for('ocr.review_job', job_id=result.job_id))


@ocr_bp.route('/job/<int:job_id>/commit', methods=['POST'])
@login_required
@permission_required(Permission.OCR_APPROVE)
def commit_job(job_id):
    """Upload reviewed ledger data to database as books"""
    from app.models import Book, BookCopy
    
    job = OCRJob.query.get_or_404(job_id)
    
    # Check all results reviewed
    unreviewed = job.results.filter(OCRResult.is_reviewed == False).count()
    if unreviewed > 0:
        flash(f'Cannot commit: {unreviewed} results still need review', 'error')
        return redirect(url_for('ocr.review_job', job_id=job.id))
    
    # Get valid reviewed results
    valid_results = job.results.filter(OCRResult.is_valid == True).all()
    if not valid_results:
        flash('No valid results to upload', 'warning')
        return redirect(url_for('ocr.review_job', job_id=job.id))
    
    count = 0
    errors = []
    
    for result in valid_results:
        try:
            # Get final values (corrected or extracted)
            title = result.final_tajuk_buku
            author = result.final_pengarang
            publisher = result.final_penerbit
            accession = result.final_no_perolehan
            call_number = result.final_no_panggilan
            
            # Skip if title missing
            if not title or not accession:
                errors.append(f'Row {result.row_number}: Missing title or accession number')
                continue
            
            # Check for duplicate accession
            existing_copy = BookCopy.query.filter_by(accession_number=accession).first()
            if existing_copy:
                errors.append(f'Row {result.row_number}: Accession {accession} already in database')
                continue
            
            # Create or find Book
            book = Book.query.filter_by(title=title, author=author).first()
            if not book:
                book = Book(
                    title=title,
                    author=author or '',
                    publisher=publisher or '',
                    isbn='',
                    description=result.final_catatan or ''
                )
                db.session.add(book)
                db.session.flush()
            
            # Create BookCopy with accession info
            copy = BookCopy(
                book_id=book.id,
                accession_number=accession,
                call_number=call_number or '',
                status='available',
                location='Library',
                isbn=''
            )
            db.session.add(copy)
            count += 1
        
        except Exception as e:
            errors.append(f'Row {result.row_number}: {str(e)}')
    
    if count > 0:
        db.session.commit()
        job.mark_committed()
        db.session.commit()
    
    # Flash messages
    if errors:
        flash(f'Uploaded {count} books. Issues with {len(errors)} rows:', 'warning')
        for error in errors[:5]:
            flash(error, 'error')
    else:
        flash(f'Successfully uploaded {count} books to database', 'success')
    
    return redirect(url_for('ocr.view_job', job_id=job.id))


@ocr_bp.route('/job/<int:job_id>/delete', methods=['POST'])
@login_required
@permission_required(Permission.OCR_APPROVE)
def delete_job(job_id):
    """Delete an OCR job"""
    job = OCRJob.query.get_or_404(job_id)
    
    # Delete source file
    if os.path.exists(job.source_path):
        try:
            os.remove(job.source_path)
        except:
            pass
    
    db.session.delete(job)
    db.session.commit()
    
    flash('OCR job deleted', 'success')
    return redirect(url_for('ocr.index'))


# ============================================
# AI Correction API Endpoints
# ============================================

@ocr_bp.route('/api/suggest/member', methods=['POST'])
@login_required
@permission_required(Permission.OCR_DIGITIZE)
def suggest_member():
    """API endpoint for AI member ID suggestions"""
    data = request.get_json()
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'suggestions': []})
    
    correction_service = OCRCorrectionService()
    result = correction_service.correct_member_id(query)
    
    if result['match']:
        suggestions = [{
            'id': result['match'],
            'name': result.get('member_name', ''),
            'confidence': result['confidence'],
            'display': f"{result['match']} - {result.get('member_name', '')} ({result['confidence']:.0%})"
        }]
        
        # Add alternatives
        for alt in result.get('alternatives', [])[:4]:
            suggestions.append({
                'id': alt['id'],
                'name': alt.get('name', ''),
                'confidence': alt['confidence'],
                'display': f"{alt['id']} - {alt.get('name', '')} ({alt['confidence']:.0%})"
            })
        
        return jsonify({'suggestions': suggestions})
    
    return jsonify({'suggestions': []})


@ocr_bp.route('/api/suggest/book', methods=['POST'])
@login_required
@permission_required(Permission.OCR_DIGITIZE)
def suggest_book():
    """API endpoint for AI book ID suggestions"""
    data = request.get_json()
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'suggestions': []})
    
    correction_service = OCRCorrectionService()
    result = correction_service.correct_book_id(query)
    
    if result['match']:
        suggestions = [{
            'id': result['match'],
            'title': result.get('book_title', ''),
            'confidence': result['confidence'],
            'display': f"{result['match']} - {result.get('book_title', '')} ({result['confidence']:.0%})"
        }]
        
        # Add alternatives
        for alt in result.get('alternatives', [])[:4]:
            suggestions.append({
                'id': alt['id'],
                'title': alt.get('title', ''),
                'confidence': alt['confidence'],
                'display': f"{alt['id']} - {alt.get('title', '')} ({alt['confidence']:.0%})"
            })
        
        return jsonify({'suggestions': suggestions})
    
    return jsonify({'suggestions': []})


@ocr_bp.route('/api/autocomplete', methods=['GET'])
@login_required
@permission_required(Permission.OCR_DIGITIZE)
def autocomplete():
    """API endpoint for autocomplete suggestions"""
    query = request.args.get('q', '').strip()
    field_type = request.args.get('type', 'all')  # 'member', 'book', or 'all'
    
    if not query or len(query) < 2:
        return jsonify({'suggestions': []})
    
    correction_service = OCRCorrectionService()
    suggestions = correction_service.get_all_suggestions(query, field_type)
    
    return jsonify({'suggestions': suggestions})


# ============ Excel Ledger Import ============

@ocr_bp.route('/import-ledger', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.ADMIN)
def import_ledger():
    """Import book ledger data from Excel file"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return render_template('ocr/import_ledger.html')
        
        file = request.files['file']
        filepath, error = save_upload_file(file)
        
        if error:
            flash(f'Upload error: {error}', 'error')
            return render_template('ocr/import_ledger.html')
        
        # Preview mode - show what will be imported
        preview = request.form.get('preview')
        if preview == 'on':
            rows, error = read_excel_file(filepath)
            if error:
                flash(f'Error reading file: {error}', 'error')
            else:
                return render_template('ocr/import_ledger_preview.html', 
                                     rows=rows, 
                                     filepath=filepath)
        
        # Actual import
        success_count, errors, imported = import_ocr_ledger_data(filepath)
        
        if success_count > 0:
            flash(f'Successfully imported {success_count} book records', 'success')
        
        if errors:
            for error in errors[:5]:  # Show first 5 errors
                flash(f'Import error: {error}', 'warning')
            if len(errors) > 5:
                flash(f'... and {len(errors) - 5} more errors', 'warning')
        
        return redirect(url_for('ocr.index'))
    
    return render_template('ocr/import_ledger.html')
