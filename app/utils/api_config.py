"""
API Configuration - CORS, error handling, middleware.
Sets up Flask app behavior expected by the React SPA.
"""
import os
import time

from flask import Flask, jsonify, redirect, request, url_for
from flask_cors import CORS


def setup_cors(app: Flask):
    """Configure CORS for local Vite development and production deployments."""
    allowed_origins = [
        'http://localhost:3000',
        'http://localhost:5173',
        'http://127.0.0.1:3000',
        'http://127.0.0.1:5173',
    ]

    if not os.environ.get('DEBUG'):
        allowed_origins.extend([
            'https://epustaka-munshi.vercel.app',
            'https://epustaka-react.vercel.app',
            r'https://.*\.vercel\.app',
        ])

    CORS(
        app,
        origins=allowed_origins,
        supports_credentials=True,
        methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'],
        allow_headers=['Content-Type', 'Authorization', 'Accept-Language'],
        expose_headers=['Content-Length', 'X-Total-Count', 'X-Page-Count'],
        max_age=3600,
    )

    app.logger.info(f"CORS configured for origins: {allowed_origins}")


def setup_error_handlers(app: Flask):
    """Convert common errors to the JSON shape consumed by the frontend."""

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'success': False,
            'message': 'Bad request - invalid input',
            'data': None,
            'status_code': 400,
        }), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            'success': False,
            'message': 'Unauthorized - please log in',
            'data': None,
            'status_code': 401,
        }), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            'success': False,
            'message': 'Forbidden - insufficient permissions',
            'data': None,
            'status_code': 403,
        }), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'message': 'Resource not found',
            'data': None,
            'status_code': 404,
        }), 404

    @app.errorhandler(409)
    def conflict(error):
        return jsonify({
            'success': False,
            'message': 'Conflict - resource already exists',
            'data': None,
            'status_code': 409,
        }), 409

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Server error: {error}')
        return jsonify({
            'success': False,
            'message': 'Internal server error',
            'data': None,
            'status_code': 500,
        }), 500

    @app.errorhandler(Exception)
    def handle_generic_exception(error):
        app.logger.error(f'Unhandled exception: {error}', exc_info=True)

        if os.environ.get('DEBUG'):
            return jsonify({
                'success': False,
                'message': str(error),
                'data': None,
                'status_code': 500,
            }), 500

        return jsonify({
            'success': False,
            'message': 'Internal server error',
            'data': None,
            'status_code': 500,
        }), 500


def setup_auth_handlers(app: Flask):
    """Return JSON for API auth failures while preserving legacy page redirects."""
    from app import login_manager

    @login_manager.unauthorized_handler
    def unauthorized_callback():
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'message': 'Unauthorized - please log in',
                'data': None,
                'status_code': 401,
            }), 401

        return redirect(url_for('auth.login', next=request.url))


def setup_request_logging(app: Flask):
    """Log request method, path, response status, and duration."""

    @app.before_request
    def before_request():
        if request.path.startswith('/static'):
            return

        request.start_time = time.time()
        app.logger.info(f"-> {request.method} {request.path}")

    @app.after_request
    def after_request(response):
        if request.path.startswith('/static'):
            return response

        duration = getattr(request, 'start_time', None)
        duration_ms = int((time.time() - duration) * 1000) if duration else 0

        status_label = 'OK' if response.status_code < 300 else (
            'REDIRECT' if response.status_code < 400 else 'ERROR'
        )

        app.logger.info(
            f"{status_label} {response.status_code} {request.method} "
            f"{request.path} ({duration_ms}ms)"
        )

        return response


def setup_api_middleware(app: Flask):
    """Setup all API middleware during app initialization."""
    setup_cors(app)
    setup_error_handlers(app)
    setup_auth_handlers(app)
    setup_request_logging(app)

    app.logger.info("API middleware configured")
