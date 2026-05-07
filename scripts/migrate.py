#!/usr/bin/env python3
"""Copy SQLite data to Supabase"""
import sqlite3, psycopg2, os
from psycopg2.extras import execute_batch
from dotenv import load_dotenv

load_dotenv()

conn_sqlite = sqlite3.connect('instance/epustaka.db')
conn_pg = psycopg2.connect(os.environ.get('DATABASE_URL'))

cur_sqlite = conn_sqlite.cursor()
cur_pg = conn_pg.cursor()

cur_sqlite.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [row[0] for row in cur_sqlite.fetchall()]

print(f'[*] Migrating {len(tables)} tables\n')
total = 0

for table in tables:
    cur_sqlite.execute(f'PRAGMA table_info({table})')
    cols = [r[1] for r in cur_sqlite.fetchall()]
    
    if not cols:
        continue
    
    cur_sqlite.execute(f'SELECT * FROM {table}')
    rows = cur_sqlite.fetchall()
    
    if not rows:
        print(f'  [{table:20}] No data')
        continue
    
    try:
        cur_pg.execute(f'DELETE FROM {table}')
        conn_pg.commit()
    except:
        pass
    
    cols_str = ', '.join(cols)
    ph = ', '.join(['%s'] * len(cols))
    sql = f'INSERT INTO {table} ({cols_str}) VALUES ({ph})'
    
    execute_batch(cur_pg, sql, rows, page_size=100)
    conn_pg.commit()
    
    total += len(rows)
    print(f'  [{table:20}] ✓ {len(rows):5} rows')

print(f'\n[✓] Total: {total} rows migrated')
conn_sqlite.close()
conn_pg.close()
