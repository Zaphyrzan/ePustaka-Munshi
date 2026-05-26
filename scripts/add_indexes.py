"""
Database Migration: Add Indexes for Performance
Run this after creating tables to add missing indexes on frequently queried columns.

Usage:
    python -c "from scripts.optimize_indexes import run_migration; run_migration()"
Or use as Flask CLI:
    flask optimize-indexes
"""
from app import db
from sqlalchemy import text
import sys


def run_migration():
    """Add all performance indexes to the database"""
    engine = db.engine
    
    # Check if we're using PostgreSQL
    if engine.dialect.name != 'postgresql':
        print("⚠️  This migration is optimized for PostgreSQL. Skipping.")
        return
    
    indexes_to_create = [
        # Books table
        ("idx_books_title", "CREATE INDEX IF NOT EXISTS idx_books_title ON books (title)"),
        ("idx_books_author", "CREATE INDEX IF NOT EXISTS idx_books_author ON books (author)"),
        ("idx_books_isbn", "CREATE INDEX IF NOT EXISTS idx_books_isbn ON books (isbn)"),
        ("idx_books_call_number", "CREATE INDEX IF NOT EXISTS idx_books_call_number ON books (call_number)"),
        ("idx_books_category", "CREATE INDEX IF NOT EXISTS idx_books_category ON books (category)"),
        
        # BookCopy table
        ("idx_book_copies_barcode", "CREATE INDEX IF NOT EXISTS idx_book_copies_barcode ON book_copies (barcode)"),
        ("idx_book_copies_book_id", "CREATE INDEX IF NOT EXISTS idx_book_copies_book_id ON book_copies (book_id)"),
        ("idx_book_copies_status", "CREATE INDEX IF NOT EXISTS idx_book_copies_status ON book_copies (status)"),
        ("idx_book_copies_book_status", "CREATE INDEX IF NOT EXISTS idx_book_copies_book_status ON book_copies (book_id, status)"),
        
        # Members table
        ("idx_members_member_id", "CREATE INDEX IF NOT EXISTS idx_members_member_id ON members (member_id)"),
        ("idx_members_is_active", "CREATE INDEX IF NOT EXISTS idx_members_is_active ON members (is_active)"),
        ("idx_members_form_level", "CREATE INDEX IF NOT EXISTS idx_members_form_level ON members (form_level)"),
        ("idx_members_member_type", "CREATE INDEX IF NOT EXISTS idx_members_member_type ON members (member_type)"),
        ("idx_members_active_type", "CREATE INDEX IF NOT EXISTS idx_members_active_type ON members (is_active, member_type)"),
        
        # Loans table
        ("idx_loans_member_id", "CREATE INDEX IF NOT EXISTS idx_loans_member_id ON loans (member_id)"),
        ("idx_loans_copy_id", "CREATE INDEX IF NOT EXISTS idx_loans_copy_id ON loans (copy_id)"),
        ("idx_loans_status", "CREATE INDEX IF NOT EXISTS idx_loans_status ON loans (status)"),
        ("idx_loans_due_date", "CREATE INDEX IF NOT EXISTS idx_loans_due_date ON loans (due_date)"),
        ("idx_loans_checkout_date", "CREATE INDEX IF NOT EXISTS idx_loans_checkout_date ON loans (checkout_date DESC)"),
        ("idx_loans_member_status", "CREATE INDEX IF NOT EXISTS idx_loans_member_status ON loans (member_id, status)"),
        
        # Users table
        ("idx_users_username", "CREATE INDEX IF NOT EXISTS idx_users_username ON users (username)"),
        ("idx_users_email", "CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)"),
        ("idx_users_is_active", "CREATE INDEX IF NOT EXISTS idx_users_is_active ON users (is_active)"),
        
        # Roles table
        ("idx_roles_is_default", "CREATE INDEX IF NOT EXISTS idx_roles_is_default ON roles (is_default)"),
    ]
    
    created_count = 0
    failed_count = 0
    
    with engine.connect() as connection:
        for index_name, sql in indexes_to_create:
            try:
                connection.execute(text(sql))
                print(f"✓ Created index: {index_name}")
                created_count += 1
            except Exception as e:
                print(f"✗ Failed to create {index_name}: {str(e)}")
                failed_count += 1
        
        # Commit all changes
        connection.commit()
    
    print(f"\n✓ Index migration complete: {created_count} created, {failed_count} failed")
    
    # Analyze tables to update query planner statistics
    print("\nAnalyzing tables for query optimizer...")
    with engine.connect() as connection:
        try:
            connection.execute(text("ANALYZE books"))
            connection.execute(text("ANALYZE book_copies"))
            connection.execute(text("ANALYZE members"))
            connection.execute(text("ANALYZE loans"))
            connection.execute(text("ANALYZE users"))
            connection.commit()
            print("✓ Table analysis complete")
        except Exception as e:
            print(f"✗ Analysis failed: {e}")


if __name__ == '__main__':
    run_migration()
