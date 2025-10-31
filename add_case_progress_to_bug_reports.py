#!/usr/bin/env python3
"""
Add case_progress column to bug_reports table
"""
import sqlite3
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_case_progress_column():
    """Add case_progress column to bug_reports table"""
    db_path = os.path.join(os.path.dirname(__file__), 'inventory.db')

    if not os.path.exists(db_path):
        logger.error(f"Database not found at {db_path}")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if column already exists
        cursor.execute("PRAGMA table_info(bug_reports)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'case_progress' in columns:
            logger.info("case_progress column already exists")
            conn.close()
            return True

        # Add the column
        logger.info("Adding case_progress column to bug_reports table...")
        cursor.execute("""
            ALTER TABLE bug_reports
            ADD COLUMN case_progress INTEGER DEFAULT 0
        """)

        conn.commit()
        logger.info("✓ Successfully added case_progress column")

        # Verify
        cursor.execute("PRAGMA table_info(bug_reports)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'case_progress' in columns:
            logger.info("✓ Verified: case_progress column exists")
        else:
            logger.error("✗ Verification failed: case_progress column not found")

        conn.close()
        return True

    except Exception as e:
        logger.error(f"Error adding column: {str(e)}")
        if 'conn' in locals():
            conn.close()
        return False

if __name__ == '__main__':
    logger.info("Starting migration: Add case_progress to bug_reports")
    success = add_case_progress_column()
    if success:
        logger.info("Migration completed successfully!")
    else:
        logger.error("Migration failed!")
