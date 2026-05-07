#!/usr/bin/env python3
"""
Simple migration: Create tables and copy data from SQLite to Supabase.
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
from dotenv import load_dotenv

load_dotenv()

import psycopg2
from psycopg2.extras import execute_batch

# Paths
SQLITE_DB = 'instance/epustaka.db'
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQLITE_PATH = os.path.join(BASE_DIR, SQLITE_DB)

def get_sqlite_connection():
    return sqlite3.connect(SQLITE_PATH)

def get_postgres_connection():
    DATABASE_URL = os.environ.get('DATABASE_URL')
    return psycopg2.connect(DATABASE_URL)

def create_tables_via_app():
    """Use init_db.py logic to create tables"""
    print("[*] Creating tables via SQLAlchemy...")
    from app import create_app, db
    from app.models.user import Role
    
    app = create_app()
    with app.app_context():
        db.create_all()
        print("  [✓] Tables created")
        
        # Insert default roles
        Role.insert_default_roles()
        print("  [✓] Default roles inserted")

def copy_data(sqlite_conn, postgres_conn):
    """Copy all data from SQLite to PostgreSQL"""
    print("\n[*] Copying data from SQLite to Supabase...")
    
    sqlite_cursor = sqlite_conn.cursor()
    postgres_cursor = postgres_conn.cursor()
    
    # Get all tables from SQLite
    sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in sqlite_cursor.fetchall()]
    
    total_rows = 0
    
    for table in tables:
        try:
            # Get columns
            sqlite_cursor.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in sqlite_cursor.fetchall()]
            
            if not columns:
                continue
            
            # Get data
            sqlite_cursor.execute(f"SELECT * FROM {table}")
            rows = sqlite_cursor.fetchall()
            
            if not rows:
                print(f"  [{table:20}] No data")
                continue
            
            # Insert data
            columns_str = ', '.join(columns)
            placeholders = ', '.join(['%s'] * len(columns))
            insert_sql = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"
            
            execute_batch(postgres_cursor, insert_sql, rows, page_size=100)
            postgres_conn.commit()
            
            total_rows += len(rows)
            print(f"  [{table:20}] ✓ {len(rows):5} rows")
            
        except Exception as e:
            print(f"  [{table:20}] ✗ {str(e)[:50]}")
            postgres_conn.rollback()
    
    print(f"\n  [✓] Total: {total_rows} rows")

def main():
    print("[*] Starting migration...\n")
    
    # Step 1: Create tables
    print("=== STEP 1: Create Tables ===")
    try:
        create_tables_via_app()
    except Exception as e:
        print(f"[✗] Failed to create tables: {e}")
        sys.exit(1)
    
    # Step 2: Copy data
    print("\n=== STEP 2: Copy Data ===")
    try:
        sqlite_conn = get_sqlite_connection()
        postgres_conn = get_postgres_connection()
        copy_data(sqlite_conn, postgres_conn)
        sqlite_conn.close()
        postgres_conn.close()
    except Exception as e:
        print(f"[✗] Failed to copy data: {e}")
        sys.exit(1)
    
    print("\n[✓] Migration complete!")

if __name__ == '__main__':
    main()
