#!/usr/bin/env python3
"""
Database migration script to add approval workflow fields to feature_requests table
"""

import logging
from sqlalchemy import create_engine, text
import config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_approval_fields():
    """Add approval workflow fields to feature_requests table"""

    # Create engine
    engine = create_engine(config.DATABASE_URL)

    # SQL statements to add the new columns
    migration_queries = [
        # Add approver_id column
        "ALTER TABLE feature_requests ADD COLUMN approver_id INTEGER;",

        # Add approval_requested_at column
        "ALTER TABLE feature_requests ADD COLUMN approval_requested_at DATETIME;",

        # Add approved_at column
        "ALTER TABLE feature_requests ADD COLUMN approved_at DATETIME;",

        # Add foreign key constraint for approver_id (optional, might fail if referential integrity is strict)
        # "ALTER TABLE feature_requests ADD CONSTRAINT fk_feature_requests_approver_id FOREIGN KEY (approver_id) REFERENCES users(id);"
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
                logger.info("✅ Successfully added approval workflow fields to feature_requests table")

            except Exception as e:
                # Rollback on error
                trans.rollback()
                raise e

    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        return False

    return True

if __name__ == "__main__":
    logger.info("Starting database migration for approval workflow fields...")

    try:
        success = migrate_approval_fields()
        if success:
            logger.info("🎉 Migration completed successfully!")
        else:
            logger.error("💥 Migration failed!")

    except Exception as e:
        logger.error(f"💥 Migration script failed: {str(e)}")