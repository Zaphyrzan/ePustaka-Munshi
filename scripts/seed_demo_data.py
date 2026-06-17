#!/usr/bin/env python
"""
Seed demo data - Creates test users and members for development
Run this after init_db.py to populate test data
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from app import create_app, db
from app.models.user import Role, User, Permission
from app.models.member import Member

def seed_demo_data():
    """Seed demo data"""
    app = create_app()
    
    with app.app_context():
        print("🌱 Seeding demo data...\n")
        
        # ========== LIBRARIAN STAFF ==========
        print("📚 Creating Librarian account...")
        librarian = User.query.filter_by(username='librarian').first()
        if not librarian:
            librarian_role = Role.query.filter_by(name='Librarian').first()
            librarian = User(
                username='librarian',
                email='librarian@epustaka.local',
                full_name='Encik Librarian',
                role_id=librarian_role.id if librarian_role else None,
                is_active=True
            )
            librarian.set_password('password123')
            db.session.add(librarian)
            db.session.commit()
            print("  ✓ Librarian: username=librarian, password=password123")
        
        # ========== STUDENT ASSISTANT (STAFF MEMBER) ==========
        print("\n👨‍💼 Creating Student Assistant (Staff) account for STU0001...")
        stu_001_user = User.query.filter_by(username='STU0001').first()
        if not stu_001_user:
            staff_assistant_role = Role.query.filter_by(name='Student Assistant').first()
            stu_001_user = User(
                username='STU0001',
                email='stu0001@school.local',
                full_name='Student Assistant 001',
                role_id=staff_assistant_role.id if staff_assistant_role else None,
                is_active=True
            )
            stu_001_user.set_password('password123')
            db.session.add(stu_001_user)
            db.session.commit()
            print("  ✓ Staff Assistant: username=STU0001, password=password123")
            print("     This user can access Books Catalog, Add/Edit Book, Checkout, and Return functions")
        
        # Create corresponding Member account for borrowing
        stu_001_member = Member.query.filter_by(member_id='STU0001').first()
        if not stu_001_member:
            stu_001_member = Member(
                member_id='STU0001',
                full_name='Student Assistant 001',
                email='stu0001@school.local',
                member_type='Staff',  # Mark as Staff
                form_level=4,
                class_group='Science 1',
                is_active=True
            )
            stu_001_member.set_password('password123')  # Set password for login
            db.session.add(stu_001_member)
            db.session.commit()
            print("  ✓ Member account created for STU0001 (Staff member)")
        
        # ========== REGULAR STUDENTS FROM DIFFERENT FORMS ==========
        print("\n📖 Creating regular student accounts (no staff access)...")
        
        # Form 1 Student
        form1_user = User.query.filter_by(username='STU0002').first()
        if not form1_user:
            student_role = Role.query.filter_by(name='Student').first()
            form1_user = User(
                username='STU0002',
                email='stu0002@school.local',
                full_name='Muhammad Ali (Form 1)',
                role_id=student_role.id if student_role else None,
                is_active=True
            )
            form1_user.set_password('password123')
            db.session.add(form1_user)
            db.session.commit()
            print("  ✓ STU0002: Muhammad Ali (Form 1), password=password123")
            
            # Create Member account
            form1_member = Member.query.filter_by(member_id='STU0002').first()
            if not form1_member:
                form1_member = Member(
                    member_id='STU0002',
                    full_name='Muhammad Ali',
                    email='stu0002@school.local',
                    member_type='Student',
                    form_level=1,
                    class_group='Science 1',
                    is_active=True
                )
                form1_member.set_password('password123')  # Set password for login
                db.session.add(form1_member)
                db.session.commit()
        
        # Form 3 Student
        form3_user = User.query.filter_by(username='STU0003').first()
        if not form3_user:
            student_role = Role.query.filter_by(name='Student').first()
            form3_user = User(
                username='STU0003',
                email='stu0003@school.local',
                full_name='Nur Safiya (Form 3)',
                role_id=student_role.id if student_role else None,
                is_active=True
            )
            form3_user.set_password('password123')
            db.session.add(form3_user)
            db.session.commit()
            print("  ✓ STU0003: Nur Safiya (Form 3), password=password123")
            
            # Create Member account
            form3_member = Member.query.filter_by(member_id='STU0003').first()
            if not form3_member:
                form3_member = Member(
                    member_id='STU0003',
                    full_name='Nur Safiya',
                    email='stu0003@school.local',
                    member_type='Student',
                    form_level=3,
                    class_group='Arts 2',
                    is_active=True
                )
                form3_member.set_password('password123')  # Set password for login
                db.session.add(form3_member)
                db.session.commit()
        
        print("\n✅ Demo data seeding complete!")
        print("\n" + "="*60)
        print("TEST ACCOUNTS CREATED")
        print("="*60)
        print("\n👑 STAFF/LIBRARIAN ACCOUNTS (Can access Circulation):")
        print("  • admin / admin123 (Administrator)")
        print("  • librarian / password123 (Librarian)")
        print("  • STU0001 / password123 (Student Assistant - Staff Member)")
        print("\n👤 REGULAR STUDENT ACCOUNTS (Borrowing only, NO staff access):")
        print("  • STU0002 / password123 (Form 1 - Muhammad Ali)")
        print("  • STU0003 / password123 (Form 3 - Nur Safiya)")
        print("\n💡 KEY DIFFERENCES:")
        print("  • STU0001 can see 'Circulation' tab (Checkout/Return)")
        print("  • STU0001's sidebar shows Staff dashboard")
        print("  • STU0002 & STU0003 only see Student Portal (Search, My Loans, etc)")
        print("  • STU0002 & STU0003's sidebar hides admin functions")
        print("\n⚠️  IMPORTANT:")
        print("  • Disabling STU0001's User account → Can't login at all")
        print("  • Disabling STU0001's Member account → Can't borrow/leaderboard")
        print("="*60)

if __name__ == '__main__':
    seed_demo_data()
