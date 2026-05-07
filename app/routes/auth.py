"""
Authentication routes - Login, Logout
"""
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, Member

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login - accepts both User (staff) and Member (students)"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        
        # Try User login first (staff accounts)
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            # Staff user found with correct password
            if user.is_active:
                # Active staff account - login as staff
                login_user(user, remember=remember)
                user.last_login = datetime.utcnow()
                db.session.commit()
                
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                return redirect(url_for('main.dashboard'))
            else:
                # Staff account is disabled, try Member login instead
                member = Member.query.filter_by(member_id=username).first()
                
                if member and member.check_password(password):
                    # Member/student found with correct password
                    if member.is_active:
                        # Active member account - login as student
                        login_user(member, remember=remember)
                        member.last_login = datetime.utcnow()
                        db.session.commit()
                        
                        next_page = request.args.get('next')
                        if next_page:
                            return redirect(next_page)
                        return redirect(url_for('main.dashboard'))
                    else:
                        # Member account is also disabled
                        flash('Your account is disabled', 'error')
                        return render_template('auth/login.html')
                else:
                    # No valid Member account
                    flash('Your staff account is disabled. Contact administrator.', 'error')
                    return render_template('auth/login.html')
        
        # Try Member login (students with member_id)
        member = Member.query.filter_by(member_id=username).first()
        
        if member and member.check_password(password):
            # Member/student found with correct password
            if member.is_active:
                # Active member account - login as student
                login_user(member, remember=remember)
                member.last_login = datetime.utcnow()
                db.session.commit()
                
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                return redirect(url_for('main.dashboard'))
            else:
                # Member account is disabled
                flash('Your account is disabled', 'error')
                return render_template('auth/login.html')
        else:
            # No valid account found, or password incorrect
            flash('Invalid username or password', 'error')
            return render_template('auth/login.html')
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('auth/profile.html', user=current_user)


@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile - name, email, username"""
    is_staff_account = hasattr(current_user, 'username')
    current_username = getattr(current_user, 'username', '')
    current_email = getattr(current_user, 'email', '')

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        new_username = request.form.get('username', '').strip()

        if is_staff_account:
            # Validate username uniqueness (if changed)
            if new_username != current_username:
                existing = User.query.filter_by(username=new_username).first()
                if existing:
                    flash('Username already taken', 'error')
                    return render_template('auth/edit_profile.html', user=current_user, can_edit_username=is_staff_account)
                if len(new_username) < 3:
                    flash('Username must be at least 3 characters', 'error')
                    return render_template('auth/edit_profile.html', user=current_user, can_edit_username=is_staff_account)
                current_user.username = new_username
        elif new_username:
            flash('Username changes are not available for student accounts', 'error')
            return render_template('auth/edit_profile.html', user=current_user, can_edit_username=is_staff_account)

        # Validate email uniqueness (if changed and not empty)
        if email and email != current_email:
            if is_staff_account:
                existing = User.query.filter_by(email=email).first()
            else:
                existing = Member.query.filter_by(email=email).first()
            if existing and existing.id != current_user.id:
                flash('Email already in use', 'error')
                return render_template('auth/edit_profile.html', user=current_user, can_edit_username=is_staff_account)
        
        current_user.full_name = full_name
        current_user.email = email
        db.session.commit()
        
        flash('Profile updated successfully', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/edit_profile.html', user=current_user, can_edit_username=is_staff_account)


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change password"""
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not current_user.check_password(current_password):
            flash('Current password is incorrect', 'error')
            return render_template('auth/change_password.html')
        
        if new_password != confirm_password:
            flash('New passwords do not match', 'error')
            return render_template('auth/change_password.html')
        
        if len(new_password) < 6:
            flash('Password must be at least 6 characters', 'error')
            return render_template('auth/change_password.html')
        
        current_user.set_password(new_password)
        db.session.commit()
        flash('Password changed successfully', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/change_password.html')
