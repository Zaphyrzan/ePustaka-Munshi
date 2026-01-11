"""
OCR routes - Ledger digitization for Malaysian library ledger format
"""
import os
import json
from datetime import datetime
from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models import OCRJob, OCRResult, OCRJobStatus, DigitizedLedger, Book, BookCopy, Permission
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
    """Run OCR processing on a job - extracts Malaysian ledger format"""
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
            
            # Create OCR result with Malaysian ledger fields
            ocr_result = OCRResult(
                job_id=job.id,
                page_number=row.get('page_number', 1),
                row_number=row.get('row_number'),
                raw_text=row.get('raw_text'),
                
                # Malaysian ledger fields - extracted
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
                
                # Confidence
                confidence_overall=row.get('confidence', 0.0)
            )
            
            # Store AI suggestions in notes for review
            ai_notes = []
            
            # Apply high-confidence AI corrections automatically
            if corrected.get('suggested_no_perolehan'):
                conf = corrected.get('ai_corrections', {}).get('no_perolehan', {}).get('confidence', 0)
                if conf >= 0.8:
                    ocr_result.no_perolehan_corrected = corrected['suggested_no_perolehan']
                    ai_notes.append(f"No Perolehan auto-corrected ({conf:.0%})")
            
            if corrected.get('suggested_tajuk_buku'):
                conf = corrected.get('ai_corrections', {}).get('tajuk_buku', {}).get('confidence', 0)
                if conf >= 0.7:
                    ocr_result.tajuk_buku_corrected = corrected['suggested_tajuk_buku']
                    ai_notes.append(f"Title matched from database ({conf:.0%})")
                    # Also fill in related author if matched
                    if corrected.get('suggested_pengarang'):
                        ocr_result.pengarang_corrected = corrected['suggested_pengarang']
            
            if corrected.get('suggested_penerbit'):
                conf = corrected.get('ai_corrections', {}).get('penerbit', {}).get('confidence', 0)
                if conf >= 0.7:
                    ocr_result.penerbit_corrected = corrected['suggested_penerbit']
            
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
    
    return render_template('ocr/review_job.html', job=job, results=results)


@ocr_bp.route('/result/<int:result_id>/update', methods=['POST'])
@login_required
@permission_required(Permission.OCR_APPROVE)
def update_result(result_id):
    """Update a single OCR result with Malaysian ledger fields"""
    result = OCRResult.query.get_or_404(result_id)
    
    is_valid = request.form.get('is_valid') == 'true'
    corrections = {}
    
    # Collect all Malaysian ledger field corrections
    for field in ['no_perolehan', 'no_panggilan', 'pengarang', 'tajuk_buku', 
                  'penerbit', 'tarikh_penerbit', 'tarikh_perolehan', 'bil_no',
                  'punca', 'harga', 'muka_surat', 'catatan']:
        value = request.form.get(field, '').strip()
        if value:
            corrections[field] = value
    
    notes = request.form.get('notes', '').strip()
    
    result.mark_reviewed(is_valid, corrections, notes)
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})
    
    flash('Rekod dikemaskini', 'success')
    return redirect(url_for('ocr.review_job', job_id=result.job_id))


@ocr_bp.route('/job/<int:job_id>/commit', methods=['POST'])
@login_required
@permission_required(Permission.OCR_APPROVE)
def commit_job(job_id):
    """Commit validated OCR results to the Digitized Ledger database"""
    job = OCRJob.query.get_or_404(job_id)
    
    # Get valid, reviewed results
    valid_results = job.results.filter(
        OCRResult.is_reviewed == True,
        OCRResult.is_valid == True,
        OCRResult.committed_ledger_id == None
    ).all()
    
    if not valid_results:
        flash('Tiada rekod yang sah untuk disimpan', 'warning')
        return redirect(url_for('ocr.view_job', job_id=job.id))
    
    committed = 0
    errors = []
    
    for result in valid_results:
        try:
            # Get final values (corrected or extracted)
            no_perolehan = result.final_no_perolehan
            
            if not no_perolehan:
                errors.append(f'Baris {result.row_number}: No Perolehan diperlukan')
                continue
            
            tajuk_buku = result.final_tajuk_buku
            if not tajuk_buku:
                errors.append(f'Baris {result.row_number}: Tajuk buku diperlukan')
                continue
            
            # Check for duplicate accession number
            existing = DigitizedLedger.query.filter_by(no_perolehan=no_perolehan).first()
            if existing:
                errors.append(f'Baris {result.row_number}: No Perolehan {no_perolehan} sudah wujud')
                continue
            
            # Create digitized ledger entry
            ledger_entry = DigitizedLedger(
                source_job_id=job.id,
                source_result_id=result.id,
                no_perolehan=no_perolehan,
                no_panggilan=result.final_no_panggilan,
                pengarang=result.final_pengarang,
                tajuk_buku=tajuk_buku,
                penerbit=result.final_penerbit,
                tarikh_penerbit=result.final_tarikh_penerbit,
                tarikh_perolehan=result.final_tarikh_perolehan,
                bil_no=result.final_bil_no,
                punca=result.final_punca,
                harga=Decimal(str(result.final_harga)) if result.final_harga else None,
                muka_surat=result.final_muka_surat,
                catatan=result.final_catatan,
                created_by=current_user.id
            )
            
            db.session.add(ledger_entry)
            db.session.flush()  # Get ledger ID
            
            result.committed_ledger_id = ledger_entry.id
            committed += 1
            
        except Exception as e:
            errors.append(f'Baris {result.row_number}: {str(e)}')
    
    if committed > 0:
        job.mark_committed()
    
    db.session.commit()
    
    if errors:
        flash(f'Berjaya simpan {committed} rekod. Ralat: {len(errors)}', 'warning')
        for error in errors[:5]:  # Show first 5 errors
            flash(error, 'error')
    else:
        flash(f'Berjaya simpan {committed} rekod ke Daftar Buku Perpustakaan', 'success')
    
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
# API Endpoints for Malaysian Ledger Review
# ============================================

@ocr_bp.route('/api/suggest', methods=['POST'])
@login_required
@permission_required(Permission.OCR_DIGITIZE)
def api_suggest():
    """API endpoint for AI field suggestions (Malaysian ledger fields)"""
    data = request.get_json()
    field = data.get('field', '')
    value = data.get('value', '').strip()
    
    if not value or len(value) < 2:
        return jsonify({'suggestions': []})
    
    correction_service = OCRCorrectionService()
    result = correction_service.suggest_from_partial(field, value)
    
    suggestions = []
    
    if field == 'tajuk_buku':
        for s in result.get('suggestions', [])[:5]:
            suggestions.append({
                'value': s.get('title', ''),
                'display': s.get('title', ''),
                'author': s.get('author'),
                'publisher': None,
                'similarity': s.get('similarity', 0)
            })
    elif field == 'pengarang':
        for s in result.get('suggestions', [])[:5]:
            suggestions.append({
                'value': s.get('author', ''),
                'display': s.get('author', ''),
                'similarity': s.get('similarity', 0)
            })
    elif field == 'penerbit':
        for s in result.get('suggestions', [])[:5]:
            suggestions.append({
                'value': s,
                'display': s,
                'similarity': 0.8
            })
    elif field == 'no_panggilan':
        for s in result.get('suggestions', [])[:5]:
            suggestions.append({
                'value': s.get('call_number', ''),
                'display': f"{s.get('call_number', '')} - {s.get('title', '')[:40]}",
                'title': s.get('title'),
                'similarity': s.get('similarity', 0)
            })
    
    # Also return best match if available
    related = {}
    if result.get('best_match'):
        related['best_match'] = result['best_match']
        related['confidence'] = result.get('confidence', 0)
    if result.get('related_author'):
        related['author'] = result['related_author']
    if result.get('related_title'):
        related['title'] = result['related_title']
    
    return jsonify({'suggestions': suggestions, 'related': related})


@ocr_bp.route('/api/save-result', methods=['POST'])
@login_required
@permission_required(Permission.OCR_DIGITIZE)
def api_save_result():
    """API endpoint to save OCR result corrections"""
    data = request.get_json()
    result_id = data.get('result_id')
    
    if not result_id:
        return jsonify({'success': False, 'error': 'Missing result_id'})
    
    result = OCRResult.query.get(result_id)
    if not result:
        return jsonify({'success': False, 'error': 'Result not found'})
    
    # Update corrected fields
    if data.get('no_perolehan'):
        result.no_perolehan_corrected = data['no_perolehan']
    if data.get('no_panggilan'):
        result.no_panggilan_corrected = data['no_panggilan']
    if data.get('pengarang'):
        result.pengarang_corrected = data['pengarang']
    if data.get('tajuk_buku'):
        result.tajuk_buku_corrected = data['tajuk_buku']
    if data.get('penerbit'):
        result.penerbit_corrected = data['penerbit']
    if data.get('tarikh_penerbit'):
        result.tarikh_penerbit_corrected = data['tarikh_penerbit']
    if data.get('tarikh_perolehan'):
        # Try to parse as date or just store year
        tarikh = data['tarikh_perolehan']
        try:
            if len(tarikh) == 4:  # Just year
                result.tarikh_perolehan_corrected = datetime.strptime(tarikh, '%Y').date()
            else:
                result.tarikh_perolehan_corrected = datetime.strptime(tarikh, '%Y-%m-%d').date()
        except:
            pass
    if data.get('bil_no'):
        result.bil_no_corrected = data['bil_no']
    if data.get('punca'):
        result.punca_corrected = data['punca']
    if data.get('harga'):
        try:
            result.harga_rm_corrected = Decimal(data['harga'])
        except:
            pass
    if data.get('muka_surat'):
        try:
            result.muka_surat_corrected = int(data['muka_surat'])
        except:
            pass
    if data.get('catatan'):
        result.catatan_corrected = data['catatan']
    
    db.session.commit()
    
    return jsonify({'success': True})


@ocr_bp.route('/api/validate-result', methods=['POST'])
@login_required
@permission_required(Permission.OCR_APPROVE)
def api_validate_result():
    """API endpoint to validate/invalidate an OCR result"""
    data = request.get_json()
    result_id = data.get('result_id')
    is_valid = data.get('is_valid', False)
    
    if not result_id:
        return jsonify({'success': False, 'error': 'Missing result_id'})
    
    result = OCRResult.query.get(result_id)
    if not result:
        return jsonify({'success': False, 'error': 'Result not found'})
    
    result.is_reviewed = True
    result.is_valid = is_valid
    result.reviewed_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({'success': True})


@ocr_bp.route('/api/autocomplete', methods=['GET'])
@login_required
@permission_required(Permission.OCR_DIGITIZE)
def autocomplete():
    """API endpoint for autocomplete suggestions"""
    query = request.args.get('q', '').strip()
    field_type = request.args.get('type', 'title')  # 'title', 'author', 'publisher', 'call_number'
    
    if not query or len(query) < 2:
        return jsonify({'suggestions': []})
    
    correction_service = OCRCorrectionService()
    suggestions = correction_service.get_all_suggestions(query, field_type)
    
    return jsonify({'suggestions': suggestions})
