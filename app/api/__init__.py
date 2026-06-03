"""
API Blueprints - JSON API endpoints for React frontend
Each module provides RESTful endpoints for specific features
"""

from flask import Blueprint

# API blueprint registry
api_blueprints = []


def register_api_blueprints(app):
    """
    Register all API blueprints with the Flask app
    This function is called from app/__init__.py
    """
    from app.api import auth_api, catalog_api, circulation_api, users_api, student_api
    
    blueprints = [
        auth_api.bp,
        catalog_api.bp,
        circulation_api.bp,
        users_api.bp,
        student_api.bp,
    ]
    
    for bp in blueprints:
        app.register_blueprint(bp)
        app.logger.info(f"✓ Registered API blueprint: {bp.name}")
