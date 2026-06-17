#!/usr/bin/env python
"""
Database initialization script - Creates tables and default admin user
Run this after a fresh database setup
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from app import create_app, db
from app.models.user import Role, User, Permission

def init_database():
    """Initialize database with default data"""
    app = create_app()
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print("✓ Database tables created")
        
        # Create default roles
        Role.insert_default_roles()
        print("✓ Default roles created")
        
        # Create default admin user if it doesn't exist
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_role = Role.query.filter_by(name='Administrator').first()
            
            admin_user = User(
                username='admin',
                email='admin@epustaka.local',
                full_name='Administrator',
                role_id=admin_role.id if admin_role else None,
                is_active=True
            )
            admin_user.set_password('admin123')  # Default password - CHANGE THIS!
            db.session.add(admin_user)
            db.session.commit()
            print("✓ Admin user created (username: admin, password: admin123)")
            print("⚠️  IMPORTANT: Change the admin password immediately after login!")
        else:
            print("ℹ️  Admin user already exists")
        
        print("\n✓ Database initialization complete!")
        print("\nYou can now login with:")
        print("  Username: admin")
        print("  Password: admin123")

if __name__ == '__main__':
    init_database()
