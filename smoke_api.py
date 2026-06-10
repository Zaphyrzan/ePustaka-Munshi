# -*- coding: utf-8 -*-
"""Smoke test for the JSON API surface used by the React frontend."""
import os

os.environ['FLASK_ENV'] = 'development'

from app import create_app

app = create_app('development')
client = app.test_client()

results = []


def check(label, resp, expect_status, expect_json=True):
    ok = resp.status_code == expect_status
    body = None
    if expect_json:
        body = resp.get_json(silent=True)
        ok = ok and body is not None
    detail = ''
    if not ok:
        raw = resp.get_data(as_text=True)
        detail = f' got {resp.status_code}, body={raw[:200]}'
    results.append((label, ok, detail))
    return body


# --- Unauthenticated: must be JSON 401, not 302 redirect ---
check('GET /api/auth/me unauthenticated -> 401 JSON', client.get('/api/auth/me'), 401)
check('GET /api/circulation/loans unauthenticated -> 401 JSON', client.get('/api/circulation/loans'), 401)
check('GET /api/users/staff unauthenticated -> 401 JSON', client.get('/api/users/staff'), 401)

# --- Login as test admin (created by test_api_endpoints.py) ---
resp = client.post('/api/auth/login', json={'username': 'test_admin', 'password': 'password123'})
check('POST /api/auth/login -> 200', resp, 200)

# --- Authenticated reads (previously 500) ---
check('GET /api/auth/me -> 200', client.get('/api/auth/me'), 200)
check('GET /api/users/staff -> 200', client.get('/api/users/staff'), 200)
check('GET /api/users/members -> 200', client.get('/api/users/members'), 200)
check('GET /api/circulation/loans -> 200', client.get('/api/circulation/loans'), 200)
check('GET /api/catalog/books -> 200', client.get('/api/catalog/books'), 200)
check('GET /api/catalog/books?search=a -> 200', client.get('/api/catalog/books?search=a'), 200)

books = check('GET /api/catalog/books page 1 -> 200', client.get('/api/catalog/books?per_page=5'), 200)
book_id = None
if books and books.get('data', {}).get('items'):
    book_id = books['data']['items'][0]['id']
    check(f'GET /api/catalog/books/{book_id} -> 200', client.get(f'/api/catalog/books/{book_id}'), 200)

# --- Student API as staff (dashboard/search/leaderboard work, loans 404 without member record) ---
check('GET /api/student/dashboard (staff) -> 200', client.get('/api/student/dashboard'), 200)
check('GET /api/student/search -> 200', client.get('/api/student/search?per_page=12'), 200)
check('GET /api/student/leaderboard -> 200', client.get('/api/student/leaderboard'), 200)
check('GET /api/student/leaderboard?form=1 -> 200', client.get('/api/student/leaderboard?form=1'), 200)
if book_id:
    check(f'GET /api/student/books/{book_id} -> 200', client.get(f'/api/student/books/{book_id}'), 200)

# --- Student API as member ---
with app.app_context():
    from app import db
    from app.models import Member

    test_member = Member.query.filter_by(member_id='STU9999').first()
    if not test_member:
        test_member = Member(
            member_id='STU9999',
            full_name='Smoke Test Student',
            email='smoke@test.local',
            member_type='Student',
            form_level=1,
            is_active=True,
        )
        db.session.add(test_member)
    test_member.set_password('password123')
    db.session.commit()

client.post('/api/auth/logout')
resp = client.post('/api/auth/login', json={'username': 'STU9999', 'password': 'password123'})
check('POST /api/auth/login (member) -> 200', resp, 200)
check('GET /api/student/dashboard (member) -> 200', client.get('/api/student/dashboard'), 200)
check('GET /api/student/loans (member) -> 200', client.get('/api/student/loans'), 200)
check('GET /api/student/search (member) -> 200', client.get('/api/student/search'), 200)
check('GET /api/users/staff as member -> 403', client.get('/api/users/staff'), 403)

print('=' * 70)
passed = sum(1 for _, ok, _ in results if ok)
for label, ok, detail in results:
    print(('PASS' if ok else 'FAIL') + '  ' + label + detail)
print('=' * 70)
print(f'{passed}/{len(results)} passed')
