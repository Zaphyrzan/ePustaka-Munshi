# -*- coding: utf-8 -*-
"""
CLI batch OCR processor - digitize big ledger PDFs outside the web request cycle.

The web route processes a whole job in one HTTP request, which times out on
multi-hundred-page PDFs. This script processes page by page, commits results
incrementally, and resumes where it left off if interrupted.

Usage:
    # Pilot: first 3 pages only
    python scripts/process_job_cli.py --pdf "C:\\path\\ledger.pdf" --name "Pilot" --pages 1-3

    # Full run (resumable - rerun with --job-id if interrupted)
    python scripts/process_job_cli.py --pdf "C:\\path\\ledger.pdf" --name "Ledger Vol 1"
    python scripts/process_job_cli.py --job-id 5

    # Tesseract baseline for the research comparison
    python scripts/process_job_cli.py --pdf "C:\\path\\ledger.pdf" --name "Baseline" --pages 1-3 --engine tesseract
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def parse_pages(spec, page_count):
    """'1-3' -> (1, 3); '5' -> (5, 5); None -> (1, page_count)"""
    if not spec:
        return 1, page_count
    if '-' in spec:
        start, end = spec.split('-', 1)
        return max(1, int(start)), min(page_count, int(end))
    page = int(spec)
    return page, page


def save_rows(db, OCRResult, job, rows):
    """Persist one page's rows (same mapping as the web route)"""
    for row in rows:
        result = OCRResult(
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
        )
        db.session.add(result)


def main():
    parser = argparse.ArgumentParser(description='Batch OCR processing for ledger PDFs')
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--pdf', help='PDF to digitize (creates a new job)')
    source.add_argument('--job-id', type=int, help='Existing job to process/resume')
    parser.add_argument('--name', help='Job name (with --pdf)')
    parser.add_argument('--pages', help="Page range, e.g. '1-3' or '7' (default: all)")
    parser.add_argument('--engine', choices=['vision', 'tesseract'], default='vision')
    parser.add_argument('--model', help='Override OCR_VISION_MODEL for this run')
    args = parser.parse_args()

    from pdf2image import convert_from_path, pdfinfo_from_path
    from app import create_app, db
    from app.models import OCRJob, OCRResult, OCRJobStatus, User
    from app.services import OCRService, VisionOCRService
    from app.services.vision_ocr_service import _find_poppler

    app = create_app(os.environ.get('FLASK_ENV', 'development'))
    with app.app_context():
        # ===== Resolve the job =====
        if args.pdf:
            pdf_path = os.path.abspath(args.pdf)
            if not os.path.exists(pdf_path):
                sys.exit(f'File not found: {pdf_path}')
            staff = User.query.first()  # audit stamp; CLI runs are staff-initiated
            job = OCRJob(
                job_name=args.name or os.path.basename(pdf_path),
                source_type='file_upload',
                source_path=pdf_path,
                original_filename=os.path.basename(pdf_path),
                status=OCRJobStatus.PENDING.value,
                created_by=staff.id if staff else None,
            )
            db.session.add(job)
            db.session.commit()
            print(f'Created job {job.id}: {job.job_name}')
        else:
            job = OCRJob.query.get(args.job_id)
            if not job:
                sys.exit(f'Job {args.job_id} not found')
            pdf_path = job.source_path
            if not os.path.exists(pdf_path):
                sys.exit(f'Source file missing: {pdf_path}')

        # ===== Set up the OCR engine =====
        tesseract_cmd = app.config.get('TESSERACT_CMD')
        if args.engine == 'vision':
            engine = VisionOCRService(
                api_key=app.config.get('ANTHROPIC_API_KEY'),
                model=args.model or app.config.get('OCR_VISION_MODEL'),
                tesseract_cmd=tesseract_cmd,
            )
            if not engine.is_available():
                sys.exit('Vision OCR not available - set ANTHROPIC_API_KEY in .env')
            print(f'Engine: vision ({engine.model})')
        else:
            engine = OCRService(tesseract_cmd=tesseract_cmd)
            if not engine.is_available():
                sys.exit('Tesseract not available')
            print('Engine: tesseract (baseline)')

        # ===== Page range and resume point =====
        poppler = _find_poppler()
        info = pdfinfo_from_path(pdf_path, poppler_path=poppler)
        first, last = parse_pages(args.pages, info['Pages'])

        # Resume: skip pages that already have saved results
        done_pages = {p for (p,) in db.session.query(OCRResult.page_number)
                      .filter(OCRResult.job_id == job.id).distinct()}
        todo = [p for p in range(first, last + 1) if p not in done_pages]
        if not todo:
            print('All requested pages already processed.')
        else:
            print(f'Pages {first}-{last} of {info["Pages"]} | already done: {len(done_pages)} | to process: {len(todo)}')

        job.mark_processing()
        job.page_count = info['Pages']
        job.ocr_config = json.dumps({
            'engine': args.engine,
            'model': getattr(engine, 'model', None),
            'pages': f'{first}-{last}',
        })
        db.session.commit()

        # ===== Process page by page, committing as we go =====
        failed = []
        started = time.time()
        for i, page_num in enumerate(todo, 1):
            try:
                # Render just this page (keeps memory flat on huge PDFs)
                image = convert_from_path(
                    pdf_path, dpi=200, poppler_path=poppler,
                    first_page=page_num, last_page=page_num,
                )[0]

                if args.engine == 'vision':
                    rows = engine.process_page(image, page_num)
                else:
                    # Tesseract path: OCR the rendered page via a temp file
                    tmp = f'{pdf_path}.cli_tmp.png'
                    image.save(tmp, 'PNG')
                    try:
                        text, words = engine.process_image(tmp)
                    finally:
                        os.remove(tmp)
                    rows = [engine._row_to_dict(r, page_num)
                            for r in engine.extract_ledger_rows(text, words)]

                save_rows(db, OCRResult, job, rows)
                job.progress = int(i / len(todo) * 100)
                db.session.commit()  # commit per page so interruption loses nothing

                elapsed = time.time() - started
                eta = elapsed / i * (len(todo) - i)
                print(f'  page {page_num}: {len(rows)} rows  ({i}/{len(todo)}, ETA {eta / 60:.0f} min)')

            except KeyboardInterrupt:
                db.session.rollback()
                print(f'\nInterrupted. Resume with: python scripts/process_job_cli.py --job-id {job.id}')
                sys.exit(1)
            except Exception as e:
                db.session.rollback()
                failed.append(page_num)
                print(f'  page {page_num}: FAILED - {e}')

        # ===== Wrap up =====
        if failed:
            job.error_message = f'Pages failed: {failed}'
            print(f'\nDone with {len(failed)} failed pages: {failed}')
            print(f'Retry them with: python scripts/process_job_cli.py --job-id {job.id}')
        job.mark_completed()
        db.session.commit()
        total = job.results.count()
        print(f'\nJob {job.id} complete: {total} rows extracted. '
              f'Review at /ocr/job/{job.id}/review')


if __name__ == '__main__':
    main()
