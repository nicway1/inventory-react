#!/usr/bin/env python3
"""
Universal migration script to add screenshot_path column to bug_reports table
Works with both SQLite and MySQL by using the existing database connection
"""

import logging
from database import engine
from sqlalchemy import inspect, text

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_screenshot_column():
    """Add screenshot_path column to bug_reports table"""
    try:
        # Get inspector to check existing columns
        inspector = inspect(engine)

        # Check if bug_reports table exists
        if 'bug_reports' not in inspector.get_table_names():
            logger.error("❌ bug_reports table does not exist")
            return

        # Get existing columns
        columns = [col['name'] for col in inspector.get_columns('bug_reports')]

        if 'screenshot_path' in columns:
            logger.info("✅ screenshot_path column already exists in bug_reports table")
            return

        # Determine database type
        db_type = engine.dialect.name
        logger.info(f"Database type: {db_type}")

        # Add the screenshot_path column based on database type
        logger.info("Adding screenshot_path column to bug_reports table...")

        with engine.connect() as conn:
            if db_type == 'sqlite':
                conn.execute(text("""
                    ALTER TABLE bug_reports
                    ADD COLUMN screenshot_path VARCHAR(500)
                """))
            elif db_type == 'mysql':
                conn.execute(text("""
                    ALTER TABLE bug_reports
                    ADD COLUMN screenshot_path VARCHAR(500) NULL
                """))
            elif db_type == 'postgresql':
                conn.execute(text("""
                    ALTER TABLE bug_reports
                    ADD COLUMN screenshot_path VARCHAR(500)
                """))
            else:
                logger.error(f"❌ Unsupported database type: {db_type}")
                return

            conn.commit()

        logger.info("✅ screenshot_path column added successfully!")

        # Verify the column was added
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('bug_reports')]

        if 'screenshot_path' in columns:
            logger.info("✅ Verified: screenshot_path column exists in bug_reports table")
        else:
            logger.error("❌ Failed to add screenshot_path column")

    except Exception as e:
        logger.error(f"❌ Error adding screenshot_path column: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    add_screenshot_column()
