#!/usr/bin/env python3
"""
Database migration script for SQLite to:
1. Add can_access_debug_logs permission to permissions table
2. Create DEVELOPER permission record with all SUPER_ADMIN permissions + debug logs
3. Update admin user to DEVELOPER role
"""

import logging
import sqlite3
import config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_developer_role_sqlite():
    """Add DEVELOPER role support to SQLite database"""

    # Get database path from config
    db_url = config.DATABASE_URL
    if db_url.startswith('sqlite:///'):
        db_path = db_url.replace('sqlite:///', '')
    else:
        logger.error("This script only works with SQLite databases")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Step 1: Add can_access_debug_logs column to permissions table
        try:
            logger.info("Adding can_access_debug_logs column to permissions table...")
            cursor.execute("ALTER TABLE permissions ADD COLUMN can_access_debug_logs BOOLEAN DEFAULT 0;")
            conn.commit()
            logger.info("✅ Successfully added can_access_debug_logs column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                logger.info("Column can_access_debug_logs already exists, skipping...")
            else:
                raise e

        # Step 2: Check if DEVELOPER permission record exists
        logger.info("Creating DEVELOPER permission record...")
        cursor.execute("SELECT COUNT(*) FROM permissions WHERE user_type = 'DEVELOPER'")
        count = cursor.fetchone()[0]

        if count == 0:
            # Get all columns from permissions table
            cursor.execute("PRAGMA table_info(permissions)")
            columns_info = cursor.fetchall()
            permission_columns = [col[1] for col in columns_info if col[1] not in ['id', 'user_type']]
            columns_str = ', '.join(permission_columns)

            # Copy SUPER_ADMIN permissions to create DEVELOPER
            logger.info("Copying SUPER_ADMIN permissions to create DEVELOPER role...")
            cursor.execute(f"""
                INSERT INTO permissions (user_type, {columns_str})
                SELECT 'DEVELOPER', {columns_str}
                FROM permissions
                WHERE user_type = 'SUPER_ADMIN'
            """)

            # Update can_access_debug_logs to TRUE for DEVELOPER
            cursor.execute("UPDATE permissions SET can_access_debug_logs = 1 WHERE user_type = 'DEVELOPER'")
            conn.commit()
            logger.info("✅ Successfully created DEVELOPER permission record")
        else:
            logger.info("DEVELOPER permission record already exists, updating can_access_debug_logs...")
            cursor.execute("UPDATE permissions SET can_access_debug_logs = 1 WHERE user_type = 'DEVELOPER'")
            conn.commit()
            logger.info("✅ Successfully updated DEVELOPER permission record")

        # Step 3: Update SUPER_ADMIN to also have debug logs access
        logger.info("Updating SUPER_ADMIN to have debug logs access...")
        cursor.execute("UPDATE permissions SET can_access_debug_logs = 1 WHERE user_type = 'SUPER_ADMIN'")
        conn.commit()
        logger.info("✅ Successfully updated SUPER_ADMIN permissions")

        # Step 4: Update admin user to DEVELOPER role
        logger.info("Updating admin user to DEVELOPER role...")
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
        count = cursor.fetchone()[0]

        if count > 0:
            cursor.execute("UPDATE users SET user_type = 'DEVELOPER' WHERE username = 'admin'")
            conn.commit()
            logger.info("✅ Successfully updated admin user to DEVELOPER role")
        else:
            logger.warning("⚠️ Admin user not found, skipping user update")

        conn.close()

    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

    return True

if __name__ == "__main__":
    logger.info("Starting SQLite database migration for DEVELOPER role...")

    try:
        success = migrate_developer_role_sqlite()
        if success:
            logger.info("🎉 Migration completed successfully!")
        else:
            logger.error("💥 Migration failed!")

    except Exception as e:
        logger.error(f"💥 Migration script failed: {str(e)}")
