#!/usr/bin/env python3
"""
PythonAnywhere migration script to add screenshot_path column to bug_reports table
Run this in PythonAnywhere Bash console or add as a Flask route
"""

import logging
from sqlalchemy import create_engine, inspect, text
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Add screenshot_path column to bug_reports table"""
    try:
        # Get DATABASE_URL from environment
        database_url = os.getenv('DATABASE_URL')

        if not database_url:
            logger.error("DATABASE_URL not set in environment")
            logger.info("Please set DATABASE_URL environment variable")
            return False

        logger.info(f"Connecting to database...")

        # Create engine
        engine = create_engine(database_url)

        # Get inspector to check existing columns
        inspector = inspect(engine)

        # Check if bug_reports table exists
        if 'bug_reports' not in inspector.get_table_names():
            logger.error("❌ bug_reports table does not exist")
            return False

        # Get existing columns
        columns = [col['name'] for col in inspector.get_columns('bug_reports')]

        if 'screenshot_path' in columns:
            logger.info("✅ screenshot_path column already exists in bug_reports table")
            return True

        # Determine database type
        db_type = engine.dialect.name
        logger.info(f"Database type: {db_type}")

        # Add the screenshot_path column
        logger.info("Adding screenshot_path column to bug_reports table...")

        with engine.connect() as conn:
            if db_type == 'mysql':
                conn.execute(text("""
                    ALTER TABLE bug_reports
                    ADD COLUMN screenshot_path VARCHAR(500) NULL
                """))
                conn.commit()
            elif db_type == 'sqlite':
                conn.execute(text("""
                    ALTER TABLE bug_reports
                    ADD COLUMN screenshot_path VARCHAR(500)
                """))
                conn.commit()
            elif db_type == 'postgresql':
                conn.execute(text("""
                    ALTER TABLE bug_reports
                    ADD COLUMN screenshot_path VARCHAR(500)
                """))
                conn.commit()
            else:
                logger.error(f"❌ Unsupported database type: {db_type}")
                return False

        logger.info("✅ screenshot_path column added successfully!")

        # Verify the column was added
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('bug_reports')]

        if 'screenshot_path' in columns:
            logger.info("✅ Verified: screenshot_path column exists in bug_reports table")
            return True
        else:
            logger.error("❌ Failed to verify screenshot_path column")
            return False

    except Exception as e:
        logger.error(f"❌ Error during migration: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n" + "="*60)
    print("BUG REPORTS SCREENSHOT MIGRATION")
    print("="*60 + "\n")

    success = run_migration()

    print("\n" + "="*60)
    if success:
        print("MIGRATION COMPLETED SUCCESSFULLY")
        print("\nNext steps:")
        print("1. Reload your PythonAnywhere web app")
        print("2. Test uploading a screenshot to a bug report")
    else:
        print("MIGRATION FAILED")
        print("\nPlease check the error messages above")
    print("="*60 + "\n")
