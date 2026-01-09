"""
User management routes
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import User, Role, Member, Permission

users_bp = Blueprint('users', __name__)


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


# ============ Staff Users ============

@users_bp.route('/staff')
@login_required
@permission_required(Permission.MANAGE_USERS)
def staff_list():
    """List staff users"""
    users = User.query.order_by(User.username).all()
    return render_template('users/staff_list.html', users=users)


@users_bp.route('/staff/add', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_USERS)
def add_staff():
    """Add a staff user"""
    roles = Role.query.all()
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role_id = request.form.get('role_id', type=int)
        
        # Validation
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('users/add_staff.html', roles=roles)
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return render_template('users/add_staff.html', roles=roles)
        
        if len(password) < 6:
            flash('Password must be at least 6 characters', 'error')
            return render_template('users/add_staff.html', roles=roles)
        
        user = User(
            username=username,
            email=email,
            full_name=request.form.get('full_name', '').strip(),
            role_id=role_id,
            is_active=True
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash(f'Staff user "{username}" created successfully', 'success')
        return redirect(url_for('users.staff_list'))
    
    return render_template('users/add_staff.html', roles=roles)


@users_bp.route('/staff/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_USERS)
def edit_staff(user_id):
    """Edit a staff user"""
    user = User.query.get_or_404(user_id)
    roles = Role.query.all()
    
    if request.method == 'POST':
        user.full_name = request.form.get('full_name', '').strip()
        user.role_id = request.form.get('role_id', type=int)
        user.is_active = request.form.get('is_active') == 'on'
        
        # Change password if provided
        new_password = request.form.get('new_password', '')
        if new_password:
            if len(new_password) < 6:
                flash('Password must be at least 6 characters', 'error')
                return render_template('users/edit_staff.html', user=user, roles=roles)
            user.set_password(new_password)
        
        db.session.commit()
        
        flash(f'Staff user "{user.username}" updated successfully', 'success')
        return redirect(url_for('users.staff_list'))
    
    return render_template('users/edit_staff.html', user=user, roles=roles)


# ============ Members ============

@users_bp.route('/members')
@login_required
@permission_required(Permission.MANAGE_MEMBERS)
def member_list():
    """List library members"""
    page = request.args.get('page', 1, type=int)
    
    query = Member.query
    
    search = request.args.get('search', '').strip()
    if search:
        search_term = f'%{search}%'
        query = query.filter(
            db.or_(
                Member.member_id.ilike(search_term),
                Member.full_name.ilike(search_term),
                Member.email.ilike(search_term)
            )
        )
    
    members = query.order_by(Member.full_name).paginate(page=page, per_page=20)
    
    return render_template('users/member_list.html', members=members, search=search)


@users_bp.route('/members/add', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_MEMBERS)
def add_member():
    """Add a library member"""
    if request.method == 'POST':
        member_id = request.form.get('member_id', '').strip()
        
        if Member.query.filter_by(member_id=member_id).first():
            flash('Member ID already exists', 'error')
            return render_template('users/add_member.html')
        
        member = Member(
            member_id=member_id,
            full_name=request.form.get('full_name', '').strip(),
            email=request.form.get('email', '').strip() or None,
            phone=request.form.get('phone', '').strip() or None,
            member_type=request.form.get('member_type', 'Student'),
            class_group=request.form.get('class_group', '').strip() or None,
            is_active=True
        )
        
        db.session.add(member)
        db.session.commit()
        
        flash(f'Member "{member.full_name}" created successfully', 'success')
        return redirect(url_for('users.member_list'))
    
    return render_template('users/add_member.html')


@users_bp.route('/members/<int:member_id>')
@login_required
def view_member(member_id):
    """View member details"""
    member = Member.query.get_or_404(member_id)
    return render_template('users/view_member.html', member=member)


@users_bp.route('/members/<int:member_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_MEMBERS)
def edit_member(member_id):
    """Edit a member"""
    member = Member.query.get_or_404(member_id)
    
    if request.method == 'POST':
        member.full_name = request.form.get('full_name', '').strip()
        member.email = request.form.get('email', '').strip() or None
        member.phone = request.form.get('phone', '').strip() or None
        member.member_type = request.form.get('member_type', 'Student')
        member.class_group = request.form.get('class_group', '').strip() or None
        member.is_active = request.form.get('is_active') == 'on'
        member.notes = request.form.get('notes', '').strip() or None
        
        db.session.commit()
        
        flash(f'Member "{member.full_name}" updated successfully', 'success')
        return redirect(url_for('users.view_member', member_id=member.id))
    
    return render_template('users/edit_member.html', member=member)
