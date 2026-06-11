# -*- coding: utf-8 -*-
"""
OCR accuracy evaluation - compares a job's raw extracted fields against
ground-truth Excel data (the manually typed ledger).

Matches OCR rows to ground-truth rows by No. Perolehan (accession number),
then reports per-field exact-match accuracy and mean character error rate
(CER, normalized Levenshtein distance). Use it to compare engines for the
research chapter, e.g.:

    python scripts/evaluate_ocr.py --excel ledger.xlsx --job-id 3
    python scripts/evaluate_ocr.py --excel ledger.xlsx --job-id 3 --csv results_vision.csv

Run one job with engine=vision and one with engine=tesseract on the same
pages, then evaluate both jobs against the same Excel file.
"""
import argparse
import csv
import re
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Fields compared, mapped to (OCRResult extracted attribute, Excel column aliases)
FIELDS = {
    'no_panggilan': ('no_panggilan_extracted', ['no_panggilan', 'call_number', 'callnumber']),
    'pengarang': ('pengarang_extracted', ['pengarang', 'author']),
    'tajuk_buku': ('tajuk_buku_extracted', ['tajuk_buku', 'tajuk', 'title', 'book title']),
    'penerbit': ('penerbit_extracted', ['penerbit', 'publisher', 'tempat_dan_nama_penerbit']),
    'tarikh_penerbit': ('tarikh_penerbit_extracted', ['tarikh_penerbit', 'year', 'publication_year', 'tahun_penerbit']),
    'punca': ('punca_extracted', ['punca', 'source', 'acquisition_source']),
    'muka_surat': ('muka_surat_extracted', ['muka_surat', 'page_count', 'pages']),
}

ACCESSION_ALIASES = ['no_perolehan', 'accession_number', 'accession_num']


def normalize(value):
    """Case/whitespace-insensitive comparison form"""
    if value is None:
        return ''
    return re.sub(r'\s+', ' ', str(value).strip().lower())


def norm_accession(value):
    """Accession numbers: strip everything but alphanumerics for matching"""
    return re.sub(r'[^0-9a-z]', '', normalize(value))


def levenshtein(a, b):
    """Edit distance (iterative two-row DP - no external dependency)"""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            curr.append(min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = curr
    return prev[-1]


def cer(extracted, truth):
    """Character error rate: edit distance / ground-truth length"""
    truth_n, ext_n = normalize(truth), normalize(extracted)
    if not truth_n:
        return None  # nothing to compare against
    return levenshtein(ext_n, truth_n) / len(truth_n)


def first_value(row, aliases):
    """Pull the first matching column value from an Excel row dict"""
    for key in aliases:
        if row.get(key) is not None and str(row[key]).strip() != '':
            return row[key]
    return None


def main():
    parser = argparse.ArgumentParser(description='Evaluate OCR job accuracy against Excel ground truth')
    parser.add_argument('--excel', required=True, help='Ground-truth Excel file (manually typed ledger)')
    parser.add_argument('--job-id', required=True, type=int, help='OCR job ID to evaluate')
    parser.add_argument('--csv', help='Optional path to write per-row results as CSV')
    args = parser.parse_args()

    from app import create_app
    from app.models import OCRJob, OCRResult
    from app.utils.excel_import import read_excel_file

    app = create_app(os.environ.get('FLASK_ENV', 'development'))
    with app.app_context():
        job = OCRJob.query.get(args.job_id)
        if not job:
            sys.exit(f'Job {args.job_id} not found')

        engine = job.ocr_config or 'unknown'
        results = job.results.order_by(OCRResult.page_number, OCRResult.row_number).all()
        if not results:
            sys.exit(f'Job {args.job_id} has no OCR results - run processing first')

        truth_rows, error = read_excel_file(args.excel)
        if error:
            sys.exit(f'Error reading Excel: {error}')

        # Index ground truth by normalized accession number
        truth_by_accession = {}
        for row in truth_rows:
            acc = norm_accession(first_value(row, ACCESSION_ALIASES))
            if acc:
                truth_by_accession[acc] = row

        # ===== Match and score =====
        matched, unmatched = 0, 0
        stats = {f: {'exact': 0, 'compared': 0, 'cer_sum': 0.0, 'cer_n': 0} for f in FIELDS}
        per_row = []

        for result in results:
            acc = norm_accession(result.no_perolehan_extracted)
            truth = truth_by_accession.get(acc)
            if truth is None:
                unmatched += 1
                continue
            matched += 1

            row_record = {'no_perolehan': result.no_perolehan_extracted}
            for field, (attr, aliases) in FIELDS.items():
                truth_val = first_value(truth, aliases)
                if truth_val is None:
                    continue  # ground truth empty - can't score this cell
                extracted_val = getattr(result, attr)
                s = stats[field]
                s['compared'] += 1
                exact = normalize(extracted_val) == normalize(truth_val)
                s['exact'] += exact
                rate = cer(extracted_val, truth_val)
                if rate is not None:
                    s['cer_sum'] += rate
                    s['cer_n'] += 1
                row_record[field + '_extracted'] = extracted_val
                row_record[field + '_truth'] = truth_val
                row_record[field + '_exact'] = exact
            per_row.append(row_record)

        # ===== Report =====
        print(f'\nOCR Evaluation - Job {args.job_id} ({engine})')
        print(f'Ground truth rows: {len(truth_by_accession)} | OCR rows: {len(results)}')
        print(f'Matched by accession: {matched} | Unmatched OCR rows: {unmatched}')
        # Accession recall: how many ground-truth rows the OCR found at all
        recall = matched / len(truth_by_accession) * 100 if truth_by_accession else 0
        print(f'Accession match rate: {recall:.1f}%\n')

        print(f'{"Field":<18}{"Compared":>9}{"Exact %":>9}{"Mean CER":>10}')
        print('-' * 46)
        total_exact, total_compared = 0, 0
        for field, s in stats.items():
            if s['compared'] == 0:
                print(f'{field:<18}{0:>9}{"-":>9}{"-":>10}')
                continue
            exact_pct = s['exact'] / s['compared'] * 100
            mean_cer = s['cer_sum'] / s['cer_n'] if s['cer_n'] else 0
            total_exact += s['exact']
            total_compared += s['compared']
            print(f'{field:<18}{s["compared"]:>9}{exact_pct:>8.1f}%{mean_cer:>10.3f}')
        if total_compared:
            print('-' * 46)
            print(f'{"OVERALL":<18}{total_compared:>9}{total_exact / total_compared * 100:>8.1f}%')

        if args.csv and per_row:
            fieldnames = sorted({k for r in per_row for k in r}, key=lambda k: (k != 'no_perolehan', k))
            with open(args.csv, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(per_row)
            print(f'\nPer-row detail written to {args.csv}')


if __name__ == '__main__':
    main()
