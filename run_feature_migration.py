#!/usr/bin/env python3
"""Run migration to add case_progress to feature_requests table"""

from database import SessionLocal, engine
from sqlalchemy import text

def run_migration():
    """Add case_progress column to feature_requests table"""
    session = SessionLocal()

    try:
        # Check if column already exists
        result = session.execute(text("""
            SELECT COUNT(*)
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'feature_requests'
            AND COLUMN_NAME = 'case_progress'
        """))

        exists = result.scalar()

        if exists:
            print("✓ Column 'case_progress' already exists in feature_requests table")
            return True

        # Add the column
        print("Adding 'case_progress' column to feature_requests table...")
        session.execute(text("""
            ALTER TABLE feature_requests
            ADD COLUMN case_progress INT DEFAULT 0
            COMMENT 'Progress percentage 0-100'
        """))

        session.commit()
        print("✓ Migration completed successfully!")
        return True

    except Exception as e:
        session.rollback()
        print(f"✗ Migration failed: {str(e)}")
        return False

    finally:
        session.close()

if __name__ == '__main__':
    print("Running feature migration...")
    success = run_migration()
    exit(0 if success else 1)
