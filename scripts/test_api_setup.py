#!/usr/bin/env python
"""Test script - Verify API setup works"""
import sys
import os

os.environ['FLASK_ENV'] = 'development'

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from app import create_app

try:
    print("📦 Initializing Flask app...")
    app = create_app('development')
    print("✅ Flask app created successfully!\n")
    
    print("📋 Registered Blueprints:")
    for name, bp in app.blueprints.items():
        print(f"  ✓ {name}")
    
    print(f"\n📊 Total blueprints: {len(app.blueprints)}")
    
    # Check for API blueprints specifically
    api_bps = [name for name in app.blueprints.keys() if name.startswith('api_')]
    print(f"🔌 API blueprints: {len(api_bps)}")
    for name in api_bps:
        print(f"  ✓ {name}")
    
    print("\n✨ All systems ready for React migration!")
    sys.exit(0)
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
