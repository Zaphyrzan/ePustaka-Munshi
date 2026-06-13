"""
User management routes
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import User, Role, Member, Permission
from app.models.member import generate_member_id
from app.utils.excel_import import (
    import_student_data, save_upload_file, get_class_groups, 
    get_form_levels, read_excel_file
)
from app.utils.api_utils import OffsetPagination, ResponseFilter, ApiResponse
from datetime import datetime

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
    """List staff users with pagination"""
    page = request.args.get('page', 1, type=int)

    # Search/filter
    search = request.args.get('search', '').strip()
    query = User.query

    if search:
        search_term = f'%{search}%'
        query = query.filter(
            db.or_(
                User.username.ilike(search_term),
                User.email.ilike(search_term),
                User.full_name.ilike(search_term)
            )
        )

    query = query.order_by(User.username)
    # Native pagination object: iterable in the template ({% for user in users %})
    users = query.paginate(page=page, per_page=15, error_out=False)

    return render_template('users/staff_list.html', users=users, search=search)


@users_bp.route('/staff/add', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_USERS)
def add_staff():
    """
    Add a staff user with comprehensive validation.
    Ensures username/email uniqueness and password strength.
    """
    roles = Role.query.all()
    
    if request.method == 'POST':
        # ===== INPUT VALIDATION =====
        
        # Get and validate username (required)
        username = request.form.get('username', '').strip()
        if not username:
            flash('Username is required', 'error')
            return render_template('users/add_staff.html', roles=roles)
        
        if len(username) < 3:
            flash('Username must be at least 3 characters', 'error')
            return render_template('users/add_staff.html', roles=roles)
        
        if len(username) > 64:
            flash('Username cannot exceed 64 characters', 'error')
            return render_template('users/add_staff.html', roles=roles)
        
        # Check if username contains only allowed characters (alphanumeric, underscore, hyphen)
        if not all(c.isalnum() or c in '_-' for c in username):
            flash('Username can only contain letters, numbers, underscores, and hyphens', 'error')
            return render_template('users/add_staff.html', roles=roles)
        
        # Check if username already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('users/add_staff.html', roles=roles)
        
        # Get and validate email (required)
        email = request.form.get('email', '').strip()
        if not email:
            flash('Email is required', 'error')
            return render_template('users/add_staff.html', roles=roles)
        
        # Validate email format
        if '@' not in email or '.' not in email.split('@')[-1]:
            flash('Invalid email format', 'error')
            return render_template('users/add_staff.html', roles=roles)
        
        if len(email) > 120:
            flash('Email cannot exceed 120 characters', 'error')
            return render_template('users/add_staff.html', roles=roles)
        
        # Check if email already exists
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return render_template('users/add_staff.html', roles=roles)
        
        # Get and validate password (optional - use default if not provided)
        password = request.form.get('password', '').strip()
        default_password = 'Munshi123'
        
        if password:
            # Only validate if a custom password is provided
            if len(password) < 6:
                flash('Password must be at least 6 characters', 'error')
                return render_template('users/add_staff.html', roles=roles)
            
            if len(password) > 128:
                flash('Password cannot exceed 128 characters', 'error')
                return render_template('users/add_staff.html', roles=roles)
        else:
            # Use default password if none provided
            password = default_password
        
        # Get and validate full_name (required)
        full_name = request.form.get('full_name', '').strip()
        if not full_name:
            flash('Full name is required', 'error')
            return render_template('users/add_staff.html', roles=roles)
        
        if len(full_name) < 2:
            flash('Full name must be at least 2 characters', 'error')
            return render_template('users/add_staff.html', roles=roles)
        
        if len(full_name) > 128:
            flash('Full name cannot exceed 128 characters', 'error')
            return render_template('users/add_staff.html', roles=roles)
        
        # Get and validate role_id (required)
        try:
            role_id = request.form.get('role_id', type=int)
            if not role_id:
                flash('Role is required', 'error')
                return render_template('users/add_staff.html', roles=roles)
            
            # Verify the role exists
            if not Role.query.get(role_id):
                flash('Invalid role selected', 'error')
                return render_template('users/add_staff.html', roles=roles)
        except (ValueError, TypeError):
            flash('Invalid role ID', 'error')
            return render_template('users/add_staff.html', roles=roles)
        
        # ===== CREATE NEW STAFF USER =====
        try:
            user = User(
                username=username,
                email=email,
                full_name=full_name,
                role_id=role_id,
                is_active=True
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            default_msg = f' (Default password: {default_password})' if request.form.get('password', '').strip() == '' else ''
            flash(f'Staff user "{username}" created successfully{default_msg}', 'success')
            return redirect(url_for('users.staff_list'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating staff user: {str(e)}', 'error')
            return render_template('users/add_staff.html', roles=roles)
    
    return render_template('users/add_staff.html', roles=roles)


@users_bp.route('/staff/<int:user_id>')
@login_required
@permission_required(Permission.MANAGE_USERS)
def view_staff(user_id):
    """View staff user details"""
    user = User.query.get_or_404(user_id)
    return render_template('users/view_staff.html', user=user)


@users_bp.route('/staff/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_USERS)
def edit_staff(user_id):
    """
    Edit a staff user with comprehensive validation.
    Allows password change and updates full name and role.
    """
    user = User.query.get_or_404(user_id)
    roles = Role.query.all()
    
    if request.method == 'POST':
        # ===== INPUT VALIDATION =====
        
        # Get and validate full_name (required)
        full_name = request.form.get('full_name', '').strip()
        if not full_name:
            flash('Full name is required', 'error')
            return render_template('users/edit_staff.html', user=user, roles=roles)
        
        if len(full_name) < 2:
            flash('Full name must be at least 2 characters', 'error')
            return render_template('users/edit_staff.html', user=user, roles=roles)
        
        if len(full_name) > 128:
            flash('Full name cannot exceed 128 characters', 'error')
            return render_template('users/edit_staff.html', user=user, roles=roles)
        
        # Get and validate role_id (required)
        try:
            role_id = request.form.get('role_id', type=int)
            if not role_id:
                flash('Role is required', 'error')
                return render_template('users/edit_staff.html', user=user, roles=roles)
            
            # Verify the role exists
            if not Role.query.get(role_id):
                flash('Invalid role selected', 'error')
                return render_template('users/edit_staff.html', user=user, roles=roles)
        except (ValueError, TypeError):
            flash('Invalid role ID', 'error')
            return render_template('users/edit_staff.html', user=user, roles=roles)
        
        # Get boolean flag for is_active
        is_active = request.form.get('is_active') == 'on'
        
        # Get and validate new password (optional)
        new_password = request.form.get('new_password', '')
        if new_password:
            # Only validate if a new password is provided
            if len(new_password) < 6:
                flash('Password must be at least 6 characters', 'error')
                return render_template('users/edit_staff.html', user=user, roles=roles)
            
            if len(new_password) > 128:
                flash('Password cannot exceed 128 characters', 'error')
                return render_template('users/edit_staff.html', user=user, roles=roles)
        
        # ===== UPDATE STAFF USER =====
        try:
            user.full_name = full_name
            user.role_id = role_id
            user.is_active = is_active
            
            # Only update password if a new one is provided
            if new_password:
                user.set_password(new_password)
            
            db.session.commit()
            
            flash(f'Staff user "{user.username}" updated successfully', 'success')
            return redirect(url_for('users.staff_list'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating staff user: {str(e)}', 'error')
            return render_template('users/edit_staff.html', user=user, roles=roles)
    
    return render_template('users/edit_staff.html', user=user, roles=roles)


# ============ Members ============

@users_bp.route('/members')
@login_required
@permission_required(Permission.MANAGE_MEMBERS)
def member_list():
    """List library members with pagination and filtering"""
    page = request.args.get('page', 1, type=int)

    query = Member.query

    # Search/filter
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
    
    # Filter by member type (optional)
    member_type = request.args.get('type', '').strip()
    if member_type:
        query = query.filter(Member.member_type == member_type)
    
    # Filter by status (optional)
    status = request.args.get('status', '').strip()
    if status == 'active':
        query = query.filter(Member.is_active == True)
    elif status == 'inactive':
        query = query.filter(Member.is_active == False)
    
    query = query.order_by(Member.full_name)
    # Native pagination: template uses members['items'] and members.iter_pages()
    members = query.paginate(page=page, per_page=15, error_out=False)

    return render_template('users/member_list.html', members=members, search=search,
                          member_type=member_type, status=status)


@users_bp.route('/members/add', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_MEMBERS)
def add_member():
    """
    Add a new library member with validation.
    Auto-generates member_id to ensure uniqueness.
    """
    if request.method == 'POST':
        # ===== INPUT VALIDATION =====
        
        # Get and validate full_name (required field)
        full_name = request.form.get('full_name', '').strip()
        if not full_name:
            flash('Full name is required', 'error')
            return render_template('users/add_member.html')
        
        if len(full_name) < 2:
            flash('Full name must be at least 2 characters', 'error')
            return render_template('users/add_member.html')
        
        if len(full_name) > 128:
            flash('Full name cannot exceed 128 characters', 'error')
            return render_template('users/add_member.html')
        
        # Get and validate email (optional but must be valid if provided)
        email = request.form.get('email', '').strip()
        if email:
            # Basic email validation (contains @ and .)
            if '@' not in email or '.' not in email.split('@')[-1]:
                flash('Invalid email format', 'error')
                return render_template('users/add_member.html')
            
            if len(email) > 120:
                flash('Email cannot exceed 120 characters', 'error')
                return render_template('users/add_member.html')
            
            # Check if email already exists
            if Member.query.filter_by(email=email).first():
                flash('Email already exists in the system', 'error')
                return render_template('users/add_member.html')
            email = email or None
        else:
            email = None
        
        # Get and validate phone (optional)
        phone = request.form.get('phone', '').strip()
        if phone:
            # Allow only digits, spaces, hyphens, and +
            if not all(c.isdigit() or c in ' +-' for c in phone):
                flash('Phone number contains invalid characters', 'error')
                return render_template('users/add_member.html')
            
            if len(phone) > 20:
                flash('Phone number cannot exceed 20 characters', 'error')
                return render_template('users/add_member.html')
            phone = phone or None
        else:
            phone = None
        
        # Get and validate member_type
        valid_member_types = ['Student', 'Staff', 'Teacher', 'Librarian', 'Admin', 'Student Assistant', 'External']
        member_type = request.form.get('member_type', 'Student')
        if member_type not in valid_member_types:
            flash('Invalid member type', 'error')
            return render_template('users/add_member.html')
        
        # Get and validate form_level (only applicable for students)
        try:
            form_level = request.form.get('form_level', type=int, default=1)
            if form_level < 1 or form_level > 6:
                flash('Form level must be between 1 and 6', 'error')
                return render_template('users/add_member.html')
        except (ValueError, TypeError):
            flash('Invalid form level', 'error')
            return render_template('users/add_member.html')
        
        # Get and validate class_group (optional)
        class_group = request.form.get('class_group', '').strip()
        if class_group and len(class_group) > 64:
            flash('Class group cannot exceed 64 characters', 'error')
            return render_template('users/add_member.html')
        class_group = class_group or None
        
        # ===== AUTO-GENERATE MEMBER ID =====
        member_id = generate_member_id()
        
        # ===== SET DEFAULT PASSWORD =====
        default_password = 'Munshi123'
        
        # ===== CREATE NEW MEMBER =====
        try:
            member = Member(
                member_id=member_id,
                full_name=full_name,
                email=email,
                phone=phone,
                member_type=member_type,
                form_level=form_level,
                class_group=class_group,
                student_year=datetime.now().year,
                is_active=True
            )
            
            # Set default password for the member
            # Students and members login with member_id (STU0001, etc.) as username
            member.set_password(default_password)
            
            db.session.add(member)
            db.session.commit()
            
            flash(f'Member "{member.full_name}" created successfully (ID: {member.member_id}, Default password: {default_password})', 'success')
            return redirect(url_for('users.view_member', member_id=member.id))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating member: {str(e)}', 'error')
            return render_template('users/add_member.html')
    
    return render_template('users/add_member.html')


@users_bp.route('/members/<int:member_id>')
@login_required
def view_member(member_id):
    """View member details"""
    member = Member.query.get_or_404(member_id)
    
    # Get member's loans sorted by checkout date (newest first), limit to 20
    from app.models import Loan
    loans = Loan.query.filter_by(member_id=member.id).order_by(Loan.checkout_date.desc()).limit(20).all()
    
    return render_template('users/view_member.html', member=member, loans=loans)


@users_bp.route('/members/<int:member_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_MEMBERS)
def edit_member(member_id):
    """
    Edit a library member with comprehensive validation.
    Prevents duplicate emails and invalid data entry.
    """
    member = Member.query.get_or_404(member_id)
    
    if request.method == 'POST':
        # ===== INPUT VALIDATION =====
        
        # Get and validate full_name (required field)
        full_name = request.form.get('full_name', '').strip()
        if not full_name:
            flash('Full name is required', 'error')
            return render_template('users/edit_member.html', member=member)
        
        if len(full_name) < 2:
            flash('Full name must be at least 2 characters', 'error')
            return render_template('users/edit_member.html', member=member)
        
        if len(full_name) > 128:
            flash('Full name cannot exceed 128 characters', 'error')
            return render_template('users/edit_member.html', member=member)
        
        # Get and validate email (optional but must be valid if provided)
        email = request.form.get('email', '').strip()
        if email:
            # Basic email validation
            if '@' not in email or '.' not in email.split('@')[-1]:
                flash('Invalid email format', 'error')
                return render_template('users/edit_member.html', member=member)
            
            if len(email) > 120:
                flash('Email cannot exceed 120 characters', 'error')
                return render_template('users/edit_member.html', member=member)
            
            # Check if email already exists (but not for the current member)
            existing_email = Member.query.filter(
                Member.email == email,
                Member.id != member.id
            ).first()
            
            if existing_email:
                flash('Email already exists for another member', 'error')
                return render_template('users/edit_member.html', member=member)
            email = email or None
        else:
            email = None
        
        # Get and validate phone (optional)
        phone = request.form.get('phone', '').strip()
        if phone:
            # Allow only digits, spaces, hyphens, and +
            if not all(c.isdigit() or c in ' +-' for c in phone):
                flash('Phone number contains invalid characters', 'error')
                return render_template('users/edit_member.html', member=member)
            
            if len(phone) > 20:
                flash('Phone number cannot exceed 20 characters', 'error')
                return render_template('users/edit_member.html', member=member)
            phone = phone or None
        else:
            phone = None
        
        # Get and validate member_type
        valid_member_types = ['Student', 'Staff', 'Teacher', 'Librarian', 'Admin', 'Student Assistant', 'External']
        member_type = request.form.get('member_type', 'Student')
        if member_type not in valid_member_types:
            flash('Invalid member type', 'error')
            return render_template('users/edit_member.html', member=member)
        
        # Get and validate form_level
        try:
            form_level = request.form.get('form_level', type=int, default=1)
            if form_level < 1 or form_level > 6:
                flash('Form level must be between 1 and 6', 'error')
                return render_template('users/edit_member.html', member=member)
        except (ValueError, TypeError):
            flash('Invalid form level', 'error')
            return render_template('users/edit_member.html', member=member)
        
        # Get and validate class_group (optional)
        class_group = request.form.get('class_group', '').strip()
        if class_group and len(class_group) > 64:
            flash('Class group cannot exceed 64 characters', 'error')
            return render_template('users/edit_member.html', member=member)
        class_group = class_group or None
        
        # Get and validate notes (optional)
        notes = request.form.get('notes', '').strip()
        if notes and len(notes) > 500:
            flash('Notes cannot exceed 500 characters', 'error')
            return render_template('users/edit_member.html', member=member)
        notes = notes or None
        
        # Get boolean flags
        is_active = request.form.get('is_active') == 'on'
        mark_for_deletion = request.form.get('mark_for_deletion') == 'on'
        
        # Get and validate new password (optional)
        new_password = request.form.get('new_password', '').strip()
        if new_password:
            # Only validate if a new password is provided
            if len(new_password) < 6:
                flash('Password must be at least 6 characters', 'error')
                return render_template('users/edit_member.html', member=member)
            
            if len(new_password) > 128:
                flash('Password cannot exceed 128 characters', 'error')
                return render_template('users/edit_member.html', member=member)
        
        # ===== UPDATE MEMBER =====
        try:
            member.full_name = full_name
            member.email = email
            member.phone = phone
            member.member_type = member_type
            member.form_level = form_level
            member.class_group = class_group
            member.is_active = is_active
            member.mark_for_deletion = mark_for_deletion
            member.notes = notes
            
            # Update password if a new one is provided
            if new_password:
                member.set_password(new_password)
            
            # If marking as graduated, set form_level to 6 and record graduation date
            if request.form.get('mark_graduated') == 'on':
                member.form_level = 6
                member.graduation_date = datetime.now()
            
            db.session.commit()
            
            flash(f'Member "{member.full_name}" updated successfully', 'success')
            return redirect(url_for('users.view_member', member_id=member.id))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating member: {str(e)}', 'error')
            return render_template('users/edit_member.html', member=member)
    
    return render_template('users/edit_member.html', member=member)


@users_bp.route('/members/<int:member_id>/delete-confirm', methods=['GET'])
@login_required
@permission_required(Permission.MANAGE_MEMBERS)
def delete_member_confirm(member_id):
    """
    Show confirmation page before deleting a member.
    Checks for existing loans and provides clear warnings.
    """
    from datetime import datetime
    from app.models import Loan
    
    member = Member.query.get_or_404(member_id)
    
    # Get all loans (active, overdue, and returned)
    all_loans = Loan.query.filter_by(member_id=member.id).all()
    active_loans = [loan for loan in all_loans if loan.status == 'active']
    overdue_loans = [loan for loan in all_loans if loan.status == 'overdue']
    active_overdue_count = len(active_loans) + len(overdue_loans)
    total_loans = len(all_loans)
    
    return render_template('users/delete_member_confirm.html', 
                         member=member, 
                         all_loans=all_loans,
                         active_loans=active_loans,
                         overdue_loans=overdue_loans,
                         active_overdue_count=active_overdue_count,
                         total_loans=total_loans,
                         now=datetime.now())


@users_bp.route('/members/<int:member_id>/delete', methods=['POST'])
@login_required
@permission_required(Permission.MANAGE_MEMBERS)
def delete_member(member_id):
    """
    Delete a member with multiple safety checks.
    
    Safety mechanisms:
    1. Requires admin confirmation (via delete-confirm page)
    2. Checks for active loans - cannot delete if member has active/overdue loans
    3. Logs deletion with reason
    4. Prevents accidental deletion with password confirmation
    """
    member = Member.query.get_or_404(member_id)
    
    # ===== SAFETY CHECK 1: Admin verification =====
    admin_confirmed = request.form.get('admin_confirmed') == 'yes'
    if not admin_confirmed:
        flash('Admin confirmation required. Please check the confirmation checkbox.', 'error')
        return redirect(url_for('users.delete_member_confirm', member_id=member.id))
    
    # ===== SAFETY CHECK 2: Check for active loans =====
    from app.models import Loan
    active_loans = Loan.query.filter_by(member_id=member.id).filter(
        Loan.status.in_(['active', 'overdue'])
    ).all()
    
    if active_loans:
        flash(
            f'Cannot delete member: {member.full_name} has {len(active_loans)} active/overdue loans. '
            f'All loans must be returned or marked as lost before deletion.',
            'error'
        )
        return redirect(url_for('users.delete_member_confirm', member_id=member.id))
    
    # ===== SAFETY CHECK 3: Verify password (double-check from current user) =====
    current_password = request.form.get('current_password', '')
    if not current_user.check_password(current_password):
        flash('Current password is incorrect. Deletion cancelled for security.', 'error')
        return redirect(url_for('users.delete_member_confirm', member_id=member.id))
    
    # ===== ALL CHECKS PASSED - PROCEED WITH DELETION =====
    try:
        full_name = member.full_name
        member_id_str = member.member_id
        
        # Get deletion reason for logging
        deletion_reason = request.form.get('deletion_reason', 'Admin deletion').strip()
        if not deletion_reason:
            deletion_reason = 'Admin deletion'
        if len(deletion_reason) > 200:
            deletion_reason = deletion_reason[:200]
        
        # Store deletion info in member's notes before deleting (if there are any)
        total_loans = Loan.query.filter_by(member_id=member.id).count()
        
        # Log the deletion
        print(f"[DELETION LOG] Member deleted: {member_id_str} ({full_name})")
        print(f"[DELETION LOG] Deleted by: {current_user.username} on {datetime.now()}")
        print(f"[DELETION LOG] Reason: {deletion_reason}")
        print(f"[DELETION LOG] Total loans history: {total_loans}")
        
        # Delete the member
        # Note: All related loans will be preserved in the database (cascade not set)
        # This ensures a complete audit trail of historical transactions
        db.session.delete(member)
        db.session.commit()
        
        flash(
            f'Member "{full_name}" ({member_id_str}) has been permanently deleted. '
            f'Historical loan records have been preserved for audit purposes.',
            'success'
        )
        return redirect(url_for('users.member_list'))
    
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting member: {str(e)}', 'error')
        return redirect(url_for('users.delete_member_confirm', member_id=member.id))


# ============ Student Administration ============

@users_bp.route('/students/active')
@login_required
@permission_required(Permission.ADMIN)
def active_students():
    """List active students based on login activity"""
    page = request.args.get('page', 1, type=int)
    
    # Students ordered by last login (active first)
    students = Member.query.filter_by(member_type='Student', is_active=True)\
        .order_by(Member.last_login.desc()).paginate(page=page, per_page=50)
    
    return render_template('users/active_students.html', students=students)


@users_bp.route('/students/graduation-list')
@login_required
@permission_required(Permission.ADMIN)
def graduation_list():
    """List students marked for graduation (Form 5) or deletion"""
    page = request.args.get('page', 1, type=int)
    filter_type = request.args.get('filter', 'all')  # all, graduated, marked_deletion
    
    query = Member.query.filter_by(member_type='Student')
    
    if filter_type == 'graduated':
        query = query.filter(Member.form_level >= 6)
    elif filter_type == 'marked_deletion':
        query = query.filter(Member.mark_for_deletion == True)
    elif filter_type == 'form5':
        query = query.filter(Member.form_level == 5)
    
    students = query.order_by(Member.form_level.desc(), Member.full_name)\
        .paginate(page=page, per_page=50)
    
    return render_template('users/graduation_list.html', students=students, filter_type=filter_type)


@users_bp.route('/students/<int:member_id>/mark-for-deletion', methods=['POST'])
@login_required
@permission_required(Permission.ADMIN)
def mark_for_deletion(member_id):
    """Mark student for deletion"""
    member = Member.query.get_or_404(member_id)
    member.mark_for_deletion = True
    db.session.commit()
    flash(f'{member.full_name} marked for deletion', 'warning')
    return redirect(request.referrer or url_for('users.graduation_list'))


@users_bp.route('/students/<int:member_id>/unmark-deletion', methods=['POST'])
@login_required
@permission_required(Permission.ADMIN)
def unmark_for_deletion(member_id):
    """Unmark student for deletion"""
    member = Member.query.get_or_404(member_id)
    member.mark_for_deletion = False
    db.session.commit()
    flash(f'{member.full_name} unmarked for deletion', 'success')
    return redirect(request.referrer or url_for('users.graduation_list'))


@users_bp.route('/students/<int:member_id>/delete', methods=['POST'])
@login_required
@permission_required(Permission.ADMIN)
def delete_student(member_id):
    """Delete a marked student"""
    member = Member.query.get_or_404(member_id)
    
    if not member.mark_for_deletion:
        flash('Student is not marked for deletion', 'error')
        return redirect(request.referrer or url_for('users.graduation_list'))
    
    # Don't delete if has active loans
    if member.active_loans_count > 0:
        flash('Cannot delete: Student has active loans', 'error')
        return redirect(request.referrer)
    
    full_name = member.full_name
    db.session.delete(member)
    db.session.commit()
    flash(f'Student "{full_name}" deleted successfully', 'success')
    return redirect(url_for('users.graduation_list', filter='marked_deletion'))


@users_bp.route('/admin/promote-students', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.ADMIN)
def promote_students():
    """Promote all students to next form (yearly operation)"""
    if request.method == 'POST':
        # Confirm button was clicked
        action = request.form.get('action')
        
        if action == 'promote':
            # Get all active Form 1-4 students and promote them
            students_to_promote = Member.query.filter(
                Member.member_type == 'Student',
                Member.form_level.between(1, 4),
                Member.is_active == True
            ).all()
            
            promoted_count = 0
            for student in students_to_promote:
                student.form_level += 1
                promoted_count += 1
            
            # Mark Form 5 students as graduated
            form5_students = Member.query.filter(
                Member.member_type == 'Student',
                Member.form_level == 5,
                Member.is_active == True
            ).all()
            
            graduated_count = 0
            for student in form5_students:
                student.form_level = 6
                student.graduation_date = datetime.now()
                graduated_count += 1
            
            db.session.commit()
            flash(f'Promoted {promoted_count} students. Graduated {graduated_count} Form 5 students', 'success')
            return redirect(url_for('users.graduation_list', filter='graduated'))
        
        # Show confirmation page
        form1_count = Member.query.filter(Member.form_level == 1, Member.member_type == 'Student', Member.is_active == True).count()
        form2_count = Member.query.filter(Member.form_level == 2, Member.member_type == 'Student', Member.is_active == True).count()
        form3_count = Member.query.filter(Member.form_level == 3, Member.member_type == 'Student', Member.is_active == True).count()
        form4_count = Member.query.filter(Member.form_level == 4, Member.member_type == 'Student', Member.is_active == True).count()
        form5_count = Member.query.filter(Member.form_level == 5, Member.member_type == 'Student', Member.is_active == True).count()
        
        stats = {
            'form1': form1_count,
            'form2': form2_count,
            'form3': form3_count,
            'form4': form4_count,
            'form5': form5_count
        }
        
        return render_template('users/promote_students.html', stats=stats)
    
    # GET - show confirmation form
    form1_count = Member.query.filter(Member.form_level == 1, Member.member_type == 'Student', Member.is_active == True).count()
    form2_count = Member.query.filter(Member.form_level == 2, Member.member_type == 'Student', Member.is_active == True).count()
    form3_count = Member.query.filter(Member.form_level == 3, Member.member_type == 'Student', Member.is_active == True).count()
    form4_count = Member.query.filter(Member.form_level == 4, Member.member_type == 'Student', Member.is_active == True).count()
    form5_count = Member.query.filter(Member.form_level == 5, Member.member_type == 'Student', Member.is_active == True).count()
    
    stats = {
        'form1': form1_count,
        'form2': form2_count,
        'form3': form3_count,
        'form4': form4_count,
        'form5': form5_count
    }
    
    return render_template('users/promote_students.html', stats=stats)


# ============ Excel Import ============

@users_bp.route('/students/import', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.ADMIN)
def import_students():
    """Import students from Excel file"""
    class_groups = get_class_groups()
    form_levels = get_form_levels()
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return render_template('users/import_students.html', 
                                 class_groups=class_groups, 
                                 form_levels=form_levels)
        
        file = request.files['file']
        filepath, error = save_upload_file(file)
        
        if error:
            flash(f'Upload error: {error}', 'error')
            return render_template('users/import_students.html', 
                                 class_groups=class_groups, 
                                 form_levels=form_levels)
        
        # Preview mode - show what will be imported
        preview = request.form.get('preview')
        if preview == 'on':
            rows, error = read_excel_file(filepath)
            if error:
                flash(f'Error reading file: {error}', 'error')
            else:
                return render_template('users/import_students_preview.html', 
                                     rows=rows, 
                                     filepath=filepath,
                                     class_groups=class_groups,
                                     form_levels=form_levels)
        
        # Actual import
        success_count, errors, imported = import_student_data(filepath)
        
        if success_count > 0:
            flash(f'Successfully imported {success_count} students', 'success')
        
        if errors:
            for error in errors[:5]:  # Show first 5 errors
                flash(f'Import error: {error}', 'warning')
            if len(errors) > 5:
                flash(f'... and {len(errors) - 5} more errors', 'warning')
        
        return redirect(url_for('users.member_list'))
    
    return render_template('users/import_students.html', 
                         class_groups=class_groups, 
                         form_levels=form_levels)


@users_bp.route('/staff/import', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.ADMIN)
def import_staff():
    """Import staff users from Excel file"""
    roles = Role.query.all()
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return render_template('users/import_staff.html', roles=roles)
        
        file = request.files['file']
        filepath, error = save_upload_file(file)
        
        if error:
            flash(f'Upload error: {error}', 'error')
            return render_template('users/import_staff.html', roles=roles)
        
        # Read the file
        rows, error = read_excel_file(filepath)
        if error:
            flash(f'Error reading file: {error}', 'error')
            return render_template('users/import_staff.html', roles=roles)
        
        # Preview mode
        preview = request.form.get('preview')
        if preview == 'on':
            return render_template('users/import_staff_preview.html', 
                                 rows=rows, 
                                 filepath=filepath,
                                 roles=roles)
        
        # Actual import - process staff data
        success_count = 0
        errors = []
        
        for idx, row in enumerate(rows, start=2):
            try:
                if len(row) < 4:
                    errors.append(f'Row {idx}: Missing required columns')
                    continue
                
                username = str(row[0] or '').strip()
                email = str(row[1] or '').strip()
                full_name = str(row[2] or '').strip()
                role_name = str(row[3] or '').strip()
                
                if not username or not email:
                    errors.append(f'Row {idx}: Missing username or email')
                    continue
                
                # Check if user exists
                if User.query.filter_by(username=username).first():
                    errors.append(f'Row {idx}: Username "{username}" already exists')
                    continue
                
                # Find role
                role = Role.query.filter_by(name=role_name).first()
                if not role:
                    errors.append(f'Row {idx}: Role "{role_name}" not found')
                    continue
                
                # Create user with default password
                user = User(
                    username=username,
                    email=email,
                    full_name=full_name or username,
                    role_id=role.id,
                    is_active=True
                )
                user.set_password('Password123')  # Default password - user should change on first login
                
                db.session.add(user)
                success_count += 1
                
            except Exception as e:
                errors.append(f'Row {idx}: {str(e)}')
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f'Database error: {str(e)}', 'error')
            return render_template('users/import_staff.html', roles=roles)
        
        if success_count > 0:
            flash(f'Successfully imported {success_count} staff users', 'success')
        
        if errors:
            for error in errors[:5]:
                flash(f'Import error: {error}', 'warning')
            if len(errors) > 5:
                flash(f'... and {len(errors) - 5} more errors', 'warning')
        
        return redirect(url_for('users.staff_list'))
    
    return render_template('users/import_staff.html', roles=roles)


@users_bp.route('/api/class-groups')
@login_required
def api_class_groups():
    """API endpoint to get class groups"""
    return jsonify(get_class_groups())


@users_bp.route('/api/form-levels')
@login_required
def api_form_levels():
    """API endpoint to get form levels"""
    return jsonify(get_form_levels())


# ============ Promote/Demote Staff ============

@users_bp.route('/members/<int:member_id>/promote-staff', methods=['POST'])
@login_required
@permission_required(Permission.MANAGE_USERS)
def promote_to_staff(member_id):
    """Promote a member to staff (Student Assistant)"""
    # Get member
    member = Member.query.get_or_404(member_id)
    role = Role.query.filter_by(name='Student Assistant').first()
    
    # Change member type to Staff
    member.member_type = 'Student Assistant'
    member.form_level = None  # Staff don't have form level
    member.class_group = None

    # Keep a matching staff User row so checkout/return audit fields can reference users.id
    user = User.query.get(member.id)
    if user is None:
        username = member.member_id
        if User.query.filter(User.username == username, User.id != member.id).first():
            username = f'staff_{member.id}'

        email = member.email
        if email and User.query.filter(User.email == email, User.id != member.id).first():
            email = f'{member.member_id.lower()}@local.invalid'
        elif not email:
            email = f'{member.member_id.lower()}@local.invalid'

        user = User(
            id=member.id,
            username=username,
            email=email,
            full_name=member.full_name,
            is_active=True,
            role=role,
            password_hash=member.password_hash,
        )
        db.session.add(user)
    else:
        user.username = member.member_id if user.username != member.member_id else user.username
        user.email = member.email or user.email
        user.full_name = member.full_name
        user.is_active = True
        if role:
            user.role = role
        if member.password_hash:
            user.password_hash = member.password_hash

    db.session.commit()
    
    flash(f'{member.full_name} promoted to Student Assistant', 'success')
    return redirect(request.referrer or url_for('users.member_list'))


@users_bp.route('/members/<int:member_id>/demote-staff', methods=['POST'])
@login_required
@permission_required(Permission.MANAGE_USERS)
def demote_from_staff(member_id):
    """Demote a staff member back to regular student"""
    # Get member
    member = Member.query.get_or_404(member_id)
    
    # Change member type back to Student
    member.member_type = 'Student'
    member.form_level = 1  # Default to Form 1

    # Disable the linked staff login so the account falls back to the member login
    user = User.query.get(member.id)
    if user:
        user.is_active = False

    db.session.commit()
    
    flash(f'{member.full_name} demoted to Student', 'success')
    return redirect(request.referrer or url_for('users.member_list'))


@users_bp.route('/staff/<int:user_id>/delete', methods=['POST'])
@login_required
@permission_required(Permission.MANAGE_USERS)
def delete_staff(user_id):
    """Delete a staff user account completely"""
    # Don't allow deleting yourself
    if user_id == current_user.id:
        flash('Cannot delete your own staff account', 'error')
        return redirect(url_for('users.staff_list'))
    
    # Get staff user
    user = User.query.get_or_404(user_id)
    
    # Delete the staff user
    username = user.username
    db.session.delete(user)
    db.session.commit()
    
    flash(f'Staff account "{username}" deleted', 'success')
    return redirect(url_for('users.staff_list'))
