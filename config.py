"""
ePustaka-Munshi Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _runtime_folder(*parts):
    """Return a writable folder path for local or serverless runtimes."""
    if os.environ.get('VERCEL'):
        return os.path.join('/tmp', 'epustaka-munshi', *parts)
    return os.path.join(BASE_DIR, *parts)


def _build_database_uri():
    """Resolve database URI from env with Supabase support.
    Optimized for Vercel serverless with proper connection pooling and SSL."""
    # Vercel should prefer a pooler URL when Supabase provides one.
    pooler_url = os.environ.get('SUPABASE_POOLER_URL')
    is_vercel = os.environ.get('VERCEL')
    database_url = pooler_url if is_vercel and pooler_url else os.environ.get('DATABASE_URL')
    
    # Debug logging for Vercel connection string selection
    if is_vercel:
        print(f"[CONFIG] VERCEL={is_vercel}, SUPABASE_POOLER_URL={'*' * 10 if pooler_url else 'NOT SET'}", flush=True)
        print(f"[CONFIG] Using {'POOLER' if pooler_url and (is_vercel and pooler_url) else 'DATABASE'}_URL", flush=True)

    if database_url:
        # SQLAlchemy 1.4+/2.x expects postgresql:// instead of postgres://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        # For Vercel serverless, add connection timeout if not already present
        # (sslmode=require is already in DATABASE_URL from Supabase)
        if os.environ.get('VERCEL') and 'supabase.co' in database_url:
            if 'connect_timeout' not in database_url:
                separator = '&' if '?' in database_url else '?'
                database_url += f"{separator}connect_timeout=10"
        
        return database_url

    # Optional Supabase fallback if DATABASE_URL is not set
    # Requires project id + DB password (and optional user/name/port overrides)
    project_id = os.environ.get('SUPABASE_PROJECT_ID')
    db_password = os.environ.get('SUPABASE_DB_PASSWORD')
    if project_id and db_password:
        db_user = os.environ.get('SUPABASE_DB_USER', 'postgres')
        db_name = os.environ.get('SUPABASE_DB_NAME', 'postgres')
        db_port = os.environ.get('SUPABASE_DB_PORT', '5432')
        return (
            f"postgresql+psycopg2://{db_user}:{db_password}"
            f"@db.{project_id}.supabase.co:{db_port}/{db_name}?sslmode=require"
        )

    return f'sqlite:///{os.path.join(BASE_DIR, "instance", "epustaka.db")}'


class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'epustaka-munshi-dev-key-change-in-production'

    # Database priority: DATABASE_URL -> Supabase env -> local SQLite
    SQLALCHEMY_DATABASE_URI = _build_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # SQLAlchemy engine options optimized for Vercel serverless
    # Vercel functions are stateless, so use connection pooling cautiously
    if os.environ.get('VERCEL'):
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,
            'pool_size': 1,  # Minimal pool for serverless (each instance is isolated)
            'max_overflow': 0,  # Disable overflow - fail fast if pool exhausted
            'pool_recycle': 3600,  # Recycle connections every hour
            'echo': False,  # Don't log SQL in production (use logs to debug)
            'connect_args': {
                'connect_timeout': 10,  # 10 second connection timeout
                'keepalives': 1,
                'keepalives_idle': 5,
            }
        }
    else:
        # Development/local configuration
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,
        }
    
    # OCR settings
    TESSERACT_CMD = os.environ.get('TESSERACT_CMD') or r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    OCR_UPLOAD_FOLDER = _runtime_folder('uploads', 'ocr')
    OCR_OUTPUT_FOLDER = _runtime_folder('uploads', 'ocr_results')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'tiff', 'pdf'}
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max upload
    
    # Scanner settings (future expansion)
    SCANNER_WATCH_FOLDER = _runtime_folder('uploads', 'scanner_spool')
    SCANNER_DEFAULT_DPI = 300
    SCANNER_DEFAULT_FORMAT = 'PNG'
    
    # Circulation defaults
    DEFAULT_LOAN_DAYS = 7  # 1 week loan period
    RENEWAL_LOAN_DAYS = 7  # 1 week renewal period
    MAX_RENEWALS = 2
    MAX_LOANS_PER_MEMBER = 5


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
