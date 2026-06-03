#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""API Endpoint Testing Script - Test auth endpoints"""
import os
import sys
import json

os.environ['FLASK_ENV'] = 'development'

from app import create_app, db
from app.models import User, Role

def test_api_endpoints():
    """Test all API endpoints"""
    app = create_app('development')
    client = app.test_client()
    
    print("TESTING API ENDPOINTS")
    print("=" * 60)
    passed = 0
    failed = 0
    
    # Test 1: Login with invalid credentials
    print("\n[TEST 1] Login with invalid credentials")
    response = client.post('/api/auth/login', 
        json={'username': 'nonexistent', 'password': 'wrong'})
    data = response.get_json()
    if response.status_code == 401 and data['success'] == False:
        print("  PASS: Correctly rejected invalid credentials")
        passed += 1
    else:
        print(f"  FAIL: Expected 401, got {response.status_code}")
        failed += 1
    
    # Test 2: Login without credentials
    print("\n[TEST 2] Login without username/password")
    response = client.post('/api/auth/login',
        json={'username': '', 'password': ''})
    data = response.get_json()
    if response.status_code == 400:
        print("  PASS: Correctly rejected empty credentials")
        passed += 1
    else:
        print(f"  FAIL: Expected 400, got {response.status_code}")
        failed += 1
    
    # Test 3: Create test staff account and login
    print("\n[TEST 3] Login with valid staff account")
    with app.app_context():
        # Create role if not exists
        admin_role = Role.query.filter_by(name='Administrator').first()
        if not admin_role:
            print("  INFO: Creating default roles...")
            Role.insert_default_roles()
            admin_role = Role.query.filter_by(name='Administrator').first()
        
        # Create test user
        test_user = User.query.filter_by(username='test_admin').first()
        if not test_user:
            test_user = User(
                username='test_admin',
                email='admin@test.local',
                full_name='Test Admin',
                is_active=True,
                role_id=admin_role.id
            )
            test_user.set_password('password123')
            db.session.add(test_user)
            db.session.commit()
            print("  INFO: Created test staff account")
        
        # Test login
        response = client.post('/api/auth/login',
            json={'username': 'test_admin', 'password': 'password123'})
        data = response.get_json()
        
        if response.status_code == 200 and data['success']:
            print("  PASS: Staff login successful")
            passed += 1
        else:
            print(f"  FAIL: Login failed - {data['message']}")
            failed += 1
    
    # Test 4: Response format
    print("\n[TEST 4] Response format validation")
    response = client.post('/api/auth/login',
        json={'username': 'test', 'password': 'test'})
    data = response.get_json()
    has_all_fields = all(k in data for k in ['success', 'message', 'data'])
    if has_all_fields:
        print("  PASS: All required response fields present")
        passed += 1
    else:
        print("  FAIL: Missing required fields")
        failed += 1
    
    # Test 5: CORS headers
    print("\n[TEST 5] CORS headers")
    response = client.options('/api/auth/login')
    cors_header = response.headers.get('Access-Control-Allow-Origin')
    if cors_header:
        print(f"  PASS: CORS configured")
        passed += 1
    else:
        print("  FAIL: No CORS headers")
        failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    if failed == 0:
        print("SUCCESS: All API tests passed!")
        return True
    else:
        print(f"FAILURE: {failed} test(s) failed")
        return False

if __name__ == '__main__':
    try:
        success = test_api_endpoints()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
