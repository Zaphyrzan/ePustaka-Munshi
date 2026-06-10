# -*- coding: utf-8 -*-
"""Count SQL queries per API endpoint to verify N+1 fixes."""
import os

os.environ['FLASK_ENV'] = 'development'

from sqlalchemy import event
from app import create_app, db

app = create_app('development')
client = app.test_client()

counter = {'n': 0}


def _count(conn, cursor, statement, parameters, context, executemany):
    counter['n'] += 1


with app.app_context():
    event.listen(db.engine, 'before_cursor_execute', _count)

client.post('/api/auth/login', json={'username': 'test_admin', 'password': 'password123'})

for path in [
    '/api/users/members?per_page=30',
    '/api/circulation/loans?per_page=15',
    '/api/catalog/books?per_page=30',
    '/api/users/staff?per_page=20',
]:
    counter['n'] = 0
    resp = client.get(path)
    print(f'{resp.status_code}  {counter["n"]:4d} queries  {path}')
