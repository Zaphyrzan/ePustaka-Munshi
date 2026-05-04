"""
ePustaka-Munshi - Library Management System
Application Entry Point
"""
import os
import click
from app import create_app, db
from app.models import User, Role, Member, Book, BookCopy, Loan, LoanStatus

app = create_app()


@app.cli.command('init-db')
def init_db():
    """Initialize the database with tables and default roles."""
    db.create_all()
    Role.insert_default_roles()
    click.echo('Database initialized with default roles.')


@app.cli.command('create-admin')
@click.option('--username', prompt=True, help='Admin username')
@click.option('--email', prompt=True, help='Admin email')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Admin password')
def create_admin(username, email, password):
    """Create an administrator account."""
    existing = User.query.filter(
        db.or_(User.username == username, User.email == email)
    ).first()
    
    if existing:
        click.echo('Error: Username or email already exists.')
        return
    
    user = User.create_admin(username, email, password)
    click.echo(f'Administrator "{username}" created successfully.')


@app.cli.command('seed-demo')
def seed_demo():
    """Seed database with demo data for testing."""
    # Ensure roles exist
    Role.insert_default_roles()
    
    # Create demo admin if not exists
    if not User.query.filter_by(username='admin').first():
        User.create_admin('admin', 'admin@epustaka.local', 'admin123')
        click.echo('Created admin user (admin / admin123)')
    
    # Create demo librarian
    librarian_role = Role.query.filter_by(name='Librarian').first()
    if not User.query.filter_by(username='librarian').first():
        user = User(
            username='librarian',
            email='librarian@epustaka.local',
            full_name='Puan Librarian',
            role=librarian_role,
            is_active=True
        )
        user.set_password('lib123')
        db.session.add(user)
        click.echo('Created librarian user (librarian / lib123)')
    
    # Create demo student user (linked to member STU0001)
    student_role = Role.query.filter_by(name='Student').first()
    if not User.query.filter_by(username='STU0001').first():
        user = User(
            username='STU0001',
            email='ahmad@student.epustaka.local',
            full_name='Ahmad bin Abdullah',
            role=student_role,
            is_active=True
        )
        user.set_password('student123')
        db.session.add(user)
        click.echo('Created student user (STU0001 / student123)')
    
    # Create demo members with student years for NILAM leaderboard
    demo_members = [
        ('STU0001', 'Ahmad bin Abdullah', 'Student', 'Science 1', 5, 25),
        ('STU0002', 'Siti binti Aminah', 'Student', 'Science 2', 5, 32),
        ('STU0003', 'Raj a/l Kumar', 'Student', 'Arts 1', 4, 18),
        ('STU0004', 'Lee Wei Ming', 'Student', 'Science 1', 4, 22),
        ('STU0005', 'Nurul Izzah', 'Student', 'Science 1', 3, 15),
        ('STU0006', 'Muhammad Hafiz', 'Student', 'Science 2', 3, 28),
        ('STU0007', 'Priya a/p Rajan', 'Student', 'Arts 1', 2, 12),
        ('STU0008', 'Tan Mei Ling', 'Student', 'Science 1', 2, 20),
        ('STU0009', 'Ali bin Hassan', 'Student', 'Science 1', 1, 8),
        ('STU0010', 'Fatimah Zahra', 'Student', 'Science 2', 1, 14),
        ('TCH001', 'Encik Teacher', 'Staff', None, None, 0),
    ]
    
    for member_id, name, mtype, class_group, year, books_read in demo_members:
        if not Member.query.filter_by(member_id=member_id).first():
            member = Member(
                member_id=member_id,
                full_name=name,
                member_type=mtype,
                class_group=class_group,
                student_year=year,
                total_books_read=books_read,
                is_active=True
            )
            db.session.add(member)
            click.echo(f'Created member: {member_id} - {name}')
    
    # Create demo books
    demo_books = [
        ('Harry Potter and the Philosopher\'s Stone', 'J.K. Rowling', '978-0747532699', 'Fiction', 'F ROW'),
        ('Laskar Pelangi', 'Andrea Hirata', '978-9793062792', 'Fiction', 'F HIR'),
        ('Sejarah Melayu', 'Tun Sri Lanang', None, 'History', 'H TUN'),
        ('Physics Form 5', 'Kementerian Pendidikan', '978-9834600123', 'Textbook', 'T PHY5'),
        ('Chemistry Form 5', 'Kementerian Pendidikan', '978-9834600124', 'Textbook', 'T CHE5'),
    ]
    
    for i, (title, author, isbn, category, call_num) in enumerate(demo_books, 1):
        if not Book.query.filter_by(title=title).first():
            book = Book(
                title=title,
                author=author,
                isbn=isbn,
                category=category,
                call_number=call_num,
                language='Malay' if 'Melayu' in title or 'Form' in title else 'English'
            )
            db.session.add(book)
            db.session.flush()
            
            # Add 2 copies per book
            for j in range(1, 3):
                acc_num = f'ACC{i:03d}{j:02d}'
                copy = BookCopy(
                    book_id=book.id,
                    accession_number=acc_num,
                    barcode=f'B{acc_num}',
                    status='available',
                    condition='Good',
                    location=f'Shelf {category[0]}'
                )
                db.session.add(copy)
            
            click.echo(f'Created book: {title} with 2 copies')
    
    db.session.commit()
    click.echo('\nDemo data seeded successfully!')
    click.echo('Login with:')
    click.echo('  - admin / admin123 (Administrator)')
    click.echo('  - librarian / lib123 (Librarian)')
    click.echo('  - STU0001 / student123 (Student)')


@app.cli.command('seed-loans')
def seed_loans():
    """Seed dummy loan data for testing."""
    from datetime import datetime, timedelta
    from app.models import Member, BookCopy, Loan, LoanStatus
    
    click.echo('Seeding dummy loan data...')
    
    # Get members
    stu001 = Member.query.filter_by(member_id='STU001').first()
    stu002 = Member.query.filter_by(member_id='STU002').first()
    
    if not stu001 or not stu002:
        click.echo('Error: STU001 or STU002 not found. Run flask seed-demo first.')
        return
    
    # Get available books
    copies = BookCopy.query.filter_by(status='available').limit(4).all()
    
    if len(copies) < 2:
        click.echo('Error: Not enough book copies available. Run flask seed-demo first.')
        return
    
    # Check if loans already exist
    existing_loans = Loan.query.filter(
        Loan.member_id.in_([stu001.id, stu002.id]),
        Loan.status.in_([LoanStatus.ACTIVE.value, LoanStatus.OVERDUE.value])
    ).count()
    
    if existing_loans > 0:
        click.echo('Dummy loans already exist. Skipping...')
        return
    
    now = datetime.utcnow()
    
    # STU001: Active loan (borrowed recently, due in 7 days)
    copy1 = copies[0]
    loan1 = Loan(
        member_id=stu001.id,
        copy_id=copy1.id,
        checkout_date=now - timedelta(days=7),
        due_date=now + timedelta(days=7),
        status=LoanStatus.ACTIVE.value,
        notes='Demo active loan for STU001'
    )
    copy1.status = 'borrowed'
    db.session.add(loan1)
    click.echo(f'Created active loan: STU001 -> {copy1.accession_number} (due in 7 days)')
    
    # STU002: Overdue loan (borrowed 3 weeks ago, due 1 week ago)
    copy2 = copies[1]
    loan2 = Loan(
        member_id=stu002.id,
        copy_id=copy2.id,
        checkout_date=now - timedelta(days=21),
        due_date=now - timedelta(days=7),
        status=LoanStatus.OVERDUE.value,
        notes='Demo overdue loan for STU002'
    )
    copy2.status = 'borrowed'
    db.session.add(loan2)
    click.echo(f'Created overdue loan: STU002 -> {copy2.accession_number} (7 days overdue)')
    
    # Optional: Add a returned loan to STU001's history for NILAM
    if len(copies) >= 3:
        copy3 = copies[2]
        loan3 = Loan(
            member_id=stu001.id,
            copy_id=copy3.id,
            checkout_date=now - timedelta(days=30),
            due_date=now - timedelta(days=16),
            return_date=now - timedelta(days=20),
            status=LoanStatus.RETURNED.value,
            notes='Demo returned loan for STU001'
        )
        db.session.add(loan3)
        click.echo(f'Created returned loan: STU001 -> {copy3.accession_number} (returned)')
    
    db.session.commit()
    click.echo('\nDummy loan data seeded successfully!')
    click.echo('STU001: 1 active loan + 1 returned')
    click.echo('STU002: 1 overdue book (7 days late)')


@app.shell_context_processor
def make_shell_context():
    """Add models to flask shell context."""
    return {
        'db': db,
        'User': User,
        'Role': Role,
        'Member': Member,
        'Book': Book,
        'BookCopy': BookCopy
    }


if __name__ == '__main__':
    app.run(debug=True, port=5000)
