#!/usr/bin/env python3
"""
Migration script to change customer_users.country from ENUM to VARCHAR(100)
Run this script on PythonAnywhere to migrate the database.

Usage:
    python3 migrations/migrate_customer_country.py
"""

import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import db_manager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_customer_country_column():
    """
    Migrate customer_users.country from ENUM to VARCHAR(100)
    """
    db_session = db_manager.get_session()

    try:
        logger.info("Starting migration: customer_users.country ENUM -> VARCHAR(100)")

        # Step 1: Check if migration is needed
        logger.info("Step 1: Checking current column type...")
        check_query = text("""
            SELECT COLUMN_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'customer_users'
            AND COLUMN_NAME = 'country'
        """)
        result = db_session.execute(check_query).fetchone()

        if result:
            column_type = result[0]
            logger.info(f"Current column type: {column_type}")

            # Check if already VARCHAR
            if 'varchar' in column_type.lower():
                logger.info("✓ Column is already VARCHAR. Migration not needed.")
                return True

            if 'enum' not in column_type.lower():
                logger.warning(f"⚠ Unexpected column type: {column_type}. Proceeding anyway...")

        # Step 2: Add temporary column
        logger.info("Step 2: Adding temporary column country_temp...")
        db_session.execute(text("""
            ALTER TABLE customer_users
            ADD COLUMN country_temp VARCHAR(100)
        """))
        db_session.commit()
        logger.info("✓ Temporary column added")

        # Step 3: Copy data from enum to string
        logger.info("Step 3: Copying data from country to country_temp...")
        db_session.execute(text("""
            UPDATE customer_users
            SET country_temp = country
        """))
        db_session.commit()
        logger.info("✓ Data copied")

        # Step 4: Drop old enum column
        logger.info("Step 4: Dropping old ENUM column...")
        db_session.execute(text("""
            ALTER TABLE customer_users
            DROP COLUMN country
        """))
        db_session.commit()
        logger.info("✓ Old column dropped")

        # Step 5: Rename temp column to country
        logger.info("Step 5: Renaming country_temp to country...")
        db_session.execute(text("""
            ALTER TABLE customer_users
            CHANGE COLUMN country_temp country VARCHAR(100) NOT NULL
        """))
        db_session.commit()
        logger.info("✓ Column renamed")

        logger.info("=" * 60)
        logger.info("✓ Migration completed successfully!")
        logger.info("=" * 60)
        logger.info("You can now create customers with custom country names.")

        return True

    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"✗ Migration failed: {str(e)}")
        logger.error("=" * 60)
        db_session.rollback()

        # Try to cleanup temporary column if it exists
        try:
            logger.info("Attempting cleanup...")
            db_session.execute(text("""
                ALTER TABLE customer_users
                DROP COLUMN IF EXISTS country_temp
            """))
            db_session.commit()
            logger.info("✓ Cleanup completed")
        except:
            pass

        return False

    finally:
        db_session.close()

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("Customer Country Column Migration")
    print("=" * 60)
    print("This will change customer_users.country from ENUM to VARCHAR(100)")
    print("to support custom country names.")
    print("=" * 60)

    response = input("\nProceed with migration? (yes/no): ").strip().lower()

    if response in ['yes', 'y']:
        success = migrate_customer_country_column()
        sys.exit(0 if success else 1)
    else:
        print("\nMigration cancelled.")
        sys.exit(0)
