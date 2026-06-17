"""Dev server pinned to the local SQLite database.

Forces DATABASE_URL before config.py loads .env, so tests can never
accidentally hit the production Supabase database.
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(BASE, 'instance', 'epustaka.db').replace('\\', '/')

from app import create_app  # noqa: E402  (env must be set before this import)

app = create_app()

if __name__ == '__main__':
    print(f"[run_local_sqlite] DB: {app.config['SQLALCHEMY_DATABASE_URI']}")
    app.run(debug=False, port=5000)
