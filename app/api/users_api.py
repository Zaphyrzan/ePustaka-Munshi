"""
Users API Routes - JSON endpoints for user and member management
Handles staff and student account management
"""
from flask import Blueprint, request, current_app
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import case, func
from sqlalchemy.orm import joinedload
from app import db
from app.models import User, Member, Role, Permission, ClassGroup
from app.models.circulation import Loan, LoanStatus
from app.utils.serializers import UserSerializer, MemberSerializer, ApiResponse

bp = Blueprint('api_users', __name__, url_prefix='/api/users')


def _has_permission(permission):
    return hasattr(current_user, 'can') and current_user.can(permission)


def _annotate_loan_counts(members):
    """Batch-compute active/overdue loan counts for a page of members.

    MemberSerializer picks these up via _active_loans/_overdue_loans,
    replacing ~5 COUNT queries per member with one grouped query.
    """
    member_ids = [member.id for member in members]
    if not member_ids:
        return

    rows = db.session.query(
        Loan.member_id,
        func.sum(case((Loan.status == LoanStatus.ACTIVE.value, 1), else_=0)),
        func.sum(case((Loan.status == LoanStatus.OVERDUE.value, 1), else_=0)),
    ).filter(Loan.member_id.in_(member_ids)).group_by(Loan.member_id).all()

    counts = {member_id: (active or 0, overdue or 0) for member_id, active, overdue in rows}
    for member in members:
        member._active_loans, member._overdue_loans = counts.get(member.id, (0, 0))


def _can_view_members():
    return _has_permission(Permission.MANAGE_MEMBERS) or _has_permission(Permission.CHECKOUT)


def _is_current_member(member):
    return current_user.__class__.__name__ == 'Member' and current_user.id == member.id


@bp.route('/staff', methods=['GET'])
@login_required
def list_staff():
    """
    Get paginated list of staff users (admin only)
    
    Query parameters:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20)
    - search: Search by username or full_name
    - role_id: Filter by role
    - active: Filter by active status (true/false)
    
    Response: Paginated list of staff users
    """
    try:
        if not _has_permission(Permission.MANAGE_USERS):
            return ApiResponse.error('Admin access required', status_code=403)
        
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        if page < 1:
            page = 1
        
        # Build query with role relationship
        query = User.query.options(joinedload(User.role))
        
        # Search filter
        search = request.args.get('search', '').strip()
        if search:
            search_term = f'%{search}%'
            query = query.filter(
                (User.username.ilike(search_term)) |
                (User.full_name.ilike(search_term))
            )
        
        # Role filter
        role_id = request.args.get('role_id', type=int)
        if role_id:
            query = query.filter(User.role_id == role_id)
        
        # Active filter
        active = request.args.get('active', '').lower()
        if active in ['true', 'false']:
            query = query.filter(User.is_active == (active == 'true'))
        
        query = query.order_by(User.created_at.desc())
        
        total = query.count()
        offset = (page - 1) * per_page
        users = query.offset(offset).limit(per_page).all()
        
        items = [UserSerializer.to_dict(user) for user in users]
        total_pages = (total + per_page - 1) // per_page
        
        return ApiResponse.success({
            'items': items,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1,
            }
        })
    
    except Exception as e:
        current_app.logger.error(f'List staff error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/staff/<int:user_id>', methods=['GET'])
@login_required
def get_staff(user_id):
    """Get staff user details"""
    try:
        if not _has_permission(Permission.MANAGE_USERS):
            return ApiResponse.error('Admin access required', status_code=403)
        
        user = User.query.options(joinedload(User.role)).get(user_id)
        if not user:
            return ApiResponse.error('Staff not found', status_code=404)
        
        return ApiResponse.success(UserSerializer.to_dict(user))
    
    except Exception as e:
        current_app.logger.error(f'Get staff error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/staff', methods=['POST'])
@login_required
def create_staff():
    """
    Create new staff account
    
    Request JSON:
    {
        "username": "staff_username",
        "email": "staff@example.com",
        "password": "securepassword",
        "full_name": "Full Name",
        "role_id": 1
    }
    """
    try:
        if not _has_permission(Permission.MANAGE_USERS):
            return ApiResponse.error('Admin access required', status_code=403)
        
        data = request.get_json()
        if not data:
            return ApiResponse.error('Request body required', status_code=400)
        
        # Validate required fields
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not email or not password:
            return ApiResponse.error('Username, email, and password required', status_code=400)
        
        # Check for duplicates
        if User.query.filter_by(username=username).first():
            return ApiResponse.error('Username already exists', status_code=409)
        
        if User.query.filter_by(email=email).first():
            return ApiResponse.error('Email already exists', status_code=409)
        
        # Get role
        role_id = data.get('role_id')
        if not role_id:
            role = Role.query.filter_by(is_default=True).first()
            if not role:
                return ApiResponse.error('No default role available', status_code=500)
            role_id = role.id
        else:
            role = Role.query.get(role_id)
            if not role:
                return ApiResponse.error('Role not found', status_code=404)
        
        # Create user
        user = User(
            username=username,
            email=email,
            full_name=data.get('full_name', '').strip(),
            role_id=role_id,
            is_active=True
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        return ApiResponse.success(
            UserSerializer.to_dict(user),
            message='Staff account created successfully',
            status_code=201
        )
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Create staff error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/staff/<int:user_id>', methods=['PUT'])
@login_required
def update_staff(user_id):
    """Update staff account"""
    try:
        if not _has_permission(Permission.MANAGE_USERS):
            return ApiResponse.error('Admin access required', status_code=403)
        
        user = User.query.get(user_id)
        if not user:
            return ApiResponse.error('Staff not found', status_code=404)
        
        data = request.get_json()
        if not data:
            return ApiResponse.error('Request body required', status_code=400)
        
        # Update fields
        if 'email' in data:
            email = data['email'].strip()
            if User.query.filter(User.email == email, User.id != user_id).first():
                return ApiResponse.error('Email already exists', status_code=409)
            user.email = email
        
        if 'full_name' in data:
            user.full_name = data['full_name'].strip() or None
        
        if 'role_id' in data:
            role = Role.query.get(data['role_id'])
            if not role:
                return ApiResponse.error('Role not found', status_code=404)
            user.role_id = data['role_id']
        
        if 'is_active' in data:
            user.is_active = bool(data['is_active'])
        
        db.session.commit()
        
        return ApiResponse.success(UserSerializer.to_dict(user), message='Staff updated successfully')
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Update staff error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/members', methods=['GET'])
@login_required
def list_members():
    """
    Get paginated list of members
    
    Query parameters:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 30)
    - search: Search by name, member_id, student_id
    - active: Filter by active status (true/false)
    """
    try:
        if not _can_view_members():
            return ApiResponse.error('Staff access required', status_code=403)

        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 30, type=int), 100)
        
        if page < 1:
            page = 1
        
        query = Member.query
        
        # Search filter
        search = request.args.get('search', '').strip()
        if search:
            search_term = f'%{search}%'
            query = query.filter(
                (Member.full_name.ilike(search_term)) |
                (Member.member_id.ilike(search_term)) |
                (Member.class_group.ilike(search_term))
            )
        
        # Active filter
        active = request.args.get('active', '').lower()
        if active in ['true', 'false']:
            query = query.filter(Member.is_active == (active == 'true'))

        # Member type filter (Student | Student Assistant | Staff | External)
        member_type = request.args.get('type', '').strip()
        if member_type:
            query = query.filter(Member.member_type == member_type)

        query = query.order_by(Member.created_at.desc())
        
        total = query.count()
        offset = (page - 1) * per_page
        members = query.offset(offset).limit(per_page).all()

        _annotate_loan_counts(members)
        items = [MemberSerializer.to_dict(member) for member in members]
        total_pages = (total + per_page - 1) // per_page
        
        return ApiResponse.success({
            'items': items,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1,
            }
        })
    
    except Exception as e:
        current_app.logger.error(f'List members error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/members/<int:member_id>', methods=['GET'])
@login_required
def get_member(member_id):
    """Get member details"""
    try:
        member = Member.query.get(member_id)
        if not member:
            return ApiResponse.error('Member not found', status_code=404)

        if not (_can_view_members() or _is_current_member(member)):
            return ApiResponse.error('Permission denied', status_code=403)
        
        return ApiResponse.success(MemberSerializer.to_dict(member))
    
    except Exception as e:
        current_app.logger.error(f'Get member error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/members', methods=['POST'])
@login_required
def create_member():
    """
    Create new member account
    
    Request JSON:
    {
        "full_name": "Student Name",
        "email": "student@example.com",
        "student_id": "STU12345",
        "phone": "+60123456789",
        "password": "password"
    }
    """
    try:
        if not _has_permission(Permission.MANAGE_MEMBERS):
            return ApiResponse.error('Permission denied', status_code=403)
        
        data = request.get_json()
        if not data:
            return ApiResponse.error('Request body required', status_code=400)
        
        # Validate required fields
        full_name = data.get('full_name', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        
        if not full_name or not email or not password:
            return ApiResponse.error('Full name, email, and password required', status_code=400)
        
        # Check uniqueness
        if Member.query.filter_by(email=email).first():
            return ApiResponse.error('Email already exists', status_code=409)

        requested_member_id = data.get('member_id', '').strip()
        if requested_member_id and Member.query.filter_by(member_id=requested_member_id).first():
            return ApiResponse.error('Member ID already exists', status_code=409)
        
        # Generate member ID
        from app.models.member import generate_member_id
        member_id = requested_member_id or generate_member_id()
        
        # Create member
        member = Member(
            full_name=full_name,
            email=email,
            member_id=member_id,
            phone=data.get('phone', '').strip() or None,
            member_type=data.get('member_type', 'Student'),
            form_level=data.get('form_level') or 1,
            class_group=data.get('class_group', '').strip() or None,
            student_year=data.get('student_year'),
            is_active=True
        )
        member.set_password(password)
        
        db.session.add(member)
        db.session.commit()
        
        return ApiResponse.success(
            MemberSerializer.to_dict(member),
            message='Member account created successfully',
            status_code=201
        )
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Create member error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/members/<int:member_id>', methods=['PUT'])
@login_required
def update_member(member_id):
    """Update member account"""
    try:
        member = Member.query.get(member_id)
        if not member:
            return ApiResponse.error('Member not found', status_code=404)
        
        # Check permission - can update own profile or if admin
        if not (_is_current_member(member) or _has_permission(Permission.MANAGE_MEMBERS)):
            return ApiResponse.error('Permission denied', status_code=403)
        
        data = request.get_json()
        if not data:
            return ApiResponse.error('Request body required', status_code=400)
        
        # Update fields
        if 'email' in data:
            email = data['email'].strip()
            if Member.query.filter(Member.email == email, Member.id != member_id).first():
                return ApiResponse.error('Email already exists', status_code=409)
            member.email = email
        
        if 'full_name' in data:
            member.full_name = data['full_name'].strip() or member.full_name
        
        if 'phone' in data:
            member.phone = data['phone'].strip() or None

        if 'class_group' in data:
            member.class_group = data['class_group'].strip() or None

        if 'form_level' in data and _has_permission(Permission.MANAGE_MEMBERS):
            member.form_level = data.get('form_level') or member.form_level

        if 'student_year' in data and _has_permission(Permission.MANAGE_MEMBERS):
            member.student_year = data.get('student_year')

        if 'member_type' in data and _has_permission(Permission.MANAGE_MEMBERS):
            member.member_type = data.get('member_type') or member.member_type
        
        if 'is_active' in data:
            if _has_permission(Permission.MANAGE_MEMBERS):
                member.is_active = bool(data['is_active'])
        
        db.session.commit()
        
        return ApiResponse.success(MemberSerializer.to_dict(member), message='Member updated successfully')
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Update member error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)



@bp.route('/members/<int:member_id>', methods=['DELETE'])
@login_required
def delete_member(member_id):
    """Delete a member (blocked while they have active loans)"""
    try:
        if not _has_permission(Permission.MANAGE_USERS):
            return ApiResponse.error('Insufficient permissions', status_code=403)
        member = Member.query.get(member_id)
        if not member:
            return ApiResponse.error('Member not found', status_code=404)
        from app.models import Loan, LoanStatus
        active = Loan.query.filter(
            Loan.member_id == member.id,
            Loan.status.in_([LoanStatus.ACTIVE.value, LoanStatus.OVERDUE.value]),
        ).count()
        if active:
            return ApiResponse.error(f'Member has {active} active loan(s)', status_code=409)
        db.session.delete(member)
        db.session.commit()
        return ApiResponse.success(message='Member deleted')
    except Exception as e:
        db.session.rollback()
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/staff/<int:user_id>', methods=['DELETE'])
@login_required
def delete_staff(user_id):
    """Delete a staff account (cannot delete yourself)"""
    try:
        if not _has_permission(Permission.MANAGE_USERS):
            return ApiResponse.error('Insufficient permissions', status_code=403)
        if user_id == current_user.id:
            return ApiResponse.error('Cannot delete your own staff account', status_code=409)
        user = User.query.get(user_id)
        if not user:
            return ApiResponse.error('Staff not found', status_code=404)
        db.session.delete(user)
        db.session.commit()
        return ApiResponse.success(message='Staff account deleted')
    except Exception as e:
        db.session.rollback()
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/members/<int:member_id>/promote', methods=['POST'])
@login_required
def promote_member(member_id):
    """Promote a member to Student Assistant (mirrors users.promote_to_staff)"""
    try:
        if not _has_permission(Permission.MANAGE_USERS):
            return ApiResponse.error('Insufficient permissions', status_code=403)
        from app.models import Role
        member = Member.query.get(member_id)
        if not member:
            return ApiResponse.error('Member not found', status_code=404)
        role = Role.query.filter_by(name='Student Assistant').first()

        # A Student Assistant is still a student in their class — keep
        # form_level and class_group so they remain in the NILAM leaderboard.
        member.member_type = 'Student Assistant'

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
                id=member.id, username=username, email=email,
                full_name=member.full_name, is_active=True, role=role,
                password_hash=member.password_hash,
            )
            db.session.add(user)
        else:
            user.full_name = member.full_name
            user.is_active = True
            if role:
                user.role = role
            if member.password_hash:
                user.password_hash = member.password_hash
        db.session.commit()
        return ApiResponse.success(MemberSerializer.to_dict(member), message=f'{member.full_name} promoted to Student Assistant')
    except Exception as e:
        db.session.rollback()
        return ApiResponse.error(str(e), status_code=500)


# ============ Class Groups ============

@bp.route('/class-groups', methods=['GET'])
@login_required
def list_class_groups():
    """Return the merged list of class names for the dropdown."""
    try:
        from app.utils.excel_import import get_class_groups
        return ApiResponse.success(get_class_groups())
    except Exception as e:
        current_app.logger.error(f'List class groups error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/class-groups', methods=['POST'])
@login_required
def create_class_group():
    """
    Add a new class name so it appears in the dropdown even before any
    member is assigned to it. Admin only.

    Request JSON: {"name": "Bestari", "form_level": 1}
    """
    try:
        if not _has_permission(Permission.MANAGE_MEMBERS):
            return ApiResponse.error('Permission denied', status_code=403)

        data = request.get_json() or {}
        name = (data.get('name') or '').strip()
        if not name:
            return ApiResponse.error('Class name is required', status_code=400)
        if len(name) > 64:
            return ApiResponse.error('Class name cannot exceed 64 characters', status_code=400)

        existing = ClassGroup.query.filter(func.lower(ClassGroup.name) == name.lower()).first()
        if existing:
            if not existing.is_active:
                existing.is_active = True
                db.session.commit()
            return ApiResponse.success(existing.to_dict(), message='Class already exists')

        form_level = data.get('form_level')
        try:
            form_level = int(form_level) if form_level not in (None, '') else None
        except (ValueError, TypeError):
            form_level = None

        cg = ClassGroup(name=name, form_level=form_level, is_active=True)
        db.session.add(cg)
        db.session.commit()
        return ApiResponse.success(cg.to_dict(), message='Class added', status_code=201)
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Create class group error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)


# ============ Student Excel Import ============

@bp.route('/members/import/preview', methods=['POST'])
@login_required
def import_members_preview():
    """
    Parse an uploaded student Excel file and return a preview WITHOUT saving.

    Accepts multipart/form-data with a 'file' field. Supports both the SMK
    Munshi class-roster layout (one sheet per class, names in column A) and
    structured header-column files.
    """
    try:
        if not _has_permission(Permission.MANAGE_MEMBERS):
            return ApiResponse.error('Permission denied', status_code=403)

        if 'file' not in request.files:
            return ApiResponse.error('No file uploaded', status_code=400)

        from app.utils.excel_import import save_upload_file, parse_student_workbook, get_class_groups
        filepath, error = save_upload_file(request.files['file'])
        if error:
            return ApiResponse.error(error, status_code=400)

        sheets, error = parse_student_workbook(filepath)
        if error:
            return ApiResponse.error(error, status_code=400)

        total = sum(len(s['students']) for s in sheets)
        return ApiResponse.success({
            'sheets': sheets,
            'total': total,
            'class_groups': get_class_groups(),
        })
    except Exception as e:
        current_app.logger.error(f'Import preview error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/members/import/commit', methods=['POST'])
@login_required
def import_members_commit():
    """
    Create members from the (possibly edited) preview rows.

    Request JSON: {"students": [{full_name, form_level, class_group, email, phone, member_type}, ...]}
    """
    try:
        if not _has_permission(Permission.MANAGE_MEMBERS):
            return ApiResponse.error('Permission denied', status_code=403)

        data = request.get_json() or {}
        students = data.get('students') or []
        if not isinstance(students, list) or not students:
            return ApiResponse.error('No students to import', status_code=400)
        if len(students) > 5000:
            return ApiResponse.error('Too many rows in one import (max 5000)', status_code=400)

        from app.utils.excel_import import commit_student_records
        success_count, errors, imported = commit_student_records(students)

        return ApiResponse.success({
            'imported': success_count,
            'errors': errors,
        }, message=f'Imported {success_count} student(s)')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Import commit error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/members/<int:member_id>/demote', methods=['POST'])
@login_required
def demote_member(member_id):
    """Demote a Student Assistant back to Student (mirrors users.demote_from_staff)"""
    try:
        if not _has_permission(Permission.MANAGE_USERS):
            return ApiResponse.error('Insufficient permissions', status_code=403)
        member = Member.query.get(member_id)
        if not member:
            return ApiResponse.error('Member not found', status_code=404)
        member.member_type = 'Student'
        member.form_level = 1
        user = User.query.get(member.id)
        if user:
            user.is_active = False
        db.session.commit()
        return ApiResponse.success(MemberSerializer.to_dict(member), message=f'{member.full_name} demoted to Student')
    except Exception as e:
        db.session.rollback()
        return ApiResponse.error(str(e), status_code=500)
