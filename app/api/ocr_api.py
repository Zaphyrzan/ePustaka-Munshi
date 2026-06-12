"""
OCR API Routes - JSON endpoints for ledger digitization jobs and review.

Mirrors app/routes/ocr.py behavior (incremental commits, page caps, barcode
generation) by reusing its helpers. OCR *processing* requires local binaries
(Poppler/Tesseract) and the Anthropic key, so upload/process endpoints work
on the locally-run Flask app; review/commit endpoints work anywhere.
"""
import os
from datetime import datetime

from flask import Blueprint, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app import db
from app.models import OCRJob, OCRResult, OCRJobStatus, Permission
from app.utils.serializers import ApiResponse

bp = Blueprint('api_ocr', __name__, url_prefix='/api/ocr')


def _require(perm):
    """Permission gate matching the web OCR routes"""
    if not (hasattr(current_user, 'can') and current_user.can(perm)):
        return ApiResponse.error('Insufficient permissions', status_code=403)
    return None


def _paginate(query, default_per_page=50, max_per_page=200):
    page = max(request.args.get('page', 1, type=int), 1)
    per_page = min(max(request.args.get('per_page', default_per_page, type=int), 1), max_per_page)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    total_pages = (total + per_page - 1) // per_page
    return items, {
        'page': page,
        'per_page': per_page,
        'total': total,
        'total_pages': total_pages,
        'has_next': page < total_pages,
        'has_prev': page > 1,
    }


def _job_summary(job):
    data = job.to_dict()
    data['result_count'] = job.results.count()
    data['reviewed_count'] = job.results.filter(OCRResult.is_reviewed == True).count()
    data['committed_count'] = job.results.filter(OCRResult.committed_ledger_id.isnot(None)).count()
    data['ready_to_commit'] = job.results.filter(
        OCRResult.is_reviewed == True,
        OCRResult.is_valid == True,
        OCRResult.committed_ledger_id.is_(None),
    ).count()
    return data


@bp.route('/jobs', methods=['GET'])
@login_required
def list_jobs():
    """Paginated OCR jobs, newest first"""
    denied = _require(Permission.OCR_DIGITIZE)
    if denied:
        return denied
    query = OCRJob.query.order_by(OCRJob.created_at.desc())
    jobs, pagination = _paginate(query, default_per_page=20, max_per_page=100)
    return ApiResponse.success({'items': [_job_summary(j) for j in jobs], 'pagination': pagination})


@bp.route('/jobs/<int:job_id>', methods=['GET'])
@login_required
def get_job(job_id):
    denied = _require(Permission.OCR_DIGITIZE)
    if denied:
        return denied
    job = OCRJob.query.get(job_id)
    if not job:
        return ApiResponse.error('Job not found', status_code=404)
    return ApiResponse.success(_job_summary(job))


@bp.route('/jobs/<int:job_id>/results', methods=['GET'])
@login_required
def list_results(job_id):
    """Paginated extraction rows for review.

    Query params: page, per_page, status=pending|reviewed|committed (optional),
    page_number (optional ledger page filter).
    """
    denied = _require(Permission.OCR_DIGITIZE)
    if denied:
        return denied
    job = OCRJob.query.get(job_id)
    if not job:
        return ApiResponse.error('Job not found', status_code=404)

    query = job.results.order_by(OCRResult.page_number, OCRResult.row_number)
    status = request.args.get('status', '').strip()
    if status == 'pending':
        query = query.filter(OCRResult.is_reviewed == False)
    elif status == 'reviewed':
        query = query.filter(OCRResult.is_reviewed == True, OCRResult.committed_ledger_id.is_(None))
    elif status == 'committed':
        query = query.filter(OCRResult.committed_ledger_id.isnot(None))
    ledger_page = request.args.get('page_number', type=int)
    if ledger_page:
        query = query.filter(OCRResult.page_number == ledger_page)

    results, pagination = _paginate(query)
    items = []
    for r in results:
        d = r.to_dict()
        d['committed'] = r.committed_ledger_id is not None
        items.append(d)
    return ApiResponse.success({'items': items, 'pagination': pagination})


@bp.route('/results/<int:result_id>', methods=['PUT'])
@login_required
def update_result(result_id):
    """Save corrections + review status for one row.

    Request JSON: ledger fields (no_perolehan, tajuk_buku, ...) plus
    is_valid (bool) and notes (optional).
    """
    denied = _require(Permission.OCR_APPROVE)
    if denied:
        return denied
    result = OCRResult.query.get(result_id)
    if not result:
        return ApiResponse.error('Result not found', status_code=404)
    if result.committed_ledger_id:
        return ApiResponse.error('Row already committed; it is read-only', status_code=409)

    from app.routes.ocr import _corrections_from_form
    data = request.get_json(silent=True) or {}
    # Plain dicts share .get with form objects, so the web helper works as-is
    corrections = _corrections_from_form({k: (str(v) if v is not None else '') for k, v in data.items()})
    is_valid = bool(data.get('is_valid', True))
    notes = (data.get('notes') or '').strip() or None

    result.mark_reviewed(is_valid, corrections, notes)
    db.session.commit()
    d = result.to_dict()
    d['committed'] = False
    return ApiResponse.success(d, message='Row updated')


@bp.route('/results/<int:result_id>/commit', methods=['POST'])
@login_required
def commit_result(result_id):
    """Save (optional corrections in body) and upload one row to the catalog"""
    denied = _require(Permission.OCR_APPROVE)
    if denied:
        return denied
    result = OCRResult.query.get(result_id)
    if not result:
        return ApiResponse.error('Result not found', status_code=404)
    if result.committed_ledger_id:
        return ApiResponse.error('Row already committed', status_code=409)

    from app.routes.ocr import _commit_result_row, _corrections_from_form
    data = request.get_json(silent=True) or {}
    corrections = _corrections_from_form({k: (str(v) if v is not None else '') for k, v in data.items()})
    result.mark_reviewed(True, corrections, (data.get('notes') or '').strip() or None)

    job = result.job
    error = _commit_result_row(job, result)
    if error:
        db.session.commit()  # keep review state even when the commit failed
        return ApiResponse.error(error, status_code=422)

    if job.results.filter(OCRResult.committed_ledger_id.is_(None)).count() == 0:
        job.mark_committed()
    db.session.commit()
    d = result.to_dict()
    d['committed'] = True
    return ApiResponse.success(d, message=f'Row {result.row_number} uploaded to catalog')


@bp.route('/jobs/<int:job_id>/bulk-review', methods=['POST'])
@login_required
def bulk_review(job_id):
    """Mark all unreviewed, uncommitted rows reviewed+valid in one call"""
    denied = _require(Permission.OCR_APPROVE)
    if denied:
        return denied
    job = OCRJob.query.get(job_id)
    if not job:
        return ApiResponse.error('Job not found', status_code=404)

    pending = job.results.filter(
        OCRResult.is_reviewed == False,
        OCRResult.committed_ledger_id.is_(None),
    ).all()
    for result in pending:
        result.mark_reviewed(True)
    db.session.commit()
    return ApiResponse.success(_job_summary(job), message=f'Marked {len(pending)} rows reviewed')


@bp.route('/jobs/<int:job_id>/commit', methods=['POST'])
@login_required
def commit_job(job_id):
    """Incremental batch commit: upload all reviewed+valid, uncommitted rows"""
    denied = _require(Permission.OCR_APPROVE)
    if denied:
        return denied
    job = OCRJob.query.get(job_id)
    if not job:
        return ApiResponse.error('Job not found', status_code=404)

    from app.routes.ocr import _commit_result_row
    valid_results = job.results.filter(
        OCRResult.is_reviewed == True,
        OCRResult.is_valid == True,
        OCRResult.committed_ledger_id.is_(None),
    ).all()
    if not valid_results:
        return ApiResponse.error('No reviewed rows ready to commit', status_code=400)

    count, errors = 0, []
    for result in valid_results:
        error = _commit_result_row(job, result)
        if error:
            errors.append(error)
        else:
            count += 1

    remaining = job.results.filter(OCRResult.committed_ledger_id.is_(None)).count()
    if count > 0:
        if remaining == 0:
            job.mark_committed()
        db.session.commit()
    else:
        db.session.rollback()

    return ApiResponse.success(
        {'committed': count, 'errors': errors[:10], 'remaining': remaining, 'job': _job_summary(job)},
        message=f'Uploaded {count} books' + (f', {len(errors)} rows had issues' if errors else ''),
    )


@bp.route('/jobs/<int:job_id>', methods=['DELETE'])
@login_required
def delete_job(job_id):
    denied = _require(Permission.OCR_APPROVE)
    if denied:
        return denied
    job = OCRJob.query.get(job_id)
    if not job:
        return ApiResponse.error('Job not found', status_code=404)
    if job.source_path and os.path.exists(job.source_path):
        try:
            os.remove(job.source_path)
        except OSError:
            pass
    db.session.delete(job)
    db.session.commit()
    return ApiResponse.success(message='Job deleted')


@bp.route('/jobs', methods=['POST'])
@login_required
def create_job():
    """Upload a scan (multipart 'file') and create a pending job.

    Enforces the same OCR_WEB_MAX_PAGES cap as the web uploader.
    Only meaningful on the locally-run Flask app (needs Poppler for PDFs).
    """
    denied = _require(Permission.OCR_DIGITIZE)
    if denied:
        return denied
    if 'file' not in request.files or not request.files['file'].filename:
        return ApiResponse.error('No file uploaded', status_code=400)

    file = request.files['file']
    from app.routes.ocr import allowed_file
    if not allowed_file(file.filename):
        return ApiResponse.error('File type not allowed', status_code=400)

    from app.services import ScannerServiceFactory
    upload_folder = current_app.config['OCR_UPLOAD_FOLDER']
    file_service = ScannerServiceFactory(upload_folder).get_file_import_service()
    original_filename = secure_filename(file.filename)
    scanned_image = file_service.import_uploaded_file(file, original_filename)

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
            return ApiResponse.error(
                f'This PDF has {page_count} pages; uploads are limited to {max_pages} '
                f'pages per job. Use the batch processor for full ledgers.',
                status_code=413,
            )

    job_name = (request.form.get('job_name') or '').strip() or f'Scan_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    job = OCRJob(
        job_name=job_name,
        source_type='file_upload',
        source_path=scanned_image.file_path,
        original_filename=original_filename,
        page_count=page_count,
        status=OCRJobStatus.PENDING.value,
        created_by=current_user.id,
    )
    db.session.add(job)
    db.session.commit()
    return ApiResponse.success(_job_summary(job), message='File uploaded', status_code=201)


@bp.route('/jobs/<int:job_id>/process', methods=['POST'])
@login_required
def process_job(job_id):
    """Run OCR on a pending job (local Flask only - needs vision engine).

    Request JSON (optional): {"engine": "vision"|"tesseract"}
    """
    denied = _require(Permission.OCR_DIGITIZE)
    if denied:
        return denied
    job = OCRJob.query.get(job_id)
    if not job:
        return ApiResponse.error('Job not found', status_code=404)
    if job.status not in [OCRJobStatus.PENDING.value, OCRJobStatus.FAILED.value]:
        return ApiResponse.error('Job cannot be processed in its current state', status_code=409)

    # Delegate to the web route logic by calling the same engines it uses
    from app.routes.ocr import process_job as web_process_job  # noqa: F401 (documentation)
    from app.services import OCRService, VisionOCRService

    data = request.get_json(silent=True) or {}
    engine_name = (data.get('engine') or 'vision').strip()

    try:
        if engine_name == 'vision':
            engine = VisionOCRService(
                api_key=current_app.config.get('ANTHROPIC_API_KEY'),
                model=data.get('model') or current_app.config.get('OCR_VISION_MODEL'),
            )
            if not engine.is_available():
                return ApiResponse.error(
                    'Vision OCR unavailable here (no ANTHROPIC_API_KEY). '
                    'Process on the local scanning station.',
                    status_code=503,
                )
            result_data = engine.process_file(job.source_path)
        else:
            engine = OCRService(tesseract_cmd=current_app.config.get('TESSERACT_CMD'))
            result_data = engine.process_file(job.source_path)

        job.status = OCRJobStatus.PROCESSING.value
        db.session.commit()

        for row in result_data.get('rows', []):
            db.session.add(OCRResult(
                job_id=job.id,
                page_number=row.get('page_number', 1),
                row_number=row.get('row_number'),
                raw_text=row.get('raw_text'),
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
                confidence_overall=row.get('confidence', 0.0),
            ))
        job.page_count = result_data.get('pages', job.page_count)
        job.ocr_config = {'engine': engine_name, 'model': getattr(engine, 'model', None)}
        job.mark_completed()
        db.session.commit()
        return ApiResponse.success(_job_summary(job), message=f'{result_data.get("total_rows", 0)} rows extracted')

    except Exception as e:
        db.session.rollback()
        job.status = OCRJobStatus.FAILED.value
        job.error_message = str(e)
        db.session.commit()
        current_app.logger.error(f'OCR process error: {e}')
        return ApiResponse.error(str(e), status_code=500)
