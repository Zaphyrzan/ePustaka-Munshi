#!/usr/bin/env python3
"""
Verify the migration: compare SQLite and Supabase data.
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')
SQLITE_DB = 'instance/epustaka.db'
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQLITE_PATH = os.path.join(BASE_DIR, SQLITE_DB)

import sqlite3
import psycopg2

def get_sqlite_connection():
    return sqlite3.connect(SQLITE_PATH)

def get_postgres_connection():
    return psycopg2.connect(DATABASE_URL)

def main():
    print("[*] Verifying migration...\n")
    
    try:
        sqlite_conn = get_sqlite_connection()
        postgres_conn = get_postgres_connection()
        
        sqlite_cursor = sqlite_conn.cursor()
        postgres_cursor = postgres_conn.cursor()
        
        # Get tables from both databases
        sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        sqlite_tables = {row[0]: None for row in sqlite_cursor.fetchall()}
        
        postgres_cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        postgres_tables = {row[0]: None for row in postgres_cursor.fetchall()}
        
        print("=" * 60)
        print(f"{'TABLE':20} {'SQLite':15} {'Supabase':15}")
        print("=" * 60)
        
        all_tables = sorted(set(list(sqlite_tables.keys()) + list(postgres_tables.keys())))
        
        for table in all_tables:
            # Get row count from SQLite
            sqlite_count = 0
            if table in sqlite_tables:
                try:
                    sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    sqlite_count = sqlite_cursor.fetchone()[0]
                except:
                    sqlite_count = '?'
            
            # Get row count from Supabase
            postgres_count = 0
            if table in postgres_tables:
                try:
                    postgres_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    postgres_count = postgres_cursor.fetchone()[0]
                except:
                    postgres_count = '?'
            
            status = "✓" if sqlite_count == postgres_count else "✗"
            print(f"{table:20} {str(sqlite_count):15} {str(postgres_count):15} {status}")
        
        print("=" * 60)
        
        sqlite_conn.close()
        postgres_conn.close()
        
        print("\n[✓] Verification complete!")
        
    except Exception as e:
        print(f"[✗] Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
