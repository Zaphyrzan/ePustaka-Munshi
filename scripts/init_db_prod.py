#!/usr/bin/env python
"""
One-shot database initialization for production (Supabase).
Run this locally ONCE after setting DATABASE_URL to initialize schema + roles.

Usage:
    export DATABASE_URL="postgresql://..."  # (or $env:DATABASE_URL on PowerShell)
    python scripts/init_db_prod.py
"""
import os
import sys
from app import create_app, db
from app.models.user import Role

def init_prod_db():
    """Initialize production database: create tables and seed default roles."""
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("❌ ERROR: DATABASE_URL environment variable not set!")
        print("   Set it before running this script.")
        sys.exit(1)
    
    print(f"🔗 Connecting to: {database_url.split('@')[1] if '@' in database_url else '???'}")
    
    app = create_app()
    
    try:
        with app.app_context():
            print("📋 Creating database tables...")
            db.create_all()
            print("✅ Tables created")
            
            print("👤 Seeding default roles...")
            Role.insert_default_roles()
            print("✅ Roles seeded")
            
            print("\n✨ Database initialized successfully!")
            print("   You can now run the app with this DATABASE_URL.")
            
    except Exception as e:
        print(f"\n❌ Initialization failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    init_prod_db()
