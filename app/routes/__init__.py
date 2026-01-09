"""
ePustaka-Munshi Routes Package
"""
from app.routes.main import main_bp
from app.routes.auth import auth_bp
from app.routes.catalog import catalog_bp
from app.routes.circulation import circulation_bp
from app.routes.ocr import ocr_bp
from app.routes.users import users_bp

__all__ = [
    'main_bp',
    'auth_bp',
    'catalog_bp',
    'circulation_bp',
    'ocr_bp',
    'users_bp'
]
