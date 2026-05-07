"""
ePustaka-Munshi Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'epustaka-munshi-dev-key-change-in-production'
    
    # SQLite database (local-first, easy deployment)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'sqlite:///{os.path.join(BASE_DIR, "instance", "epustaka.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
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
