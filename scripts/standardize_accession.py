"""Standardize all accession numbers to the canonical ACC-YYYY-NNNN format.

Older books (OCR-imported "4490", legacy "ACC00101", etc.) get reassigned a
standard number, continuing the per-year sequence so they never collide with
already-standard copies. The year comes from the copy's created_at.

Safety:
  - DRY RUN by default. Pass --commit to actually write.
  - Targets LOCAL sqlite by default. Pass --prod to use the .env DATABASE_URL
    (Supabase). Without --prod it forces the local instance/epustaka.db.
  - Writes an old->new mapping to scripts/accession_mapping_<ts>.csv for audit.

Usage:
  python scripts/standardize_accession.py                 # local, dry run
  python scripts/standardize_accession.py --commit        # local, apply
  python scripts/standardize_accession.py --prod --commit # Supabase, apply
"""
import os
import re
import sys
import csv
from collections import defaultdict
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
USE_PROD = '--prod' in sys.argv
COMMIT = '--commit' in sys.argv

if not USE_PROD:
    # Force the local SQLite DB so we never touch production by accident.
    os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(BASE, 'instance', 'epustaka.db').replace('\\', '/')

from app import create_app, db  # noqa: E402
from app.models import BookCopy  # noqa: E402

STD = re.compile(r'^ACC-\d{4}-\d{4}$')

app = create_app()
with app.app_context():
    print(f"[standardize] DB: {app.config['SQLALCHEMY_DATABASE_URI'].split('@')[-1]}")
    copies = BookCopy.query.order_by(BookCopy.id).all()

    # Seed each year's running max from copies already in standard format.
    year_max = defaultdict(int)
    for c in copies:
        if c.accession_number and STD.match(c.accession_number):
            _, y, s = c.accession_number.split('-')
            year_max[int(y)] = max(year_max[int(y)], int(s))

    changes = []
    for c in copies:
        if c.accession_number and STD.match(c.accession_number):
            continue  # already standard
        year = c.created_at.year if c.created_at else datetime.utcnow().year
        year_max[year] += 1
        new_acc = f'ACC-{year}-{year_max[year]:04d}'
        changes.append((c.id, c.accession_number, new_acc))
        c.accession_number = new_acc

    total = len(copies)
    print(f"[standardize] {total} copies, {len(changes)} non-standard -> reassigned")
    for cid, old, new in changes[:25]:
        print(f"    #{cid}: {old!r} -> {new}")
    if len(changes) > 25:
        print(f"    ... and {len(changes) - 25} more")

    if changes:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        tag = 'prod' if USE_PROD else 'local'
        path = os.path.join(BASE, 'scripts', f'accession_mapping_{tag}_{ts}.csv')
        with open(path, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['copy_id', 'old_accession', 'new_accession'])
            w.writerows(changes)
        print(f"[standardize] mapping saved -> {path}")

    if COMMIT:
        db.session.commit()
        print(f"[standardize] COMMITTED {len(changes)} changes.")
    else:
        db.session.rollback()
        print("[standardize] DRY RUN — no changes written. Re-run with --commit to apply.")
