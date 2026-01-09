"""
Authentication routes - Login, Logout
"""
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        
        user = User.query.filter_by(username=username).first()
        
        if user is None or not user.check_password(password):
            flash('Invalid username or password', 'error')
            return render_template('auth/login.html')
        
        if not user.is_active:
            flash('Your account is disabled', 'error')
            return render_template('auth/login.html')
        
        login_user(user, remember=remember)
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('main.dashboard'))
    
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
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        new_username = request.form.get('username', '').strip()
        
        # Validate username uniqueness (if changed)
        if new_username != current_user.username:
            existing = User.query.filter_by(username=new_username).first()
            if existing:
                flash('Username already taken', 'error')
                return render_template('auth/edit_profile.html', user=current_user)
            if len(new_username) < 3:
                flash('Username must be at least 3 characters', 'error')
                return render_template('auth/edit_profile.html', user=current_user)
            current_user.username = new_username
        
        # Validate email uniqueness (if changed and not empty)
        if email and email != current_user.email:
            existing = User.query.filter_by(email=email).first()
            if existing:
                flash('Email already in use', 'error')
                return render_template('auth/edit_profile.html', user=current_user)
        
        current_user.full_name = full_name
        current_user.email = email
        db.session.commit()
        
        flash('Profile updated successfully', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/edit_profile.html', user=current_user)


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
