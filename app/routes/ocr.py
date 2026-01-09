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
                member_id_extracted=row.get('member_id'),
                member_name_extracted=row.get('member_name'),
                book_id_extracted=row.get('book_id'),
                book_title_extracted=row.get('book_title'),
                transaction_type=row.get('transaction_type'),
                date_extracted=row.get('date_text'),
                parsed_date=datetime.fromisoformat(row['parsed_date']).date() if row.get('parsed_date') else None,
                confidence_overall=row.get('confidence', 0.0)
            )
            
            # Store AI suggestions in notes for review
            ai_notes = []
            if corrected.get('suggested_member_id') and corrected['suggested_member_id'] != row.get('member_id'):
                ai_corrections = corrected.get('ai_corrections', {}).get('member', {})
                confidence = ai_corrections.get('confidence', 0)
                ai_notes.append(f"AI suggested member: {corrected['suggested_member_id']} ({confidence:.0%})")
                # Auto-apply high confidence corrections
                if confidence >= 0.8:
                    ocr_result.reviewed_member_id = corrected['suggested_member_id']
            
            if corrected.get('suggested_book_id') and corrected['suggested_book_id'] != row.get('book_id'):
                book_corrections = corrected.get('ai_corrections', {}).get('book', {})
                book_confidence = book_corrections.get('confidence', 0)
                ai_notes.append(f"AI suggested book: {corrected['suggested_book_id']} ({book_confidence:.0%})")
                # Auto-apply high confidence corrections
                if book_confidence >= 0.8:
                    ocr_result.reviewed_book_id = corrected['suggested_book_id']
            
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
    """Review and validate OCR results"""
    job = OCRJob.query.get_or_404(job_id)
    
    if job.status not in [OCRJobStatus.COMPLETED.value, OCRJobStatus.REVIEWED.value]:
        flash('Job must be completed before review', 'error')
        return redirect(url_for('ocr.view_job', job_id=job.id))
    
    results = job.results.order_by(OCRResult.page_number, OCRResult.row_number).all()
    
    # Get members and copies for validation dropdowns
    members = Member.query.filter_by(is_active=True).order_by(Member.member_id).all()
    
    return render_template('ocr/review_job.html', job=job, results=results, members=members)


@ocr_bp.route('/result/<int:result_id>/update', methods=['POST'])
@login_required
@permission_required(Permission.OCR_APPROVE)
def update_result(result_id):
    """Update a single OCR result"""
    result = OCRResult.query.get_or_404(result_id)
    
    is_valid = request.form.get('is_valid') == 'true'
    corrections = {}
    
    member_id = request.form.get('member_id', '').strip()
    if member_id:
        corrections['member_id'] = member_id
    
    book_id = request.form.get('book_id', '').strip()
    if book_id:
        corrections['book_id'] = book_id
    
    date_str = request.form.get('date', '').strip()
    if date_str:
        try:
            corrections['date'] = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    
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
    """Commit validated OCR results to loan records"""
    job = OCRJob.query.get_or_404(job_id)
    
    # Get valid, reviewed results
    valid_results = job.results.filter(
        OCRResult.is_reviewed == True,
        OCRResult.is_valid == True,
        OCRResult.committed_loan_id == None
    ).all()
    
    if not valid_results:
        flash('No valid results to commit', 'warning')
        return redirect(url_for('ocr.view_job', job_id=job.id))
    
    committed = 0
    errors = []
    
    for result in valid_results:
        try:
            # Find member
            member_id = result.final_member_id
            member = Member.query.filter_by(member_id=member_id).first()
            if not member:
                errors.append(f'Row {result.row_number}: Member {member_id} not found')
                continue
            
            # Find copy
            book_id = result.final_book_id
            copy = BookCopy.query.filter_by(accession_number=book_id).first()
            if not copy:
                errors.append(f'Row {result.row_number}: Book copy {book_id} not found')
                continue
            
            # Create historical loan record
            loan = Loan(
                member_id=member.id,
                copy_id=copy.id,
                checkout_date=datetime.combine(result.final_date, datetime.min.time()) if result.final_date else datetime.utcnow(),
                due_date=datetime.combine(result.final_date, datetime.min.time()) if result.final_date else datetime.utcnow(),
                status='returned',  # Historical records are marked as returned
                notes=f'Imported from OCR Job #{job.id}'
            )
            db.session.add(loan)
            db.session.flush()  # Get loan ID
            
            result.committed_loan_id = loan.id
            committed += 1
        
        except Exception as e:
            errors.append(f'Row {result.row_number}: {str(e)}')
    
    if committed > 0:
        job.mark_committed()
    
    db.session.commit()
    
    if errors:
        flash(f'Committed {committed} records. Errors: {len(errors)}', 'warning')
        for error in errors[:5]:  # Show first 5 errors
            flash(error, 'error')
    else:
        flash(f'Successfully committed {committed} records to loan history', 'success')
    
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
