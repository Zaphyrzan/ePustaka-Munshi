"""
Auth API Routes - JSON endpoints for authentication
Handles login, logout, registration, profile management
"""

from flask import Blueprint, request, jsonify, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from app import db
from app.models import User, Member
from app.utils.serializers import UserSerializer, MemberSerializer, ApiResponse

# Create blueprint
bp = Blueprint('api_auth', __name__, url_prefix='/api/auth')


@bp.route('/login', methods=['POST'])
def login():
    """
    Login endpoint - accepts username and password
    Returns user data and sets session cookie
    
    Request JSON:
    {
        "username": "staff_username or STU0001",
        "password": "password",
        "remember_me": true  (optional)
    }
    
    Response:
    {
        "success": true,
        "message": "Login successful",
        "data": {
            "user": {...},
            "role": "Administrator|Librarian|Student Assistant|Student"
        }
    }
    """
    try:
        # Get JSON data, handle missing content type
        try:
            data = request.get_json()
        except Exception as e:
            return ApiResponse.error('Request must be JSON (Content-Type: application/json)', status_code=400)
        
        if not data:
            return ApiResponse.error('Request body must be JSON', status_code=400)
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        remember_me = data.get('remember_me', False)
        
        if not username or not password:
            return ApiResponse.error('Username and password required', status_code=400)
        
        # Try Staff (User) login first
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            # Staff user found with correct password
            if user.is_active:
                # Check if linked member is also disabled
                linked_member = Member.query.filter_by(member_id=user.username).first()
                if linked_member and not linked_member.is_active:
                    return ApiResponse.error('Your account is disabled', status_code=403)
                
                # Active staff account - login as staff
                login_user(user, remember=remember_me)
                user.last_login = datetime.utcnow()
                db.session.commit()
                
                user_data = UserSerializer.to_dict(user)
                role_name = user.role.name if user.role else 'Unknown'
                
                return ApiResponse.success({
                    'user': user_data,
                    'role': role_name,
                    'user_type': 'staff'
                }, message='Staff login successful')
            else:
                # Staff account is disabled, try Member login instead
                member = Member.query.filter_by(member_id=username).first()
                
                if member and member.check_password(password):
                    # Member/student found with correct password
                    if member.is_active:
                        # Active member account - login as student
                        login_user(member, remember=remember_me)
                        member.last_login = datetime.utcnow()
                        db.session.commit()
                        
                        member_data = MemberSerializer.to_dict(member)
                        
                        return ApiResponse.success({
                            'user': member_data,
                            'role': 'Student',
                            'user_type': 'student'
                        }, message='Student login successful')
                    else:
                        # Member account is also disabled
                        return ApiResponse.error('Your account is disabled', status_code=403)
                else:
                    # Password incorrect for member
                    return ApiResponse.error('Invalid username or password', status_code=401)
        
        # Try direct Member login
        member = Member.query.filter_by(member_id=username).first()
        
        if member and member.check_password(password):
            # Member/student found with correct password
            if member.is_active:
                # Active member account - login as student
                login_user(member, remember=remember_me)
                member.last_login = datetime.utcnow()
                db.session.commit()
                
                member_data = MemberSerializer.to_dict(member)
                
                return ApiResponse.success({
                    'user': member_data,
                    'role': 'Student',
                    'user_type': 'student'
                }, message='Student login successful')
            else:
                # Member account is disabled
                return ApiResponse.error('Your account is disabled', status_code=403)
        
        # User not found or password incorrect
        return ApiResponse.error('Invalid username or password', status_code=401)
    
    except Exception as e:
        current_app.logger.error(f'Login error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """
    Logout endpoint - clears session
    
    Response:
    {
        "success": true,
        "message": "Logout successful"
    }
    """
    try:
        logout_user()
        return ApiResponse.success(message='Logout successful')
    except Exception as e:
        current_app.logger.error(f'Logout error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    """
    Get current logged-in user data
    
    Response:
    {
        "success": true,
        "data": {
            "user": {...},
            "role": "Administrator|Librarian|Student|Student Assistant",
            "user_type": "staff|student"
        }
    }
    """
    try:
        if isinstance(current_user, User):
            # Staff user
            user_data = UserSerializer.to_dict(current_user)
            role_name = current_user.role.name if current_user.role else 'Unknown'
            
            return ApiResponse.success({
                'user': user_data,
                'role': role_name,
                'user_type': 'staff'
            })
        else:
            # Member/student
            member_data = MemberSerializer.to_dict(current_user)
            
            return ApiResponse.success({
                'user': member_data,
                'role': 'Student',
                'user_type': 'student'
            })
    except Exception as e:
        current_app.logger.error(f'Get current user error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/me', methods=['PUT'])
@login_required
def update_me():
    """Let the logged-in user update their own contact info.

    Email (all users) and phone (members only) are editable; name and
    login id / member id are NOT self-editable.
    """
    try:
        data = request.get_json(silent=True) or {}

        if 'email' in data:
            email = (data.get('email') or '').strip() or None
            if email:
                # Reject if another account of the same kind already uses it
                if isinstance(current_user, User):
                    clash = User.query.filter(User.email == email, User.id != current_user.id).first()
                else:
                    clash = Member.query.filter(Member.email == email, Member.id != current_user.id).first()
                if clash:
                    return ApiResponse.error('That email is already in use', status_code=409)
            current_user.email = email

        # Phone only exists on Member accounts
        if 'phone' in data and not isinstance(current_user, User):
            current_user.phone = (data.get('phone') or '').strip() or None

        db.session.commit()

        if isinstance(current_user, User):
            return ApiResponse.success(UserSerializer.to_dict(current_user), message='Profile updated')
        return ApiResponse.success(MemberSerializer.to_dict(current_user), message='Profile updated')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Update profile error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)


@bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """
    Change current user's password

    Request JSON:
    {
        "current_password": "old_password",
        "new_password": "new_password",
        "confirm_password": "new_password"
    }
    
    Response:
    {
        "success": true,
        "message": "Password changed successfully"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return ApiResponse.error('Request body must be JSON', status_code=400)
        
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')
        confirm_password = data.get('confirm_password', '')
        
        # Validate inputs
        if not current_password or not new_password or not confirm_password:
            return ApiResponse.error('All fields are required', status_code=400)
        
        if new_password != confirm_password:
            return ApiResponse.error('New passwords do not match', status_code=400)
        
        if len(new_password) < 6:
            return ApiResponse.error('Password must be at least 6 characters', status_code=400)
        
        # Verify current password
        if not current_user.check_password(current_password):
            return ApiResponse.error('Current password is incorrect', status_code=401)
        
        # Set new password
        current_user.set_password(new_password)
        db.session.commit()
        
        return ApiResponse.success(message='Password changed successfully')
    
    except Exception as e:
        current_app.logger.error(f'Change password error: {str(e)}')
        return ApiResponse.error(str(e), status_code=500)
