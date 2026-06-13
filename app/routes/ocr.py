"""
OCR routes - Ledger digitization
"""
import os
import re
import json
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models import OCRJob, OCRResult, OCRJobStatus, Loan, Member, BookCopy, Permission
from app.services import ScannerServiceFactory, OCRService, OCRCorrectionService, VisionOCRService
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


def _truncate(value, max_len):
    """Trim a value to a catalog column limit (Postgres rejects overlong strings)"""
    if value is None:
        return None
    value = str(value).strip()
    return value[:max_len] if value else None


def _parse_year(value):
    """Extract a 4-digit year from a ledger date string like '2003' or 'KL: 12/2003'"""
    if not value:
        return None
    match = re.search(r'\b(1[89]\d{2}|20\d{2})\b', str(value))
    return int(match.group(1)) if match else None


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

        # PDFs are processed synchronously in one web request, so reject page
        # counts that would hang the browser and burn API credits unattended.
        page_count = 1
        if original_filename.lower().endswith('.pdf'):
            try:
                from pdf2image.pdf2image import pdfinfo_from_path
                from app.services.vision_ocr_service import _find_poppler
                info = pdfinfo_from_path(scanned_image.file_path, poppler_path=_find_poppler())
                page_count = int(info.get('Pages', 1))
            except Exception:
                page_count = 1
            max_pages = current_app.config.get('OCR_WEB_MAX_PAGES', 10)
            if page_count > max_pages:
                try:
                    os.remove(scanned_image.file_path)
                except OSError:
                    pass
                flash(
                    f'This PDF has {page_count} pages; web uploads are limited to '
                    f'{max_pages} pages per job. For full ledgers, use the batch '
                    f'processor (scripts/process_job_cli.py), which runs page by '
                    f'page and can resume.',
                    'error',
                )
                return render_template('ocr/upload.html')

        # Create OCR job
        job_name = request.form.get('job_name', '').strip() or f'Scan_{datetime.now().strftime("%Y%m%d_%H%M%S")}'

        job = OCRJob(
            job_name=job_name,
            source_type='file_upload',
            source_path=scanned_image.file_path,
            original_filename=original_filename,
            page_count=page_count,
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

    # Engine selection: Claude vision reads the handwritten ledgers; Tesseract
    # remains available as the printed-text/research baseline (engine=tesseract)
    tesseract_cmd = current_app.config.get('TESSERACT_CMD')
    engine = request.form.get('engine', 'vision')

    vision_service = VisionOCRService(
        api_key=current_app.config.get('ANTHROPIC_API_KEY'),
        model=current_app.config.get('OCR_VISION_MODEL'),
        tesseract_cmd=tesseract_cmd
    )

    if engine == 'vision' and vision_service.is_available():
        ocr_service = vision_service
    else:
        if engine == 'vision':
            flash('Vision OCR not configured (set ANTHROPIC_API_KEY). Falling back to Tesseract.', 'warning')
        ocr_service = OCRService(tesseract_cmd=tesseract_cmd)
        if not ocr_service.is_available():
            flash('OCR service (Tesseract) is not available. Please install Tesseract OCR.', 'error')
            return redirect(url_for('ocr.view_job', job_id=job.id))

    try:
        job.mark_processing()
        # Record the engine used so results can be compared per-engine later
        job.ocr_config = json.dumps({
            'engine': 'vision' if isinstance(ocr_service, VisionOCRService) else 'tesseract',
            'model': getattr(ocr_service, 'model', None)
        })
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

    # Rows reviewed + approved but not yet committed - enables batch commits
    ready_to_commit = job.results.filter(
        OCRResult.is_reviewed == True,
        OCRResult.is_valid == True,
        OCRResult.committed_ledger_id.is_(None),
    ).count()

    return render_template('ocr/review_job.html', job=job, results=results,
                           ready_to_commit=ready_to_commit)


def _corrections_from_form(form):
    """Collect non-empty ledger field corrections from a review form"""
    corrections = {}
    for field in ['no_perolehan', 'no_panggilan', 'pengarang', 'tajuk_buku',
                  'penerbit', 'tarikh_penerbit', 'punca',
                  'tarikh_perolehan', 'bil_no', 'harga', 'muka_surat', 'catatan']:
        value = form.get(field, '').strip()
        if value:
            corrections[field] = value
    return corrections


@ocr_bp.route('/result/<int:result_id>/update', methods=['POST'])
@login_required
@permission_required(Permission.OCR_APPROVE)
def update_result(result_id):
    """Update ledger extraction with corrections"""
    result = OCRResult.query.get_or_404(result_id)

    # The form posts a hidden false plus the checkbox true; the checkbox wins.
    # (form.get returns only the FIRST value, which is always the hidden false)
    is_valid = 'true' in request.form.getlist('is_valid')
    corrections = _corrections_from_form(request.form)

    notes = request.form.get('notes', '').strip()
    result.mark_reviewed(is_valid, corrections, notes)
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})
    
    flash('Result updated', 'success')
    return redirect(url_for('ocr.review_job', job_id=result.job_id))


def _commit_result_row(job, result):
    """Turn one reviewed ledger row into Book + BookCopy + DigitizedLedger.

    Runs in a savepoint so a failing row rolls back alone. Returns an error
    message, or None on success. Caller is responsible for db.session.commit().
    """
    from app.models import Book, BookCopy
    from app.models.ocr import DigitizedLedger
    from app.utils.barcode_utils import generate_barcode
    from app.utils.text_format import to_caps

    # Final values (corrected or extracted), trimmed to catalog column limits.
    # Descriptive fields stored UPPERCASE per school policy.
    title = to_caps(_truncate(result.final_tajuk_buku, 256))
    author = to_caps(_truncate(result.final_pengarang, 256)) or ''
    accession = _truncate(result.final_no_perolehan, 32)

    if not title or not accession:
        return f'Row {result.row_number}: Missing title or accession number'

    # Skip rows whose accession is already catalogued (re-commit safety)
    if BookCopy.query.filter_by(accession_number=accession).first():
        return f'Row {result.row_number}: Accession {accession} already in database'

    try:
        with db.session.begin_nested():
            # Reuse the title-level record if it exists, else create it
            # (mirrors the CRUD add-book flow in catalog.add_book)
            book = Book.query.filter_by(title=title, author=author).first()
            if not book:
                book = Book(
                    title=title,
                    author=author,
                    publisher=to_caps(_truncate(result.final_penerbit, 128)),
                    call_number=_truncate(result.final_no_panggilan, 32),
                    publication_year=_parse_year(result.final_tarikh_penerbit),
                    page_count=result.final_muka_surat,
                    price=result.final_harga
                )
                db.session.add(book)
                db.session.flush()  # Get book.id for the copy below

            # Physical copy carries the acquisition details from the ledger.
            # Barcode mirrors the CRUD add-copy flow so scanner-based
            # checkout/return works for OCR-committed books too.
            copy = BookCopy(
                book_id=book.id,
                accession_number=accession,
                barcode=generate_barcode(accession),
                status='available',
                location='Library',
                acquisition_date=result.final_tarikh_perolehan,
                acquisition_source=_truncate(result.final_punca, 64),
                price=result.final_harga,
                notes=result.final_catatan
            )
            db.session.add(copy)

            # Archive the full ledger row for scan-to-book traceability
            ledger = DigitizedLedger(
                source_job_id=job.id,
                source_result_id=result.id,
                no_perolehan=result.final_no_perolehan,
                no_panggilan=result.final_no_panggilan,
                pengarang=result.final_pengarang,
                tajuk_buku=result.final_tajuk_buku,
                penerbit=result.final_penerbit,
                tarikh_penerbit=result.final_tarikh_penerbit,
                tarikh_perolehan=result.final_tarikh_perolehan,
                bil_no=result.final_bil_no,
                punca=result.final_punca,
                harga=result.final_harga,
                muka_surat=result.final_muka_surat,
                catatan=result.final_catatan,
                linked_book_id=book.id,
                created_by=current_user.id
            )
            db.session.add(ledger)
            db.session.flush()  # Get copy.id and ledger.id
            ledger.linked_copy_id = copy.id
            result.committed_ledger_id = ledger.id

    except Exception as e:
        return f'Row {result.row_number}: {str(e)}'
    return None


@ocr_bp.route('/job/<int:job_id>/commit', methods=['POST'])
@login_required
@permission_required(Permission.OCR_APPROVE)
def commit_job(job_id):
    """Commit reviewed ledger rows to the catalog (Book + BookCopy) and the DigitizedLedger archive"""
    job = OCRJob.query.get_or_404(job_id)

    # Incremental commit: take rows that are reviewed, approved, and not yet
    # committed. Unreviewed rows simply wait for a later commit, so large jobs
    # can be committed in batches instead of all-or-nothing.
    valid_results = job.results.filter(
        OCRResult.is_reviewed == True,
        OCRResult.is_valid == True,
        OCRResult.committed_ledger_id.is_(None),
    ).all()
    if not valid_results:
        flash('No reviewed rows ready to commit. Review and approve rows first - '
              'you can commit in batches.', 'warning')
        return redirect(url_for('ocr.review_job', job_id=job.id))

    count = 0
    errors = []

    for result in valid_results:
        error = _commit_result_row(job, result)
        if error:
            errors.append(error)
        else:
            count += 1

    remaining = job.results.filter(OCRResult.committed_ledger_id.is_(None)).count()
    if count > 0:
        # Only seal the job once every row is committed; otherwise keep it
        # reviewable so the next batch can be committed later.
        if remaining == 0:
            job.mark_committed()
        db.session.commit()
    else:
        db.session.rollback()

    # Flash messages
    if errors:
        flash(f'Uploaded {count} books. Issues with {len(errors)} rows:', 'warning')
        for error in errors[:5]:
            flash(error, 'error')
    elif remaining > 0:
        flash(f'Successfully uploaded {count} books. {remaining} rows not yet '
              f'committed - review and commit them anytime.', 'success')
    else:
        flash(f'Successfully uploaded {count} books to database', 'success')

    return redirect(url_for('ocr.view_job', job_id=job.id))


@ocr_bp.route('/result/<int:result_id>/commit', methods=['POST'])
@login_required
@permission_required(Permission.OCR_APPROVE)
def commit_result(result_id):
    """Save one row's corrections and upload it to the catalog immediately"""
    result = OCRResult.query.get_or_404(result_id)
    job = result.job

    if result.committed_ledger_id:
        flash(f'Row {result.row_number} is already uploaded', 'warning')
        return redirect(url_for('ocr.review_job', job_id=job.id) + f'#row-{result.id}')

    # Apply any edits from the row form, mark reviewed+valid, then commit it
    result.mark_reviewed(True, _corrections_from_form(request.form),
                         request.form.get('notes', '').strip() or None)
    error = _commit_result_row(job, result)
    if error:
        db.session.commit()  # keep the review state even when the upload failed
        flash(error, 'error')
    else:
        if job.results.filter(OCRResult.committed_ledger_id.is_(None)).count() == 0:
            job.mark_committed()
        db.session.commit()
        flash(f'Row {result.row_number} uploaded to catalog', 'success')

    return redirect(url_for('ocr.review_job', job_id=job.id) + f'#row-{result.id}')


@ocr_bp.route('/job/<int:job_id>/bulk-review', methods=['POST'])
@login_required
@permission_required(Permission.OCR_APPROVE)
def bulk_review(job_id):
    """Mark every unreviewed row as reviewed and valid in one click.

    Extracted values become the final values; individual rows can still be
    corrected afterwards until they are committed.
    """
    job = OCRJob.query.get_or_404(job_id)

    pending = job.results.filter(
        OCRResult.is_reviewed == False,
        OCRResult.committed_ledger_id.is_(None),
    ).all()
    for result in pending:
        result.mark_reviewed(True)
    db.session.commit()

    flash(f'Marked {len(pending)} rows as reviewed and valid. '
          f'They are now ready to upload.', 'success')
    return redirect(url_for('ocr.review_job', job_id=job.id))


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
