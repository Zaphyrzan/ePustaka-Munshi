"""
Vercel API entry point for the ePustaka-Munshi Flask app.
Vercel looks for WSGI apps in the /api directory.
"""
from app import create_app

# Create the Flask app
app = create_app()

# Vercel requires the app to be exposed as 'app'
__all__ = ['app']
