#!/usr/bin/env python3
"""
Drop all tables from Supabase database.
This is a cleanup/reset operation.
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("[!] DATABASE_URL not set in environment")
    sys.exit(1)

import psycopg2

def get_connection():
    """Create a database connection"""
    return psycopg2.connect(DATABASE_URL)

def drop_all_tables(conn):
    """Drop all user-created tables"""
    with conn.cursor() as cur:
        # Get all tables
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
        """)
        tables = [row[0] for row in cur.fetchall()]
        
        if not tables:
            print("[*] No tables found to drop")
            return
        
        print(f"[*] Dropping {len(tables)} tables...")
        
        # Drop all tables
        for table in tables:
            try:
                # Use quoted identifier for reserved keywords
                quoted = f'"{table}"' if table in ['user', 'role', 'order'] else table
                cur.execute(f"DROP TABLE IF EXISTS {quoted} CASCADE")
                print(f"  [✓] Dropped {table}")
            except Exception as e:
                print(f"  [✗] Failed to drop {table}: {e}")
        
        conn.commit()
        print("[✓] All tables dropped!")

if __name__ == '__main__':
    try:
        conn = get_connection()
        drop_all_tables(conn)
        conn.close()
        print("\n[✓] Cleanup complete!")
    except Exception as e:
        print(f"[✗] Error: {e}")
        sys.exit(1)
