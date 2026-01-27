#!/usr/bin/env python3
"""
Debug script to check what DATABASE_URL is being used.
Run on PythonAnywhere: python debug_database_url.py
"""

import os
import sys

print("=" * 60)
print("DATABASE_URL Debug")
print("=" * 60)

# Check current environment
print("\n1. Current DATABASE_URL in environment:")
db_url = os.environ.get('DATABASE_URL', 'NOT SET')
print(f"   {db_url[:50]}..." if len(db_url) > 50 else f"   {db_url}")

# Check for .env file
print("\n2. Checking for .env file:")
env_paths = [
    '/home/nicway2/mysite3/.env',
    '/home/nicway2/.env',
    '.env'
]

for path in env_paths:
    if os.path.exists(path):
        print(f"   FOUND: {path}")
        with open(path, 'r') as f:
            for line in f:
                if 'DATABASE' in line.upper() or 'SQLITE' in line.lower():
                    print(f"      {line.strip()}")
    else:
        print(f"   Not found: {path}")

# Check what load_dotenv would do
print("\n3. Testing load_dotenv behavior:")
try:
    from dotenv import load_dotenv

    # Show what DATABASE_URL is before load_dotenv
    print(f"   Before load_dotenv: {os.environ.get('DATABASE_URL', 'NOT SET')[:60]}")

    # Load .env
    load_dotenv()

    # Show what DATABASE_URL is after load_dotenv
    print(f"   After load_dotenv:  {os.environ.get('DATABASE_URL', 'NOT SET')[:60]}")
except ImportError:
    print("   python-dotenv not installed")

# Check database.py would use
print("\n4. What database.py would use:")
try:
    # Reset to simulate fresh import
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory.db')
        db_url = f'sqlite:///{db_path}'

    if db_url.startswith('sqlite'):
        print(f"   Would use SQLite: {db_url}")
    elif db_url.startswith('mysql'):
        print(f"   Would use MySQL: {db_url[:60]}...")
    else:
        print(f"   Would use: {db_url[:60]}...")
except Exception as e:
    print(f"   Error: {e}")

# Check if inventory.db exists
print("\n5. Checking for inventory.db file:")
sqlite_paths = [
    '/home/nicway2/mysite3/inventory.db',
    '/home/nicway2/inventory/inventory.db',
    'inventory.db'
]

for path in sqlite_paths:
    if os.path.exists(path):
        size = os.path.getsize(path) / 1024 / 1024
        print(f"   FOUND: {path} ({size:.2f} MB)")
    else:
        print(f"   Not found: {path}")

print("\n" + "=" * 60)
print("Recommendation:")
print("=" * 60)
print("""
If DATABASE_URL is not showing the MySQL URL:
1. Check your WSGI file is setting DATABASE_URL BEFORE importing app
2. Delete or rename any .env file with SQLite settings
3. Reload the web app

Your WSGI should have this BEFORE 'from app import app':
os.environ['DATABASE_URL'] = 'mysql+pymysql://nicway2:truelog123%40@nicway2.mysql.pythonanywhere-services.com/nicway2$inventory'
""")
