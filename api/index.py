"""
Vercel API entry point for the ePustaka-Munshi Flask app.
Vercel looks for WSGI apps in the /api directory.
"""
import sys
import os

# Add parent directory to path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wsgi import app

# Vercel requires the app to be exposed as 'app'
__all__ = ['app']
