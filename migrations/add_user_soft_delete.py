#!/usr/bin/env python3
"""
Database Migration: Add User Soft Delete Columns
Adds is_deleted and deleted_at columns to the users table for soft delete functionality.

Run this script to add the soft delete columns to your database.
"""

import sys
import os
import sqlite3

# Add the parent directory to the path to import models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_database_path():
    """Get SQLite database path from config"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Check DATABASE_URL environment variable
    database_url = os.getenv('DATABASE_URL')
    if database_url and database_url.startswith('sqlite:///'):
        return database_url.replace('sqlite:///', '')

    # Default path - same as database.py
    return os.path.join(base_dir, 'inventory.db')


def check_column_exists_sqlite(cursor, table_name, column_name):
    """Check if a column exists in SQLite table"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def run_migration():
    """Run the user soft delete migration for SQLite"""

    print("=" * 70)
    print("USER SOFT DELETE DATABASE MIGRATION (SQLite)")
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

        # Check if columns already exist
        is_deleted_exists = check_column_exists_sqlite(cursor, 'users', 'is_deleted')
        deleted_at_exists = check_column_exists_sqlite(cursor, 'users', 'deleted_at')

        if is_deleted_exists and deleted_at_exists:
            print("All soft delete columns already exist!")
            print("Migration is not needed.")
            return True

        try:
            # Add is_deleted column
            if not is_deleted_exists:
                print("Adding is_deleted column to users table...")
                cursor.execute("""
                    ALTER TABLE users
                    ADD COLUMN is_deleted BOOLEAN DEFAULT 0
                """)
                print("Added is_deleted column")

            # Add deleted_at column
            if not deleted_at_exists:
                print("Adding deleted_at column to users table...")
                cursor.execute("""
                    ALTER TABLE users
                    ADD COLUMN deleted_at DATETIME
                """)
                print("Added deleted_at column")

            connection.commit()
            print("Migration completed successfully!")

            # Verify
            print("\nVerifying migration...")
            is_deleted_exists = check_column_exists_sqlite(cursor, 'users', 'is_deleted')
            deleted_at_exists = check_column_exists_sqlite(cursor, 'users', 'deleted_at')

            if is_deleted_exists and deleted_at_exists:
                print("Verified all columns were created successfully!")
                print("\nSoft delete feature for users is now available.")
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
    print("User Soft Delete Database Migration")
    print("This script will add is_deleted and deleted_at columns to users table")

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
