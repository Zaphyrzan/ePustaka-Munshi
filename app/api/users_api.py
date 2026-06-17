"""
Users API Routes - JSON endpoints for user and member management
Handles staff and student account management
"""
from flask import Blueprint, request, current_app
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import case, func, exists, and_
from sqlalchemy.orm import joinedload
from app import db
from app.models import User, Member, Role, Permission, ClassGroup
from app.models.circulation import Loan, LoanStatus
from app.utils.serializers import UserSerializer, MemberSerializer, ApiResponse
from app.utils.text_format import to_caps

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
        
        # Build query with role relationship. The Administration tab only shows
        # operators: exclude role "Student" (legacy/seed rows) and exclude
        # "demoted leftovers" — a User whose linked Member is now a regular
        # type (Student/Staff/External), i.e. they were demoted off the team.
        # A promoted account's username IS the member's member_id (set on promote),
        # which is the reliable link (User.id can coincidentally collide).
        is_regular_member = exists().where(
            and_(Member.member_id == User.username, Member.member_type.in_(['Student', 'Staff', 'External']))
        )
        query = (
            User.query.options(joinedload(User.role))
            .join(Role)
            .filter(Role.name != 'Student')
            .filter(~is_regular_member)
        )

        # Search filter
        search = request.args.get('search', '').strip()
        if search:
            search_term = f'%{search}%'
            query = query.filter(
                (User.username.ilike(search_term)) |
                (User.full_name.ilike(search_term))
            )

        # Role filter — by id or by name (Administrator / Librarian / Library Prefect)
        role_id = request.args.get('role_id', type=int)
        if role_id:
            query = query.filter(User.role_id == role_id)
        role_name = request.args.get('role', '').strip()
        if role_name:
            query = query.filter(Role.name == role_name)
        
        # Active filter
        active = request.args.get('active', '').lower()
        if active in ['true', 'false']:
            query = query.filter(User.is_active == (active == 'true'))

        # Sorting (clickable column headers in the UI)
        sort = request.args.get('sort', 'created_at')
        order = request.args.get('order', 'desc' if sort == 'created_at' else 'asc')
        sort_map = {
            'username': User.username,
            'full_name': User.full_name,
            'email': User.email,
            'role': Role.name,
            'created_at': User.created_at,
        }
        col = sort_map.get(sort, User.created_at)
        query = query.order_by(col.asc() if order == 'asc' else col.desc())

        total = query.count()
        offset = (page - 1) * per_page
        users = query.offset(offset).limit(per_page).all()

        # Annotate which operators are promoted members (username == member_id,
        # member is an operator type) so Administration can offer "demote".
        usernames = [u.username for u in users]
        promoted = {}  # username -> (member_type, member_db_id)
        if usernames:
            for m in Member.query.filter(
                Member.member_id.in_(usernames),
                Member.member_type.in_(['Library Prefect', 'Librarian']),
            ).all():
                promoted[m.member_id] = (m.member_type, m.id)

        items = []
        for user in users:
            d = UserSerializer.to_dict(user)
            info = promoted.get(user.username)
            d['promoted_member_type'] = info[0] if info else None  # None = real staff account
            d['linked_member_id'] = info[1] if info else None
            items.append(d)
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

        # Accept the role by name too (the edit form sends a name, not an id).
        if 'role' in data and data.get('role'):
            role = Role.query.filter_by(name=data['role']).first()
            if role:
                user.role_id = role.id

        # Password reset: leave blank to keep the existing one.
        new_password = (data.get('password') or '').strip()
        if new_password:
            user.set_password(new_password)

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

        # Member type filter (Student | Staff | External). Promoted operators
        # (Library Prefect, Librarian) live in the Administration tab, so the
        # Members list excludes them unless explicitly requested by type.
        member_type = request.args.get('type', '').strip()
        if member_type:
            query = query.filter(Member.member_type == member_type)
        elif request.args.get('include_operators', '').lower() != 'true':
            query = query.filter(Member.member_type.notin_(['Library Prefect', 'Librarian']))

        # Graduated filter: Form 5 students are candidates for year-end clearing.
        if request.args.get('graduated', '').lower() == 'true':
            query = query.filter(Member.member_type == 'Student', Member.form_level >= 5)

        # Sorting (clickable column headers in the UI)
        sort = request.args.get('sort', 'created_at')
        order = request.args.get('order', 'desc' if sort == 'created_at' else 'asc')
        sort_map = {
            'member_id': Member.member_id,
            'full_name': Member.full_name,
            'member_type': Member.member_type,
            'form_level': Member.form_level,
            'created_at': Member.created_at,
        }
        col = sort_map.get(sort, Member.created_at)
        query = query.order_by(col.asc() if order == 'asc' else col.desc())

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
        
        # Generate a standardized member ID for the member's type when one
        # wasn't supplied (STU#### students, TCH#### staff, EXT#### external).
        from app.models.member import generate_member_id
        member_id = requested_member_id or generate_member_id(data.get('member_type', 'Student'))
        
        # Create member
        member = Member(
            full_name=to_caps(full_name),
            email=email,
            member_id=member_id,
            phone=data.get('phone', '').strip() or None,
            member_type=data.get('member_type', 'Student'),
            form_level=data.get('form_level') or 1,
            class_group=to_caps(data.get('class_group', '').strip()) or None,
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
            member.full_name = to_caps(data['full_name'].strip()) or member.full_name
        
        if 'phone' in data:
            member.phone = data['phone'].strip() or None

        if 'class_group' in data:
            member.class_group = to_caps(data['class_group'].strip()) or None

        if 'form_level' in data and _has_permission(Permission.MANAGE_MEMBERS):
            member.form_level = data.get('form_level') or member.form_level

        if 'student_year' in data and _has_permission(Permission.MANAGE_MEMBERS):
            member.student_year = data.get('student_year')

        if 'member_type' in data and _has_permission(Permission.MANAGE_MEMBERS):
            member.member_type = data.get('member_type') or member.member_type
        
        if 'is_active' in data:
            if _has_permission(Permission.MANAGE_MEMBERS):
                member.is_active = bool(data['is_active'])
                # Keep a promoted member's operator login in sync (linked by
                # username == member_id) so deactivating also locks Admin access.
                op = User.query.filter_by(username=member.member_id).first()
                if op:
                    op.is_active = member.is_active

        # Password reset: admins (or the member themselves) may set a new one.
        new_password = (data.get('password') or '').strip()
        if new_password:
            member.set_password(new_password)
            # Mirror to the linked operator account if this is a promoted member.
            op = User.query.filter_by(username=member.member_id).first()
            if op:
                op.password_hash = member.password_hash

        db.session.commit()

        return ApiResponse.success(MemberSerializer.to_dict(member), message='Member updated successfully')
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Update member error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)



@bp.route('/members/<int:member_id>', methods=['DELETE'])
@login_required
def delete_member(member_id):
    """Delete a member with safety checks (mirrors the old Flask flow):
    blocked while loans are outstanding, requires the admin's password, and
    logs the deletion reason. Historical loan records are preserved.
    Deleting members is Administrator-only.
    """
    try:
        if not _has_permission(Permission.ADMIN):
            return ApiResponse.error('Only an Administrator can delete members', status_code=403)
        member = Member.query.get(member_id)
        if not member:
            return ApiResponse.error('Member not found', status_code=404)

        data = request.get_json(silent=True) or {}
        from app.models import Loan, LoanStatus

        active = Loan.query.filter(
            Loan.member_id == member.id,
            Loan.status.in_([LoanStatus.ACTIVE.value, LoanStatus.OVERDUE.value]),
        ).count()
        if active:
            return ApiResponse.error(f'Member has {active} active loan(s)', status_code=409)

        # Safety: confirm the admin's own password before a permanent delete.
        if not current_user.check_password(data.get('current_password', '')):
            return ApiResponse.error('Current password is incorrect. Deletion cancelled.', status_code=403)

        reason = (data.get('deletion_reason') or '').strip()[:200] or 'Admin deletion'
        total_loans = Loan.query.filter_by(member_id=member.id).count()
        current_app.logger.warning(
            f'[DELETION] Member {member.member_id} ({member.full_name}) deleted by '
            f'{current_user.username}; reason="{reason}"; loan history={total_loans}'
        )

        # Remove a linked operator account (promoted Prefect/Librarian) so it
        # doesn't linger in Administration. Detach it from loan audit columns
        # first to keep referential integrity.
        op = User.query.filter_by(username=member.member_id).first()
        if op and op.id != current_user.id:
            Loan.query.filter_by(checkout_by=op.id).update({'checkout_by': None})
            Loan.query.filter_by(return_by=op.id).update({'return_by': None})
            db.session.delete(op)

        db.session.delete(member)
        db.session.commit()
        return ApiResponse.success(message='Member deleted')
    except Exception as e:
        db.session.rollback()
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/members/bulk-delete', methods=['POST'])
@login_required
def bulk_delete_members():
    """Delete several members at once (e.g. clearing graduated students).
    Requires the admin's password and a reason; members with active loans are
    skipped and reported back so nothing is lost silently. Administrator-only.
    """
    try:
        if not _has_permission(Permission.ADMIN):
            return ApiResponse.error('Only an Administrator can delete members', status_code=403)
        data = request.get_json(silent=True) or {}
        ids = data.get('ids') or []
        if not isinstance(ids, list) or not ids:
            return ApiResponse.error('No members selected', status_code=400)
        if not current_user.check_password(data.get('current_password', '')):
            return ApiResponse.error('Current password is incorrect. Deletion cancelled.', status_code=403)
        reason = (data.get('deletion_reason') or '').strip()[:200] or 'Bulk deletion (graduated)'

        from app.models import Loan, LoanStatus
        deleted, skipped = [], []
        for member in Member.query.filter(Member.id.in_(ids)).all():
            active = Loan.query.filter(
                Loan.member_id == member.id,
                Loan.status.in_([LoanStatus.ACTIVE.value, LoanStatus.OVERDUE.value]),
            ).count()
            if active:
                skipped.append(member.member_id)
                continue
            current_app.logger.warning(
                f'[DELETION] Member {member.member_id} ({member.full_name}) bulk-deleted by '
                f'{current_user.username}; reason="{reason}"'
            )
            op = User.query.filter_by(username=member.member_id).first()
            if op and op.id != current_user.id:
                Loan.query.filter_by(checkout_by=op.id).update({'checkout_by': None})
                Loan.query.filter_by(return_by=op.id).update({'return_by': None})
                db.session.delete(op)
            db.session.delete(member)
            deleted.append(member.member_id)
        db.session.commit()
        msg = f'{len(deleted)} member(s) deleted'
        if skipped:
            msg += f'; {len(skipped)} skipped (active loans): {", ".join(skipped)}'
        return ApiResponse.success({'deleted': deleted, 'skipped': skipped}, message=msg)
    except Exception as e:
        db.session.rollback()
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/staff/<int:user_id>', methods=['DELETE'])
@login_required
def delete_staff(user_id):
    """Delete a staff account (cannot delete yourself). Requires the admin's
    password and logs the deletion reason; loan audit links are detached so
    historical loans are preserved.
    """
    try:
        if not _has_permission(Permission.MANAGE_USERS):
            return ApiResponse.error('Insufficient permissions', status_code=403)
        if user_id == current_user.id:
            return ApiResponse.error('Cannot delete your own staff account', status_code=409)
        user = User.query.get(user_id)
        if not user:
            return ApiResponse.error('Staff not found', status_code=404)

        data = request.get_json(silent=True) or {}
        if not current_user.check_password(data.get('current_password', '')):
            return ApiResponse.error('Current password is incorrect. Deletion cancelled.', status_code=403)

        reason = (data.get('deletion_reason') or '').strip()[:200] or 'Admin deletion'
        current_app.logger.warning(
            f'[DELETION] Staff {user.username} ({user.full_name}) deleted by '
            f'{current_user.username}; reason="{reason}"'
        )

        from app.models import Loan
        Loan.query.filter_by(checkout_by=user.id).update({'checkout_by': None})
        Loan.query.filter_by(return_by=user.id).update({'return_by': None})

        db.session.delete(user)
        db.session.commit()
        return ApiResponse.success(message='Staff account deleted')
    except Exception as e:
        db.session.rollback()
        return ApiResponse.error(str(e), status_code=500)


# A borrower is promoted onto the library team: a Student becomes a Library
# Prefect, a Staff/Teacher becomes a Librarian. Both get a linked operator
# account with the matching role so they can run the system.
_PROMOTE_MAP = {'Student': 'Library Prefect', 'Staff': 'Librarian'}
_DEMOTE_MAP = {'Library Prefect': 'Student', 'Librarian': 'Staff'}


@bp.route('/members/<int:member_id>/promote', methods=['POST'])
@login_required
def promote_member(member_id):
    """Promote a member onto the library team (Student->Library Prefect, Staff->Librarian)."""
    try:
        if not _has_permission(Permission.MANAGE_USERS):
            return ApiResponse.error('Insufficient permissions', status_code=403)
        from app.models import Role
        member = Member.query.get(member_id)
        if not member:
            return ApiResponse.error('Member not found', status_code=404)

        target_type = _PROMOTE_MAP.get(member.member_type)
        if not target_type:
            return ApiResponse.error(
                'Only Students (-> Library Prefect) and Staff (-> Librarian) can be promoted',
                status_code=400,
            )
        role = Role.query.filter_by(name=target_type).first()

        # Keep form_level/class_group (a Library Prefect is still a student in
        # their class, so they remain on the NILAM leaderboard).
        member.member_type = target_type

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
        return ApiResponse.success(MemberSerializer.to_dict(member), message=f'{member.full_name} promoted to {target_type}')
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
        name = to_caps((data.get('name') or '').strip())  # classes stored UPPERCASE
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


@bp.route('/class-groups/<path:name>', methods=['DELETE'])
@login_required
def delete_class_group(name):
    """Delete a managed class by name (admin only).

    Blocked if any member is still assigned to it, so deleting a class can
    never orphan students. Reassign or clear those members first.
    """
    try:
        if not _has_permission(Permission.MANAGE_MEMBERS):
            return ApiResponse.error('Permission denied', status_code=403)

        target = (name or '').strip()
        in_use = Member.query.filter(func.lower(Member.class_group) == target.lower()).count()
        if in_use:
            return ApiResponse.error(
                f'{in_use} member(s) are still in this class. Reassign them before deleting.',
                status_code=409,
            )

        cg = ClassGroup.query.filter(func.lower(ClassGroup.name) == target.lower()).first()
        if not cg:
            return ApiResponse.error('Class not found', status_code=404)
        db.session.delete(cg)
        db.session.commit()
        return ApiResponse.success(message=f'Class "{cg.name}" deleted')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Delete class group error: {str(e)}')
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
    """Demote off the team (Library Prefect->Student, Librarian->Staff)."""
    try:
        if not _has_permission(Permission.MANAGE_USERS):
            return ApiResponse.error('Insufficient permissions', status_code=403)
        member = Member.query.get(member_id)
        if not member:
            return ApiResponse.error('Member not found', status_code=404)

        target_type = _DEMOTE_MAP.get(member.member_type)
        if not target_type:
            return ApiResponse.error('This member is not on the library team', status_code=400)

        member.member_type = target_type
        if target_type == 'Student' and not member.form_level:
            member.form_level = 1
        # Disable the linked operator account; their borrower login still works
        user = User.query.get(member.id)
        if user:
            user.is_active = False
        db.session.commit()
        return ApiResponse.success(MemberSerializer.to_dict(member), message=f'{member.full_name} demoted to {target_type}')
    except Exception as e:
        db.session.rollback()
        return ApiResponse.error(str(e), status_code=500)
