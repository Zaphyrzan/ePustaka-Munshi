"""
Circulation routes - Borrow/Return management
"""
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Member, Book, BookCopy, Loan, LoanStatus, CopyStatus, Permission

circulation_bp = Blueprint('circulation', __name__)


def permission_required(perm):
    """Decorator to check permission"""
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.can(perm):
                flash('You do not have permission to access this page', 'error')
                return redirect(url_for('main.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@circulation_bp.route('/')
@login_required
def index():
    """Circulation main page"""
    return render_template('circulation/index.html')


@circulation_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.CHECKOUT)
def checkout():
    """Process book checkout"""
    if request.method == 'POST':
        member_id = request.form.get('member_id', '').strip()
        barcode = request.form.get('barcode', '').strip()
        
        # Find member
        member = Member.query.filter_by(member_id=member_id).first()
        if not member:
            flash('Member not found', 'error')
            return render_template('circulation/checkout.html')
        
        if not member.can_borrow:
            if not member.is_active:
                flash('Member account is inactive', 'error')
            elif member.overdue_loans_count > 0:
                flash('Member has overdue books. Please return them first.', 'error')
            else:
                flash('Member has reached maximum loan limit', 'error')
            return render_template('circulation/checkout.html', member=member)
        
        # Find copy by barcode (scanner input)
        copy = BookCopy.query.filter_by(barcode=barcode).first()
        if not copy:
            flash('Book copy not found', 'error')
            return render_template('circulation/checkout.html', member=member)
        
        if not copy.is_available:
            if copy.status == CopyStatus.ON_LOAN.value:
                loan = copy.current_loan
                if loan:
                    flash(f'Book is currently on loan to {loan.member.full_name} until {loan.due_date.strftime("%d/%m/%Y")}', 'error')
                else:
                    flash('Book is currently on loan', 'error')
            else:
                flash(f'Book copy is not available (Status: {copy.status})', 'error')
            return render_template('circulation/checkout.html', member=member)
        
        # Create loan
        loan = Loan.create_checkout(
            member_id=member.id,
            copy_id=copy.id,
            user_id=current_user.id
        )
        db.session.commit()
        
        flash(f'{member.full_name} has successfully borrowed "{copy.book.title}". Due back: {loan.due_date.strftime("%d/%m/%Y")}', 'success')
        return redirect(url_for('circulation.checkout'))
    
    return render_template('circulation/checkout.html')


@circulation_bp.route('/return', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.RETURN)
def return_book():
    """Process book return"""
    if request.method == 'POST':
        barcode = request.form.get('barcode', '').strip()
        
        # Find copy by barcode (scanner input)
        copy = BookCopy.query.filter_by(barcode=barcode).first()
        if not copy:
            flash('Book copy not found', 'error')
            return render_template('circulation/return.html')
        
        # Find active loan
        loan = copy.current_loan
        if not loan:
            flash('This book is not currently on loan', 'error')
            return render_template('circulation/return.html')
        
        # Process return
        was_overdue = loan.is_overdue
        days_overdue = loan.days_overdue
        
        loan.process_return(user_id=current_user.id)
        db.session.commit()
        
        if was_overdue:
            flash(f'Book "{loan.copy.book.title}" returned by {loan.member.full_name} ({days_overdue} days overdue)', 'warning')
        else:
            flash(f'Book "{loan.copy.book.title}" successfully returned by {loan.member.full_name}', 'success')
        
        return redirect(url_for('circulation.return_book'))
    
    return render_template('circulation/return.html')


@circulation_bp.route('/renew/<int:loan_id>', methods=['POST'])
@login_required
@permission_required(Permission.CHECKOUT)
def renew(loan_id):
    """Renew a loan"""
    loan = Loan.query.get_or_404(loan_id)
    
    if not loan.can_renew:
        if loan.is_overdue:
            flash('Cannot renew: Book is overdue', 'error')
        else:
            flash('Cannot renew: Maximum renewals reached', 'error')
        return redirect(request.referrer or url_for('circulation.active_loans'))
    
    loan.renew()
    db.session.commit()
    
    flash(f'Loan renewed. New due date: {loan.due_date.strftime("%d/%m/%Y")}', 'success')
    return redirect(request.referrer or url_for('circulation.active_loans'))


@circulation_bp.route('/active')
@login_required
def active_loans():
    """List all active loans"""
    page = request.args.get('page', 1, type=int)
    view = request.args.get('view', 'active')  # active, overdue, history
    
    query = Loan.query
    
    # Apply filters based on view
    if view == 'active':
        loans = query.filter(
            Loan.status.in_([LoanStatus.ACTIVE.value, LoanStatus.OVERDUE.value])
        ).order_by(Loan.due_date).paginate(page=page, per_page=20)
    elif view == 'overdue':
        loans = query.filter(
            Loan.status == LoanStatus.OVERDUE.value
        ).order_by(Loan.due_date).paginate(page=page, per_page=20)
    else:  # history
        # Apply history filters
        member_id = request.args.get('member', '')
        if member_id:
            member = Member.query.filter_by(member_id=member_id).first()
            if member:
                query = query.filter(Loan.member_id == member.id)
        
        status = request.args.get('status', '')
        if status:
            query = query.filter(Loan.status == status)
        
        loans = query.order_by(Loan.checkout_date.desc()).paginate(page=page, per_page=20)
    
    return render_template('circulation/active_loans.html', loans=loans, current_view=view)


@circulation_bp.route('/overdue')
@login_required
def overdue_loans():
    """List overdue loans"""
    page = request.args.get('page', 1, type=int)
    
    loans = Loan.query.filter(
        Loan.status == LoanStatus.OVERDUE.value
    ).order_by(Loan.due_date).paginate(page=page, per_page=20)
    
    return render_template('circulation/overdue_loans.html', loans=loans)


@circulation_bp.route('/history')
@login_required
def loan_history():
    """Loan history with filters"""
    page = request.args.get('page', 1, type=int)
    
    query = Loan.query
    
    # Filters
    member_id = request.args.get('member', '')
    if member_id:
        member = Member.query.filter_by(member_id=member_id).first()
        if member:
            query = query.filter(Loan.member_id == member.id)
    
    status = request.args.get('status', '')
    if status:
        query = query.filter(Loan.status == status)
    
    loans = query.order_by(Loan.checkout_date.desc()).paginate(page=page, per_page=20)
    
    return render_template('circulation/history.html', loans=loans)


@circulation_bp.route('/member/<int:member_id>/loans')
@login_required
def member_loans(member_id):
    """View member's loan history"""
    member = Member.query.get_or_404(member_id)
    loans = member.loans.order_by(Loan.checkout_date.desc()).all()
    
    return render_template('circulation/member_loans.html', member=member, loans=loans)


# Update overdue status (can be called periodically)
@circulation_bp.route('/update-overdue', methods=['POST'])
@login_required
def update_overdue():
    """Update overdue status of loans"""
    now = datetime.utcnow()
    
    # Find active loans past due date
    overdue = Loan.query.filter(
        Loan.status == LoanStatus.ACTIVE.value,
        Loan.due_date < now
    ).all()
    
    count = 0
    for loan in overdue:
        loan.status = LoanStatus.OVERDUE.value
        count += 1
    
    db.session.commit()
    
    flash(f'Updated {count} loans to overdue status', 'info')
    return redirect(url_for('circulation.index'))


# API endpoints
@circulation_bp.route('/api/member/<member_id>')
@login_required
def api_get_member(member_id):
    """Get member info for checkout form"""
    member = Member.query.filter_by(member_id=member_id).first()
    if member:
        return jsonify(member.to_dict())
    return jsonify({'error': 'Member not found'}), 404


@circulation_bp.route('/api/copy/<barcode>/loan')
@login_required
def api_get_copy_loan(barcode):
    """Get copy and current loan info for return form"""
    copy = BookCopy.query.filter_by(barcode=barcode).first()
    if not copy:
        return jsonify({'error': 'Copy not found'}), 404
    
    result = copy.to_dict()
    loan = copy.current_loan
    if loan:
        result['current_loan'] = loan.to_dict()
    
    return jsonify(result)
