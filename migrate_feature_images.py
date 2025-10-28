#!/usr/bin/env python3
"""
Migration script to add images column to feature_requests table
"""

from sqlalchemy import create_engine, text
from utils.db_manager import DatabaseManager
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_feature_images():
    """Add images column to feature_requests table"""
    try:
        # Get database connection
        db_manager = DatabaseManager()
        engine = db_manager.engine

        logger.info("Adding images column to feature_requests table...")

        with engine.begin() as conn:
            if 'mysql' in str(engine.url):
                # MySQL syntax
                conn.execute(text("""
                    ALTER TABLE feature_requests
                    ADD COLUMN images TEXT NULL
                """))
            else:
                # SQLite syntax
                conn.execute(text("""
                    ALTER TABLE feature_requests
                    ADD COLUMN images TEXT
                """))

            logger.info("✓ Successfully added images column to feature_requests")

        return True

    except Exception as e:
        # Check if column already exists
        if 'Duplicate column name' in str(e) or 'duplicate column name' in str(e):
            logger.info("✓ Column 'images' already exists in feature_requests table")
            return True

        logger.error(f"✗ Error during migration: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    success = migrate_feature_images()
    sys.exit(0 if success else 1)
