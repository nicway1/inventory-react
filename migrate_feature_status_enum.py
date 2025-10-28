#!/usr/bin/env python3
"""
Migration script to update feature_requests status enum
Adds missing statuses: PENDING_APPROVAL, APPROVED, REJECTED
"""

from sqlalchemy import create_engine, text
from utils.db_manager import DatabaseManager
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_feature_status_enum():
    """Update the feature_requests status enum to include all statuses"""
    try:
        # Get database connection
        db_manager = DatabaseManager()
        engine = db_manager.engine

        # Check if we're using MySQL (enum update only needed for MySQL)
        if 'mysql' not in str(engine.url):
            logger.info("Not using MySQL - enum update not needed (SQLite stores as strings)")
            return True

        logger.info("Updating feature_requests status enum...")

        with engine.begin() as conn:
            # Update the status column to include all enum values
            conn.execute(text("""
                ALTER TABLE feature_requests
                MODIFY COLUMN status ENUM(
                    'REQUESTED',
                    'PENDING_APPROVAL',
                    'APPROVED',
                    'REJECTED',
                    'IN_PLANNING',
                    'IN_DEVELOPMENT',
                    'IN_TESTING',
                    'COMPLETED',
                    'CANCELLED'
                ) DEFAULT 'REQUESTED'
            """))

            logger.info("✓ Successfully updated feature_requests status enum")
            logger.info("  Added: PENDING_APPROVAL, APPROVED, REJECTED")

        return True

    except Exception as e:
        logger.error(f"✗ Error during migration: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    success = migrate_feature_status_enum()
    sys.exit(0 if success else 1)
