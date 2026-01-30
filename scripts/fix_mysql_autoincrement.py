#!/usr/bin/env python3
"""
Fix MySQL auto-increment issues for tables that were migrated from SQLite.

Run this script on your MySQL server to fix tables where the primary key
doesn't have AUTO_INCREMENT set properly.

Usage:
    python fix_mysql_autoincrement.py
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

def fix_auto_increment():
    """Fix auto-increment on all tables that need it."""

    database_url = os.environ.get('DATABASE_URL')

    if not database_url or 'mysql' not in database_url:
        print("ERROR: This script is only for MySQL databases.")
        print(f"Current DATABASE_URL: {database_url[:50]}..." if database_url else "DATABASE_URL not set")
        return False

    print(f"Connecting to MySQL database...")
    engine = create_engine(database_url)

    # Tables that should have auto-increment on their 'id' column
    tables_to_fix = [
        'api_usage',
        'user_sessions',
        'users',
        'tickets',
        'assets',
        'accessories',
        'queues',
        'companies',
        'packages',
        'intake_tickets',
        'intake_attachments',
        'ticket_attachments',
        'ticket_comments',
        'ticket_history',
        'service_records',
        'features',
        'bugs',
        'releases',
        'weekly_meetings',
        'action_items',
        'device_specs',
        'api_keys',
    ]

    with engine.connect() as conn:
        # Get database name
        result = conn.execute(text("SELECT DATABASE()"))
        db_name = result.scalar()
        print(f"Database: {db_name}\n")

        fixed_count = 0
        error_count = 0

        for table in tables_to_fix:
            try:
                # Check if table exists
                result = conn.execute(text(f"""
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_schema = :db AND table_name = :table
                """), {"db": db_name, "table": table})

                if result.scalar() == 0:
                    print(f"  SKIP: {table} (table doesn't exist)")
                    continue

                # Check if id column has auto_increment
                result = conn.execute(text(f"""
                    SELECT EXTRA FROM information_schema.columns
                    WHERE table_schema = :db
                    AND table_name = :table
                    AND column_name = 'id'
                """), {"db": db_name, "table": table})

                extra = result.scalar()

                if extra and 'auto_increment' in extra.lower():
                    print(f"  OK: {table} (already has AUTO_INCREMENT)")
                    continue

                # Delete any rows with id=0 first
                result = conn.execute(text(f"SELECT COUNT(*) FROM `{table}` WHERE id = 0"))
                zero_count = result.scalar()

                if zero_count > 0:
                    print(f"  Deleting {zero_count} rows with id=0 from {table}...")
                    conn.execute(text(f"DELETE FROM `{table}` WHERE id = 0"))
                    conn.commit()

                # Get max id to set auto_increment start value
                result = conn.execute(text(f"SELECT COALESCE(MAX(id), 0) FROM `{table}`"))
                max_id = result.scalar() or 0

                # Fix the auto_increment
                print(f"  FIXING: {table}...")
                conn.execute(text(f"ALTER TABLE `{table}` MODIFY id INT NOT NULL AUTO_INCREMENT"))
                conn.commit()

                # Set auto_increment to max_id + 1 if there are existing rows
                if max_id > 0:
                    conn.execute(text(f"ALTER TABLE `{table}` AUTO_INCREMENT = {max_id + 1}"))
                    conn.commit()

                print(f"  FIXED: {table} (AUTO_INCREMENT set, starting from {max_id + 1})")
                fixed_count += 1

            except Exception as e:
                print(f"  ERROR: {table} - {str(e)}")
                error_count += 1
                continue

        print(f"\n{'='*50}")
        print(f"Summary: {fixed_count} tables fixed, {error_count} errors")

        if error_count > 0:
            print("\nSome tables had errors. You may need to fix them manually.")
            return False

        return True


if __name__ == '__main__':
    print("MySQL Auto-Increment Fix Script")
    print("=" * 50)

    success = fix_auto_increment()

    if success:
        print("\nAll tables fixed successfully!")
    else:
        print("\nScript completed with some issues.")

    sys.exit(0 if success else 1)
