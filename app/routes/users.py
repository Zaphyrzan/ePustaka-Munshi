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
        # Auto-generate member_id (don't accept manual input)
        member_id = generate_member_id()
        
        member = Member(
            member_id=member_id,
            full_name=request.form.get('full_name', '').strip(),
            email=request.form.get('email', '').strip() or None,
            phone=request.form.get('phone', '').strip() or None,
            member_type=request.form.get('member_type', 'Student'),
            form_level=request.form.get('form_level', type=int, default=1),
            class_group=request.form.get('class_group', '').strip() or None,
            student_year=datetime.now().year,
            is_active=True
        )
        
        db.session.add(member)
        db.session.commit()
        
        flash(f'Member "{member.full_name}" created successfully (ID: {member.member_id})', 'success')
        return redirect(url_for('users.view_member', member_id=member.id))
    
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
    """Edit a member"""
    member = Member.query.get_or_404(member_id)
    
    if request.method == 'POST':
        member.full_name = request.form.get('full_name', '').strip()
        member.email = request.form.get('email', '').strip() or None
        member.phone = request.form.get('phone', '').strip() or None
        member.member_type = request.form.get('member_type', 'Student')
        member.form_level = request.form.get('form_level', type=int, default=1)
        member.class_group = request.form.get('class_group', '').strip() or None
        member.is_active = request.form.get('is_active') == 'on'
        member.mark_for_deletion = request.form.get('mark_for_deletion') == 'on'
        member.notes = request.form.get('notes', '').strip() or None
        
        # If marking as graduated, set form_level to 6
        if request.form.get('mark_graduated') == 'on':
            member.form_level = 6
            member.graduation_date = datetime.now()
        
        db.session.commit()
        
        flash(f'Member "{member.full_name}" updated successfully', 'success')
        return redirect(url_for('users.view_member', member_id=member.id))
    
    return render_template('users/edit_member.html', member=member)


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
    
    # Change member type to Staff
    member.member_type = 'Student Assistant'
    member.form_level = None  # Staff don't have form level
    member.class_group = None
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
