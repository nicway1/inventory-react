#!/usr/bin/env python3
"""
Migration script to add screenshot_path column to bug_reports table
"""

import sqlite3
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_screenshot_column():
    """Add screenshot_path column to bug_reports table"""
    try:
        # Connect to the database
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()

        # Check if column already exists
        cursor.execute("PRAGMA table_info(bug_reports)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'screenshot_path' in columns:
            logger.info("screenshot_path column already exists in bug_reports table")
            conn.close()
            return

        # Add the screenshot_path column
        logger.info("Adding screenshot_path column to bug_reports table...")
        cursor.execute("""
            ALTER TABLE bug_reports
            ADD COLUMN screenshot_path VARCHAR(500)
        """)

        conn.commit()
        logger.info("✅ screenshot_path column added successfully!")

        # Verify the column was added
        cursor.execute("PRAGMA table_info(bug_reports)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'screenshot_path' in columns:
            logger.info("✅ Verified: screenshot_path column exists in bug_reports table")
        else:
            logger.error("❌ Failed to add screenshot_path column")

        conn.close()

    except Exception as e:
        logger.error(f"❌ Error adding screenshot_path column: {str(e)}")
        raise

if __name__ == "__main__":
    add_screenshot_column()
