#!/usr/bin/env python3
"""
Quick fix to add can_access_debug_logs column to permissions table
Run this on PythonAnywhere to fix the missing column error
"""

import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_debug_logs_column():
    """Add can_access_debug_logs column to permissions table"""

    # Update this path to match your PythonAnywhere database location
    db_path = 'inventory.db'  # Or use the full path on PythonAnywhere

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if column already exists
        cursor.execute("PRAGMA table_info(permissions)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'can_access_debug_logs' in columns:
            logger.info("✅ Column can_access_debug_logs already exists")
            return True

        # Add the column
        logger.info("Adding can_access_debug_logs column...")
        cursor.execute("ALTER TABLE permissions ADD COLUMN can_access_debug_logs BOOLEAN DEFAULT 0")
        conn.commit()
        logger.info("✅ Successfully added can_access_debug_logs column")

        # Set it to TRUE for SUPER_ADMIN and DEVELOPER
        logger.info("Updating permissions for SUPER_ADMIN and DEVELOPER...")
        cursor.execute("""
            UPDATE permissions
            SET can_access_debug_logs = 1
            WHERE user_type IN ('SUPER_ADMIN', 'DEVELOPER')
        """)
        conn.commit()

        affected_rows = cursor.rowcount
        logger.info(f"✅ Updated {affected_rows} permission records")

        conn.close()
        return True

    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        if 'conn' in locals():
            conn.close()
        return False

if __name__ == '__main__':
    logger.info("Starting quick fix for can_access_debug_logs column...")
    success = add_debug_logs_column()

    if success:
        logger.info("🎉 Fix completed successfully!")
        logger.info("Please reload your web app on PythonAnywhere")
    else:
        logger.error("💥 Fix failed!")
