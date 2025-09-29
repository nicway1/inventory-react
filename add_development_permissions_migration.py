#!/usr/bin/env python3
"""
Database migration script to add development module permissions to permissions table
"""

import logging
from sqlalchemy import create_engine, text
import config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_development_permissions():
    """Add development module permissions to permissions table"""

    # Create engine - use SQLite
    engine = create_engine(config.DATABASE_URL)

    # SQL statements to add the new columns
    migration_queries = [
        # Development Module Permissions
        "ALTER TABLE permissions ADD COLUMN can_access_development BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE permissions ADD COLUMN can_view_features BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE permissions ADD COLUMN can_create_features BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE permissions ADD COLUMN can_edit_features BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE permissions ADD COLUMN can_approve_features BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE permissions ADD COLUMN can_view_bugs BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE permissions ADD COLUMN can_create_bugs BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE permissions ADD COLUMN can_edit_bugs BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE permissions ADD COLUMN can_view_releases BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE permissions ADD COLUMN can_create_releases BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE permissions ADD COLUMN can_edit_releases BOOLEAN DEFAULT FALSE;",
    ]

    try:
        with engine.connect() as connection:
            # Start a transaction
            trans = connection.begin()

            try:
                for query in migration_queries:
                    logger.info(f"Executing: {query}")
                    connection.execute(text(query))

                # Commit the transaction
                trans.commit()
                logger.info("✅ Successfully added development permissions to permissions table")

                # Now update Super Admin permissions to have all development access
                update_queries = [
                    "UPDATE permissions SET can_access_development = TRUE WHERE user_type = 'SUPER_ADMIN';",
                    "UPDATE permissions SET can_view_features = TRUE WHERE user_type = 'SUPER_ADMIN';",
                    "UPDATE permissions SET can_create_features = TRUE WHERE user_type = 'SUPER_ADMIN';",
                    "UPDATE permissions SET can_edit_features = TRUE WHERE user_type = 'SUPER_ADMIN';",
                    "UPDATE permissions SET can_approve_features = TRUE WHERE user_type = 'SUPER_ADMIN';",
                    "UPDATE permissions SET can_view_bugs = TRUE WHERE user_type = 'SUPER_ADMIN';",
                    "UPDATE permissions SET can_create_bugs = TRUE WHERE user_type = 'SUPER_ADMIN';",
                    "UPDATE permissions SET can_edit_bugs = TRUE WHERE user_type = 'SUPER_ADMIN';",
                    "UPDATE permissions SET can_view_releases = TRUE WHERE user_type = 'SUPER_ADMIN';",
                    "UPDATE permissions SET can_create_releases = TRUE WHERE user_type = 'SUPER_ADMIN';",
                    "UPDATE permissions SET can_edit_releases = TRUE WHERE user_type = 'SUPER_ADMIN';"
                ]

                trans = connection.begin()
                for query in update_queries:
                    logger.info(f"Executing: {query}")
                    connection.execute(text(query))

                trans.commit()
                logger.info("✅ Successfully updated Super Admin development permissions")

            except Exception as e:
                # Rollback on error
                trans.rollback()
                raise e

    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        return False

    return True

if __name__ == "__main__":
    logger.info("Starting database migration for development permissions...")

    try:
        success = migrate_development_permissions()
        if success:
            logger.info("🎉 Migration completed successfully!")
        else:
            logger.error("💥 Migration failed!")

    except Exception as e:
        logger.error(f"💥 Migration script failed: {str(e)}")