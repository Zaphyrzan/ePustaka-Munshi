#!/usr/bin/env python3
"""Data migration with type conversion"""
import sqlite3, psycopg2, os
from psycopg2.extras import execute_batch
from dotenv import load_dotenv

load_dotenv()

conn_sqlite = sqlite3.connect('instance/epustaka.db')
conn_pg = psycopg2.connect(os.environ.get('DATABASE_URL'))

cur_sqlite = conn_sqlite.cursor()
cur_pg = conn_pg.cursor()

# Map of tables to boolean columns that need conversion
BOOLEAN_COLUMNS = {
    'roles': ['is_default'],
    'users': ['is_active'],
    'members': ['is_active', 'mark_for_deletion'],
    'loans': ['fine_paid'],
    'ocr_jobs': [],
    'ocr_results': ['is_reviewed'],
}

tables_in_order = ['roles', 'users', 'books', 'members', 'book_copies', 'loans', 'ocr_jobs', 'ocr_results', 'digitized_ledger']

print('[*] Migrating with type conversion\n')
total = 0

for table in tables_in_order:
    cur_sqlite.execute(f'PRAGMA table_info({table})')
    col_info = [(r[1], r[2]) for r in cur_sqlite.fetchall()]  # name, type
    cols = [r[0] for r in col_info]
    
    if not cols:
        continue
    
    cur_sqlite.execute(f'SELECT * FROM {table}')
    rows = cur_sqlite.fetchall()
    
    if not rows:
        print(f'  [{table:20}] No data')
        continue
    
    # Truncate
    try:
        cur_pg.execute(f'TRUNCATE TABLE {table} CASCADE')
        conn_pg.commit()
    except:
        conn_pg.rollback()
    
    # Convert boolean columns in rows
    bool_cols = BOOLEAN_COLUMNS.get(table, [])
    bool_indices = [cols.index(bc) for bc in bool_cols if bc in cols]
    
    converted_rows = []
    for row in rows:
        row_list = list(row)
        # Convert integer booleans to actual booleans
        for idx in bool_indices:
            if row_list[idx] is not None:
                row_list[idx] = bool(row_list[idx])
        converted_rows.append(tuple(row_list))
    
    # Insert
    cols_str = ', '.join(cols)
    ph = ', '.join(['%s'] * len(cols))
    sql = f'INSERT INTO {table} ({cols_str}) VALUES ({ph})'
    
    try:
        execute_batch(cur_pg, sql, converted_rows, page_size=100)
        conn_pg.commit()
        total += len(converted_rows)
        print(f'  [{table:20}] ✓ {len(converted_rows):5} rows')
    except Exception as e:
        print(f'  [{table:20}] ✗ {str(e)[:45]}')
        conn_pg.rollback()

print(f'\n[✓] Total: {total} rows')
conn_sqlite.close()
conn_pg.close()
