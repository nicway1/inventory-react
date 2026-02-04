#!/usr/bin/env python3
"""
Database Migration: Add Category Permissions
Creates the necessary table for user ticket category creation control.

Migration adds:
- user_category_permissions table: Stores which ticket categories each user can create

Run this script to add the category permission functionality to your database.
Supports both SQLite and MySQL databases.
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


def check_table_exists_sqlite(cursor, table_name):
    """Check if a table exists in SQLite database"""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cursor.fetchone() is not None


def run_migration():
    """Run the category permissions migration for SQLite"""

    print("=" * 70)
    print("CATEGORY PERMISSIONS DATABASE MIGRATION (SQLite)")
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

        # Check if table already exists
        table_exists = check_table_exists_sqlite(cursor, 'user_category_permissions')

        if table_exists:
            print("Category permissions table already exists!")
            print("Migration is not needed.")
            return True

        try:
            # Create user_category_permissions table
            print("Creating user_category_permissions table...")
            cursor.execute("""
                CREATE TABLE user_category_permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    category_key VARCHAR(100) NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            # Create indexes for performance
            cursor.execute("CREATE INDEX idx_ucp_user_id ON user_category_permissions(user_id)")
            cursor.execute("CREATE INDEX idx_ucp_category_key ON user_category_permissions(category_key)")
            print("Created user_category_permissions table with indexes")

            connection.commit()
            print("Migration completed successfully!")

            # Verify
            print("\nVerifying migration...")
            table_exists = check_table_exists_sqlite(cursor, 'user_category_permissions')

            if table_exists:
                print("Verified table was created successfully!")
                print("\nCategory permissions feature is now available.")
                print("Admins can now control which ticket categories users can create.")
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
    print("Category Permissions Database Migration")
    print("This script will add the necessary table for ticket category creation control")

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
