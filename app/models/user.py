"""
User, Role, and Permission models
Supports RBAC: Librarian, Library Prefect, Student
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login_manager


class Permission:
    """Permission flags (bitwise)"""
    VIEW_CATALOG = 1          # View books/copies
    SEARCH = 2                # Search catalog
    BORROW = 4                # Borrow books (member action)
    MANAGE_CATALOG = 8        # Add/edit/delete books
    MANAGE_COPIES = 16        # Add/edit/delete copies
    CHECKOUT = 32             # Process checkouts
    RETURN = 64               # Process returns
    MANAGE_MEMBERS = 128      # Add/edit members
    MANAGE_USERS = 256        # Add/edit staff users
    OCR_DIGITIZE = 512        # Use OCR digitization
    OCR_APPROVE = 1024        # Approve OCR results
    ADMIN = 2048              # Full admin access


class Role(db.Model):
    """User roles with permission sets"""
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(256))
    permissions = db.Column(db.Integer, default=0)
    is_default = db.Column(db.Boolean, default=False, index=True)
    
    users = db.relationship('User', backref='role', lazy='dynamic')
    
    def __repr__(self):
        return f'<Role {self.name}>'
    
    def has_permission(self, perm):
        """Check if role has a specific permission"""
        return self.permissions & perm == perm
    
    def add_permission(self, perm):
        """Add a permission to the role"""
        if not self.has_permission(perm):
            self.permissions += perm
    
    def remove_permission(self, perm):
        """Remove a permission from the role"""
        if self.has_permission(perm):
            self.permissions -= perm
    
    def reset_permissions(self):
        """Reset all permissions"""
        self.permissions = 0
    
    @staticmethod
    def insert_default_roles():
        """Create default roles if they don't exist"""
        roles = {
            'Student': [
                Permission.VIEW_CATALOG,
                Permission.SEARCH,
                Permission.BORROW
            ],
            'Library Prefect': [
                Permission.VIEW_CATALOG,
                Permission.SEARCH,
                Permission.MANAGE_CATALOG,
                Permission.MANAGE_COPIES,
                Permission.CHECKOUT,
                Permission.RETURN
            ],
            'Librarian': [
                Permission.VIEW_CATALOG,
                Permission.SEARCH,
                Permission.MANAGE_CATALOG,
                Permission.MANAGE_COPIES,
                Permission.CHECKOUT,
                Permission.RETURN,
                Permission.MANAGE_MEMBERS,
                Permission.MANAGE_USERS,
                Permission.OCR_DIGITIZE,
                Permission.OCR_APPROVE
            ],
            'Administrator': [
                Permission.VIEW_CATALOG,
                Permission.SEARCH,
                Permission.MANAGE_CATALOG,
                Permission.MANAGE_COPIES,
                Permission.CHECKOUT,
                Permission.RETURN,
                Permission.MANAGE_MEMBERS,
                Permission.MANAGE_USERS,
                Permission.OCR_DIGITIZE,
                Permission.OCR_APPROVE,
                Permission.ADMIN
            ]
        }
        default_role = 'Student'
        
        for role_name, perms in roles.items():
            role = Role.query.filter_by(name=role_name).first()
            if role is None:
                role = Role(name=role_name)
            role.reset_permissions()
            for perm in perms:
                role.add_permission(perm)
            role.is_default = (role_name == default_role)
            db.session.add(role)
        
        db.session.commit()


class User(UserMixin, db.Model):
    """System users (staff accounts)"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(128))
    is_active = db.Column(db.Boolean, default=True)
    
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        """Hash and set the password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def can(self, perm):
        """Check if user has a specific permission"""
        return self.role is not None and self.role.has_permission(perm)
    
    def is_administrator(self):
        """Check if user has admin permission"""
        return self.can(Permission.ADMIN)
    
    def get_id(self):
        """Return user ID for Flask-Login (prefixed with 'user_')"""
        return f'user_{self.id}'
    
    @staticmethod
    def create_admin(username, email, password):
        """Create an admin user"""
        admin_role = Role.query.filter_by(name='Administrator').first()
        if admin_role is None:
            Role.insert_default_roles()
            admin_role = Role.query.filter_by(name='Administrator').first()
        
        user = User(
            username=username,
            email=email,
            role=admin_role,
            full_name='System Administrator'
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user


@login_manager.user_loader
def load_user(user_id):
    """Flask-Login user loader callback - handles both User and Member"""
    from app.models import Member
    
    # user_id format: "user_123" for User or "member_456" for Member
    if user_id.startswith('user_'):
        user_id_num = int(user_id.split('_')[1])
        return User.query.get(user_id_num)
    elif user_id.startswith('member_'):
        user_id_num = int(user_id.split('_')[1])
        return Member.query.get(user_id_num)
    else:
        # Fallback for old-style numeric IDs (assume User)
        return User.query.get(int(user_id))
