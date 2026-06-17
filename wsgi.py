"""WSGI entrypoint for production deployments."""
from app import create_app

app = create_app()
