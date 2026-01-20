"""
Migration script to add assigned_to_id column to service_records table
Run this script to add the @mention assignment feature to Service Records
"""

import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Add assigned_to_id column to service_records table"""

    # Import database connection
    try:
        from database import engine
        from sqlalchemy import text
    except ImportError:
        logger.error("Could not import database module. Make sure you're running from the project directory.")
        return False

    try:
        with engine.connect() as conn:
            # Check if column already exists
            # Works for both MySQL and SQLite
            try:
                result = conn.execute(text("SELECT assigned_to_id FROM service_records LIMIT 1"))
                logger.info("✅ assigned_to_id column already exists in service_records table")
                return True
            except Exception:
                pass  # Column doesn't exist, proceed with migration

            logger.info("Adding assigned_to_id column to service_records table...")

            # Detect database type
            db_url = str(engine.url)

            if 'mysql' in db_url.lower():
                # MySQL syntax
                alter_sql = """
                    ALTER TABLE service_records
                    ADD COLUMN assigned_to_id INT NULL,
                    ADD CONSTRAINT fk_service_records_assigned_to
                    FOREIGN KEY (assigned_to_id) REFERENCES users(id)
                """
            else:
                # SQLite syntax (no foreign key constraint in ALTER)
                alter_sql = "ALTER TABLE service_records ADD COLUMN assigned_to_id INTEGER"

            conn.execute(text(alter_sql))
            conn.commit()

            logger.info("✅ Successfully added assigned_to_id column to service_records table")

            # Verify the column was added
            try:
                result = conn.execute(text("SELECT assigned_to_id FROM service_records LIMIT 1"))
                logger.info("✅ Verified: assigned_to_id column exists in service_records table")
            except Exception as e:
                logger.error(f"❌ Verification failed: {e}")
                return False

            return True

    except Exception as e:
        logger.error(f"❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Service Records Migration - Add assigned_to_id column")
    print("=" * 60)
    print()

    success = run_migration()

    print()
    if success:
        print("✅ Migration completed successfully!")
        print()
        print("You can now use the @mention feature in Service Records")
        print("to assign users to service requests.")
    else:
        print("❌ Migration failed. Check the error messages above.")
        sys.exit(1)
