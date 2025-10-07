#!/usr/bin/env python3
"""
Database migration script to:
1. Add can_access_debug_logs permission to permissions table
2. Create DEVELOPER permission record with all SUPER_ADMIN permissions + debug logs
3. Update admin user to DEVELOPER role
"""

import logging
from sqlalchemy import create_engine, text
import config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_developer_role():
    """Add DEVELOPER role support to database"""

    # Create engine - use SQLite
    engine = create_engine(config.DATABASE_URL)

    try:
        with engine.connect() as connection:
            # Step 1: Add DEVELOPER to user_type ENUM in permissions table
            trans = connection.begin()
            try:
                logger.info("Adding DEVELOPER to user_type ENUM in permissions table...")
                connection.execute(text("ALTER TABLE permissions MODIFY COLUMN user_type ENUM('SUPER_ADMIN', 'DEVELOPER', 'SUPERVISOR', 'COUNTRY_ADMIN', 'CLIENT') NOT NULL;"))
                trans.commit()
                logger.info("✅ Successfully updated permissions.user_type ENUM")
            except Exception as e:
                trans.rollback()
                if "duplicate" in str(e).lower() or "already" in str(e).lower():
                    logger.info("DEVELOPER already in ENUM, skipping...")
                else:
                    raise e

            # Step 1b: Add DEVELOPER to user_type ENUM in users table
            trans = connection.begin()
            try:
                logger.info("Adding DEVELOPER to user_type ENUM in users table...")
                connection.execute(text("ALTER TABLE users MODIFY COLUMN user_type ENUM('SUPER_ADMIN', 'DEVELOPER', 'SUPERVISOR', 'COUNTRY_ADMIN', 'CLIENT') DEFAULT 'SUPERVISOR';"))
                trans.commit()
                logger.info("✅ Successfully updated users.user_type ENUM")
            except Exception as e:
                trans.rollback()
                if "duplicate" in str(e).lower() or "already" in str(e).lower():
                    logger.info("DEVELOPER already in ENUM, skipping...")
                else:
                    raise e

            # Step 2: Add can_access_debug_logs column to permissions table
            trans = connection.begin()
            try:
                logger.info("Adding can_access_debug_logs column to permissions table...")
                connection.execute(text("ALTER TABLE permissions ADD COLUMN can_access_debug_logs BOOLEAN DEFAULT FALSE;"))
                trans.commit()
                logger.info("✅ Successfully added can_access_debug_logs column")
            except Exception as e:
                trans.rollback()
                if "duplicate column name" in str(e).lower():
                    logger.info("Column can_access_debug_logs already exists, skipping...")
                else:
                    raise e

            # Step 3: Create DEVELOPER permission record by copying SUPER_ADMIN permissions
            trans = connection.begin()
            try:
                logger.info("Creating DEVELOPER permission record...")

                # Check if DEVELOPER permission already exists
                result = connection.execute(text("SELECT COUNT(*) FROM permissions WHERE user_type = 'DEVELOPER'"))
                count = result.scalar()

                if count == 0:
                    # Copy all SUPER_ADMIN permissions and set debug logs to TRUE
                    logger.info("Copying SUPER_ADMIN permissions to create DEVELOPER role...")

                    # Get all column names from permissions table
                    result = connection.execute(text("SHOW COLUMNS FROM permissions"))
                    all_columns = [row[0] for row in result]

                    # Filter out id and user_type, as we'll handle those separately
                    permission_columns = [col for col in all_columns if col not in ['id', 'user_type']]
                    columns_str = ', '.join(permission_columns)

                    # Create INSERT query that copies SUPER_ADMIN but sets user_type to DEVELOPER
                    insert_query = text(f"""
                        INSERT INTO permissions (user_type, {columns_str})
                        SELECT 'DEVELOPER', {columns_str}
                        FROM permissions
                        WHERE user_type = 'SUPER_ADMIN'
                    """)
                    connection.execute(insert_query)

                    # Update can_access_debug_logs to TRUE for DEVELOPER
                    connection.execute(text("UPDATE permissions SET can_access_debug_logs = TRUE WHERE user_type = 'DEVELOPER'"))
                    logger.info("✅ Successfully created DEVELOPER permission record")
                else:
                    logger.info("DEVELOPER permission record already exists, updating can_access_debug_logs...")
                    connection.execute(text("UPDATE permissions SET can_access_debug_logs = TRUE WHERE user_type = 'DEVELOPER'"))
                    logger.info("✅ Successfully updated DEVELOPER permission record")

                trans.commit()
            except Exception as e:
                trans.rollback()
                raise e

            # Step 4: Update SUPER_ADMIN to also have debug logs access
            trans = connection.begin()
            try:
                logger.info("Updating SUPER_ADMIN to have debug logs access...")
                connection.execute(text("UPDATE permissions SET can_access_debug_logs = TRUE WHERE user_type = 'SUPER_ADMIN'"))
                trans.commit()
                logger.info("✅ Successfully updated SUPER_ADMIN permissions")
            except Exception as e:
                trans.rollback()
                raise e

            # Step 5: Update admin user to DEVELOPER role
            trans = connection.begin()
            try:
                logger.info("Updating admin user to DEVELOPER role...")

                # Check if admin user exists
                result = connection.execute(text("SELECT COUNT(*) FROM users WHERE username = 'admin'"))
                count = result.scalar()

                if count > 0:
                    connection.execute(text("UPDATE users SET user_type = 'DEVELOPER' WHERE username = 'admin'"))
                    logger.info("✅ Successfully updated admin user to DEVELOPER role")
                else:
                    logger.warning("⚠️ Admin user not found, skipping user update")

                trans.commit()
            except Exception as e:
                trans.rollback()
                raise e

    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        return False

    return True

if __name__ == "__main__":
    logger.info("Starting database migration for DEVELOPER role...")

    try:
        success = migrate_developer_role()
        if success:
            logger.info("🎉 Migration completed successfully!")
        else:
            logger.error("💥 Migration failed!")

    except Exception as e:
        logger.error(f"💥 Migration script failed: {str(e)}")
