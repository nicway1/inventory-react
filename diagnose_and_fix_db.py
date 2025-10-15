#!/usr/bin/env python3
"""
Diagnose which database is being used and fix the screenshot_path issue
"""
import sys
import os

# Simulate Flask's environment
os.chdir('/Users/user/invK/inventory')
sys.path.insert(0, '/Users/user/invK/inventory')

print("="*70)
print("DATABASE DIAGNOSIS AND FIX")
print("="*70)

try:
    # Check all possible ways DATABASE_URL might be set
    print("\n1. Checking environment variables...")
    print(f"   DATABASE_URL from os.environ: {os.environ.get('DATABASE_URL', 'NOT SET')}")

    # Load .env
    print("\n2. Loading .env file...")
    from dotenv import load_dotenv
    load_dotenv(override=True)
    print(f"   DATABASE_URL after load_dotenv: {os.getenv('DATABASE_URL', 'NOT SET')}")

    # Check app.py config
    print("\n3. Checking app.py configuration...")
    import app
    if hasattr(app.app, 'config'):
        db_uri = app.app.config.get('SQLALCHEMY_DATABASE_URI', 'NOT SET')
        print(f"   SQLALCHEMY_DATABASE_URI: {db_uri}")

    # Import database module
    print("\n4. Checking database.py module...")
    from database import engine, DATABASE_URL, SessionLocal
    print(f"   DATABASE_URL variable: {DATABASE_URL}")
    print(f"   Engine URL: {engine.url}")
    print(f"   Engine dialect: {engine.dialect.name}")
    print(f"   Engine driver: {engine.driver}")

    # Try to connect and inspect
    print("\n5. Connecting to database...")
    from sqlalchemy import inspect, text
    inspector = inspect(engine)

    tables = inspector.get_table_names()
    print(f"   Found {len(tables)} tables")

    if 'bug_reports' not in tables:
        print("\n   ❌ ERROR: bug_reports table not found!")
        print("   This database doesn't have your application data.")
        sys.exit(1)

    # Check bug_reports columns
    print("\n6. Checking bug_reports table...")
    columns = [col['name'] for col in inspector.get_columns('bug_reports')]
    print(f"   Found {len(columns)} columns in bug_reports")

    has_screenshot = 'screenshot_path' in columns
    print(f"   Has screenshot_path column: {has_screenshot}")

    if has_screenshot:
        print("\n" + "="*70)
        print("✅ DATABASE IS ALREADY MIGRATED!")
        print("="*70)
        print("\nThe screenshot_path column exists in your database.")
        print("If you're still seeing errors, try:")
        print("1. Make sure Flask is completely stopped")
        print("2. Clear any __pycache__ directories:")
        print("   find . -type d -name '__pycache__' -exec rm -rf {} +")
        print("3. Restart Flask")
        sys.exit(0)

    # Need to run migration
    print("\n7. screenshot_path column is MISSING. Running migration...")
    db_type = engine.dialect.name

    db_session = SessionLocal()
    try:
        if db_type == 'mysql':
            print("   Executing MySQL ALTER TABLE...")
            db_session.execute(text("""
                ALTER TABLE bug_reports
                ADD COLUMN screenshot_path VARCHAR(500) NULL
            """))
        elif db_type == 'sqlite':
            print("   Executing SQLite ALTER TABLE...")
            db_session.execute(text("""
                ALTER TABLE bug_reports
                ADD COLUMN screenshot_path VARCHAR(500)
            """))
        elif db_type == 'postgresql':
            print("   Executing PostgreSQL ALTER TABLE...")
            db_session.execute(text("""
                ALTER TABLE bug_reports
                ADD COLUMN screenshot_path VARCHAR(500)
            """))
        else:
            print(f"\n   ❌ ERROR: Unsupported database type: {db_type}")
            sys.exit(1)

        db_session.commit()
        print("   ✅ SQL executed successfully")

        # Verify
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('bug_reports')]

        if 'screenshot_path' in columns:
            print("\n" + "="*70)
            print("✅ MIGRATION SUCCESSFUL!")
            print("="*70)
            print("\nThe screenshot_path column has been added to your database.")
            print("\nNext steps:")
            print("1. Clear Python cache: find . -type d -name '__pycache__' -exec rm -rf {} +")
            print("2. Restart your Flask application")
            print("3. The error should be gone!")
            print("="*70)
        else:
            print("\n❌ ERROR: Column not found after migration!")

    except Exception as e:
        db_session.rollback()
        print(f"\n   ❌ ERROR during migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db_session.close()

except Exception as e:
    print(f"\n❌ FATAL ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
