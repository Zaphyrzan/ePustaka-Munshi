"""
ePustaka-Munshi - Library Management System
Application Factory
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy import text
import os

from config import config

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'


def _sync_postgres_sequences(app):
    """Ensure PostgreSQL sequences are aligned with migrated data."""
    engine = db.engine
    if engine.dialect.name != 'postgresql':
        return

    # Tables that rely on integer PK sequences.
    tables = [
        'roles',
        'users',
        'members',
        'books',
        'book_copies',
        'loans',
        'ocr_jobs',
        'ocr_results',
        'digitized_ledger',
    ]

    for table in tables:
        sequence_name = db.session.execute(
            text("SELECT pg_get_serial_sequence(:table_name, 'id')"),
            {'table_name': f'public.{table}'}
        ).scalar()

        if not sequence_name:
            continue

        max_id = db.session.execute(
            text(f"SELECT COALESCE(MAX(id), 0) FROM public.{table}")
        ).scalar() or 0

        if max_id > 0:
            db.session.execute(
                text("SELECT setval(:sequence_name, :seq_value, true)"),
                {'sequence_name': sequence_name, 'seq_value': int(max_id)}
            )
        else:
            db.session.execute(
                text("SELECT setval(:sequence_name, 1, false)"),
                {'sequence_name': sequence_name}
            )

    db.session.commit()


def _sync_staff_accounts(app):
    """Create missing staff User rows for promoted members."""
    from app.models.member import Member
    from app.models.user import Role, User

    staff_role = Role.query.filter_by(name='Library Prefect').first()
    staff_members = Member.query.filter(Member.member_type != 'Student').all()

    for member in staff_members:
        user = User.query.get(member.id)
        if user:
            continue

        username = member.member_id
        if User.query.filter(User.username == username).first():
            username = f'staff_{member.id}'

        email = member.email
        if email and User.query.filter(User.email == email).first():
            email = f'{member.member_id.lower()}@local.invalid'
        elif not email:
            email = f'{member.member_id.lower()}@local.invalid'

        user = User(
            id=member.id,
            username=username,
            email=email,
            full_name=member.full_name,
            is_active=True,
            role=staff_role,
            password_hash=member.password_hash,
        )
        db.session.add(user)

    if staff_members:
        db.session.commit()


def create_app(config_name=None):
    """Application factory pattern"""
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')
    
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])
    
    # Ensure instance and upload folders exist. Only needed for local
    # SQLite/OCR; on Vercel the filesystem is read-only and the DB is
    # Supabase, so a failure here must not block startup.
    for folder in (
        app.instance_path,
        app.config.get('OCR_UPLOAD_FOLDER', 'uploads/ocr'),
        app.config.get('OCR_OUTPUT_FOLDER', 'uploads/ocr_results'),
        app.config.get('SCANNER_WATCH_FOLDER', 'uploads/scanner_spool'),
    ):
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError:
            app.logger.warning(f'Could not create folder {folder} (read-only filesystem?)')
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    
    # Register i18n (internationalization) for language switching
    from app.utils.i18n import register_i18n
    register_i18n(app)
    
    # Setup API middleware (CORS, error handling, logging)
    # This must be done before registering blueprints
    from app.utils.api_config import setup_api_middleware
    setup_api_middleware(app)
    
    # Register API blueprints (JSON endpoints for React frontend)
    from app.api import register_api_blueprints
    register_api_blueprints(app)
    
    # Register traditional Flask blueprints (HTML templates - legacy)
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
    
    # Create database tables and setup monitoring
    with app.app_context():
        db.create_all()
        
        # Setup database connection pool monitoring and health checks
        # (must be done inside app context so db.engine is available)
        from app.utils.db_pool_utils import (
            setup_connection_pool_listeners,
            ConnectionPoolMonitor,
            set_pool_monitor
        )
        monitor = ConnectionPoolMonitor(db.engine)
        setup_connection_pool_listeners(db.engine, monitor)
        set_pool_monitor(monitor)
        
        # Log pool configuration for debugging
        if os.environ.get('VERCEL'):
            app.logger.info(
                f"Database pool configured for Vercel: "
                f"pool_size={app.config['SQLALCHEMY_ENGINE_OPTIONS'].get('pool_size')}, "
                f"max_overflow={app.config['SQLALCHEMY_ENGINE_OPTIONS'].get('max_overflow')}"
            )
        
        # Seed default roles if not exist
        from app.models.user import Role
        Role.insert_default_roles()

        # Seed default class groups (SMK Munshi streams) if none exist
        from app.models.member import ClassGroup
        ClassGroup.seed_defaults()
        _sync_staff_accounts(app)
        _sync_postgres_sequences(app)
    
    return app
