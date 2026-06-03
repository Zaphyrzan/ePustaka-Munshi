"""
API Configuration - CORS, error handling, middleware
Sets up Flask app for React SPA integration
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
import os
import time


def setup_cors(app: Flask):
    """
    Configure CORS for React frontend
    
    Allows requests from localhost (dev) and production URLs (Vercel, etc.)
    """
    # Determine allowed origins based on environment
    allowed_origins = [
        'http://localhost:3000',      # Local dev
        'http://localhost:5173',      # Vite dev server
        'http://127.0.0.1:3000',
        'http://127.0.0.1:5173',
    ]
    
    # Add production origins
    if not os.environ.get('DEBUG'):
        allowed_origins.extend([
            'https://epustaka-munshi.vercel.app',
            'https://epustaka-react.vercel.app',
            'https://*.vercel.app',  # Any Vercel deployment
        ])
    
    CORS(app, 
         origins=allowed_origins,
         supports_credentials=True,  # Allow cookies for authentication
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'],
         allow_headers=['Content-Type', 'Authorization', 'Accept-Language'],
         expose_headers=['Content-Length', 'X-Total-Count', 'X-Page-Count'],
         max_age=3600)
    
    app.logger.info(f"CORS configured for origins: {allowed_origins}")


def setup_error_handlers(app: Flask):
    """
    Setup error handlers for API responses
    Converts exceptions to JSON format
    """
    
    @app.errorhandler(400)
    def bad_request(error):
        """Bad request - invalid input"""
        return jsonify({
            'success': False,
            'message': 'Bad request - invalid input',
            'data': None,
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        """Unauthorized - not authenticated"""
        return jsonify({
            'success': False,
            'message': 'Unauthorized - please log in',
            'data': None,
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        """Forbidden - insufficient permissions"""
        return jsonify({
            'success': False,
            'message': 'Forbidden - insufficient permissions',
            'data': None,
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        """Resource not found"""
        return jsonify({
            'success': False,
            'message': 'Resource not found',
            'data': None,
        }), 404
    
    @app.errorhandler(409)
    def conflict(error):
        """Resource conflict - e.g., duplicate entry"""
        return jsonify({
            'success': False,
            'message': 'Conflict - resource already exists',
            'data': None,
        }), 409
    
    @app.errorhandler(500)
    def internal_error(error):
        """Internal server error"""
        app.logger.error(f'Server error: {error}')
        return jsonify({
            'success': False,
            'message': 'Internal server error',
            'data': None,
        }), 500
    
    @app.errorhandler(Exception)
    def handle_generic_exception(error):
        """Catch-all for any unhandled exceptions"""
        app.logger.error(f'Unhandled exception: {error}', exc_info=True)
        
        # Return different response based on environment
        if os.environ.get('DEBUG'):
            # In development, show the actual error
            return jsonify({
                'success': False,
                'message': str(error),
                'data': None,
            }), 500
        else:
            # In production, hide the actual error
            return jsonify({
                'success': False,
                'message': 'Internal server error',
                'data': None,
            }), 500


def setup_request_logging(app: Flask):
    """
    Setup request/response logging for debugging
    Logs all API requests with method, path, status code, and duration
    """
    
    @app.before_request
    def before_request():
        """Log incoming request"""
        # Skip logging for static files
        if request.path.startswith('/static'):
            return
        
        request.start_time = request.environ.get('werkzeug.request.start_time')
        app.logger.info(f"→ {request.method} {request.path}")
    
    @app.after_request
    def after_request(response):
        """Log outgoing response"""
        # Skip logging for static files
        if request.path.startswith('/static'):
            return response
        
        # Calculate request duration
        if hasattr(request, 'start_time'):
            duration = request.environ.get('werkzeug.request.start_time')
            duration_ms = int((time.time() - duration) * 1000) if duration else 0
        else:
            duration_ms = 0
        
        # Log response with status code
        status_color = '🟢' if response.status_code < 300 else \
                       '🟡' if response.status_code < 400 else \
                       '🔴'
        
        app.logger.info(
            f"{status_color} {response.status_code} {request.method} {request.path} "
            f"({duration_ms}ms)"
        )
        
        return response


def setup_api_middleware(app: Flask):
    """
    Setup all API middleware
    Called during app initialization
    """
    
    # Setup CORS
    setup_cors(app)
    
    # Setup error handlers
    setup_error_handlers(app)
    
    # Setup request logging
    setup_request_logging(app)
    
    app.logger.info("✓ API middleware configured")
