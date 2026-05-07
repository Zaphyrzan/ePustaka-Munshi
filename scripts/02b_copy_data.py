#!/usr/bin/env python3
"""
Copy data from SQLite (epustaka.db) to Supabase PostgreSQL.
Tables must already exist (use init_db.py first).
"""
import os
import sys
import sqlite3
from dotenv import load_dotenv

load_dotenv()

import psycopg2
from psycopg2.extras import execute_batch

# Paths
SQLITE_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'epustaka.db')

def get_sqlite_conn():
    return sqlite3.connect(SQLITE_PATH)

def get_postgres_conn():
    return psycopg2.connect(os.environ.get('DATABASE_URL'))

def copy_data():
    """Copy all data from SQLite to PostgreSQL"""
    print("[*] Copying data from SQLite to Supabase...\n")
    
    sqlite_conn = get_sqlite_conn()
    postgres_conn = get_postgres_conn()
    
    sqlite_cur = sqlite_conn.cursor()
    postgres_cur = postgres_conn.cursor()
    
    # Get all tables from SQLite
    sqlite_cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in sqlite_cur.fetchall()]
    
    total_rows = 0
    
    for table in tables:
        try:
            # Get columns
            sqlite_cur.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in sqlite_cur.fetchall()]
            
            if not columns:
                continue
            
            # Get data
            sqlite_cur.execute(f"SELECT * FROM {table}")
            rows = sqlite_cur.fetchall()
            
            if not rows:
                print(f"  [{table:20}] No data")
                continue
            
            # Delete existing data in target table first (to avoid duplicates)
            try:
                postgres_cur.execute(f"DELETE FROM {table}")
                postgres_conn.commit()
            except:
                pass
            
            # Insert data
            columns_str = ', '.join(columns)
            placeholders = ', '.join(['%s'] * len(columns))
            insert_sql = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"
            
            execute_batch(postgres_cur, insert_sql, rows, page_size=100)
            postgres_conn.commit()
            
            total_rows += len(rows)
            print(f"  [{table:20}] ✓ {len(rows):5} rows")
            
        except Exception as e:
            print(f"  [{table:20}] ✗ {str(e)[:60]}")
            postgres_conn.rollback()
    
    print(f"\n[✓] Total: {total_rows} rows copied")
    
    sqlite_conn.close()
    postgres_conn.close()

if __name__ == '__main__':
    try:
        copy_data()
        print("\n[✓] Data migration complete!")
    except Exception as e:
        print(f"\n[✗] Error: {e}")
        sys.exit(1)
