"""
ePustaka-Munshi - Library Management System
Application Factory
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

from config import config, _runtime_folder

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'


def create_app(config_name=None):
    """Application factory pattern"""
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')
    
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])
    
    # Ensure instance and upload folders exist
    # Use _runtime_folder to handle Vercel read-only filesystem with /tmp fallback
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(_runtime_folder('uploads', 'ocr'), exist_ok=True)
    os.makedirs(_runtime_folder('uploads', 'ocr_results'), exist_ok=True)
    os.makedirs(_runtime_folder('uploads', 'scanner_spool'), exist_ok=True)
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    
    # Register i18n (internationalization) for language switching
    from app.utils.i18n import register_i18n
    register_i18n(app)
    
    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.catalog import catalog_bp
    from app.routes.circulation import circulation_bp
    from app.routes.ocr import ocr_bp
    from app.routes.users import users_bp
    from app.routes.student import student_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(catalog_bp, url_prefix='/catalog')
    app.register_blueprint(circulation_bp, url_prefix='/circulation')
    app.register_blueprint(ocr_bp, url_prefix='/ocr')
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(student_bp, url_prefix='/student')
    
    # Create database tables
    with app.app_context():
        db.create_all()
        # Seed default roles if not exist
        from app.models.user import Role
        Role.insert_default_roles()
    
    return app
