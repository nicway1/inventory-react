#!/usr/bin/env python3
"""
Database Migration: Add Export Tickets Permission
Adds the can_export_tickets column to the permissions table.

Run this script to add the export tickets permission to your database.
"""

import sys
import os
import sqlite3

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_database_path():
    """Get SQLite database path from config"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Check DATABASE_URL environment variable
    database_url = os.getenv('DATABASE_URL')
    if database_url and database_url.startswith('sqlite:///'):
        return database_url.replace('sqlite:///', '')

    # Default path
    return os.path.join(base_dir, 'inventory.db')


def check_column_exists_sqlite(cursor, table_name, column_name):
    """Check if a column exists in SQLite table"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def run_migration():
    """Run the export tickets permission migration for SQLite"""

    print("=" * 70)
    print("EXPORT TICKETS PERMISSION DATABASE MIGRATION (SQLite)")
    print("=" * 70)

    db_path = get_database_path()
    print(f"Database path: {db_path}")

    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        return False

    try:
        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()

        print("Connected to SQLite database successfully")

        # Check if column already exists
        column_exists = check_column_exists_sqlite(cursor, 'permissions', 'can_export_tickets')

        if column_exists:
            print("can_export_tickets column already exists!")
            print("Migration is not needed.")
            return True

        try:
            # Add can_export_tickets column to permissions table
            print("Adding can_export_tickets column to permissions table...")
            cursor.execute("""
                ALTER TABLE permissions
                ADD COLUMN can_export_tickets BOOLEAN DEFAULT 0
            """)
            print("Added can_export_tickets column")

            # Set default values - enable for SUPER_ADMIN and DEVELOPER
            print("Setting default values...")
            cursor.execute("""
                UPDATE permissions
                SET can_export_tickets = 1
                WHERE user_type IN ('SUPER_ADMIN', 'DEVELOPER')
            """)
            print("Set can_export_tickets=True for SUPER_ADMIN and DEVELOPER")

            connection.commit()
            print("Migration completed successfully!")

            # Verify
            print("\nVerifying migration...")
            column_exists = check_column_exists_sqlite(cursor, 'permissions', 'can_export_tickets')

            if column_exists:
                print("Verified column was created successfully!")
                print("\nExport tickets permission is now available in Permission Management.")
                return True
            else:
                print("Migration verification failed")
                return False

        except Exception as e:
            connection.rollback()
            print(f"Error during migration: {e}")
            return False

    except Exception as e:
        print(f"Database connection error: {e}")
        return False

    finally:
        if 'connection' in locals():
            connection.close()
            print("Database connection closed")


if __name__ == "__main__":
    print("Export Tickets Permission Database Migration")
    print("This script will add the can_export_tickets column to the permissions table")

    response = input("\nDo you want to proceed with the migration? (y/N): ")
    if response.lower() != 'y':
        print("Migration cancelled.")
        sys.exit(0)

    success = run_migration()

    if success:
        print("\n" + "=" * 70)
        print("MIGRATION SUCCESSFUL!")
        print("=" * 70)
        sys.exit(0)
    else:
        print("\n" + "=" * 70)
        print("MIGRATION FAILED!")
        print("=" * 70)
        sys.exit(1)
