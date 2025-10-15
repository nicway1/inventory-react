#!/usr/bin/env python3
"""
Emergency fix for MySQL screenshot_path migration
This script imports from your Flask app to use the exact same database connection
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment first
from dotenv import load_dotenv
load_dotenv()

print("="*60)
print("SCREENSHOT MIGRATION FIX")
print("="*60)

try:
    # Import after loading environment
    from database import engine, SessionLocal
    from sqlalchemy import inspect, text
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    print(f"\nDatabase Engine: {engine.url}")
    print(f"Database Type: {engine.dialect.name}")

    # Get inspector
    inspector = inspect(engine)

    # Check if bug_reports table exists
    if 'bug_reports' not in inspector.get_table_names():
        print("\n❌ ERROR: bug_reports table does not exist!")
        sys.exit(1)

    # Check existing columns
    columns = [col['name'] for col in inspector.get_columns('bug_reports')]
    print(f"\nFound {len(columns)} columns in bug_reports table")

    if 'screenshot_path' in columns:
        print("\n✅ screenshot_path column already exists!")
        print("No migration needed.")
        sys.exit(0)

    print("\n⚠️  screenshot_path column is missing. Running migration...")

    # Determine database type and run appropriate migration
    db_type = engine.dialect.name
    db_session = SessionLocal()

    try:
        if db_type == 'mysql':
            print("Running MySQL ALTER TABLE statement...")
            db_session.execute(text("""
                ALTER TABLE bug_reports
                ADD COLUMN screenshot_path VARCHAR(500) NULL
            """))
        elif db_type == 'sqlite':
            print("Running SQLite ALTER TABLE statement...")
            db_session.execute(text("""
                ALTER TABLE bug_reports
                ADD COLUMN screenshot_path VARCHAR(500)
            """))
        elif db_type == 'postgresql':
            print("Running PostgreSQL ALTER TABLE statement...")
            db_session.execute(text("""
                ALTER TABLE bug_reports
                ADD COLUMN screenshot_path VARCHAR(500)
            """))
        else:
            print(f"\n❌ ERROR: Unsupported database type: {db_type}")
            sys.exit(1)

        db_session.commit()
        print("✅ Migration SQL executed successfully")

        # Verify
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('bug_reports')]

        if 'screenshot_path' in columns:
            print("\n" + "="*60)
            print("✅ SUCCESS! screenshot_path column added successfully!")
            print("="*60)
            print("\nNext steps:")
            print("1. Restart your Flask application")
            print("2. The error should be gone!")
            print("3. You can now upload screenshots to bug reports")
            print("="*60 + "\n")
        else:
            print("\n❌ ERROR: Migration ran but column not found!")
            sys.exit(1)

    except Exception as e:
        db_session.rollback()
        print(f"\n❌ ERROR running migration: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db_session.close()

except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
