#!/usr/bin/env python3
"""Migrate data - disable FKs, handle type mismatches"""
import sqlite3, psycopg2, os
from psycopg2.extras import execute_batch
from dotenv import load_dotenv

load_dotenv()

conn_sqlite = sqlite3.connect('instance/epustaka.db')
conn_pg = psycopg2.connect(os.environ.get('DATABASE_URL'))

cur_sqlite = conn_sqlite.cursor()
cur_pg = conn_pg.cursor()

# Disable foreign key checks during migration
cur_pg.execute('SET CONSTRAINTS ALL DEFERRED')

# Tables in order
tables_in_order = [
    'roles',
    'users',
    'books',
    'members',
    'book_copies',
    'loans',
    'ocr_jobs',
    'ocr_results',
    'digitized_ledger',
]

print(f'[*] Disabling foreign key constraints\n')
print(f'[*] Migrating tables\n')
total = 0

for table in tables_in_order:
    cur_sqlite.execute(f'PRAGMA table_info({table})')
    cols = [r[1] for r in cur_sqlite.fetchall()]
    
    if not cols:
        continue
    
    cur_sqlite.execute(f'SELECT * FROM {table}')
    rows = cur_sqlite.fetchall()
    
    if not rows:
        print(f'  [{table:20}] No data')
        continue
    
    # Truncate table (faster than delete with FKs)
    try:
        cur_pg.execute(f'TRUNCATE TABLE {table} CASCADE')
        conn_pg.commit()
    except:
        conn_pg.rollback()
    
    # Insert data
    cols_str = ', '.join(cols)
    ph = ', '.join(['%s'] * len(cols))
    sql = f'INSERT INTO {table} ({cols_str}) VALUES ({ph})'
    
    try:
        execute_batch(cur_pg, sql, rows, page_size=100)
        conn_pg.commit()
        total += len(rows)
        print(f'  [{table:20}] ✓ {len(rows):5} rows')
    except Exception as e:
        print(f'  [{table:20}] ✗ {str(e)[:45]}')
        conn_pg.rollback()

print(f'\n[✓] Total: {total} rows')
conn_sqlite.close()
conn_pg.close()
