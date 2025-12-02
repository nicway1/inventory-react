#!/usr/bin/env python3
"""
Database Migration: Add Mention Permissions
Creates the necessary table and column for user @mention visibility control.

Migration adds:
- user_mention_permissions table: Stores which users/groups each user can see in @mention
- mention_filter_enabled column on users table: Boolean to enable/disable filtering

Run this script to add the mention permission functionality to your database.
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


def check_column_exists_sqlite(cursor, table_name, column_name):
    """Check if a column exists in SQLite table"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def run_migration():
    """Run the mention permissions migration for SQLite"""

    print("=" * 70)
    print("MENTION PERMISSIONS DATABASE MIGRATION (SQLite)")
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
        table_exists = check_table_exists_sqlite(cursor, 'user_mention_permissions')
        column_exists = check_column_exists_sqlite(cursor, 'users', 'mention_filter_enabled')

        if table_exists and column_exists:
            print("All mention permission objects already exist!")
            print("Migration is not needed.")
            return True

        try:
            # Add mention_filter_enabled column to users table
            if not column_exists:
                print("Adding mention_filter_enabled column to users table...")
                cursor.execute("""
                    ALTER TABLE users
                    ADD COLUMN mention_filter_enabled BOOLEAN DEFAULT 0
                """)
                print("Added mention_filter_enabled column")

            # Create user_mention_permissions table
            if not table_exists:
                print("Creating user_mention_permissions table...")
                cursor.execute("""
                    CREATE TABLE user_mention_permissions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        target_type VARCHAR(20) NOT NULL,
                        target_id INTEGER NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                """)
                # Create indexes
                cursor.execute("CREATE INDEX idx_ump_user_id ON user_mention_permissions(user_id)")
                cursor.execute("CREATE INDEX idx_ump_target ON user_mention_permissions(target_type, target_id)")
                print("Created user_mention_permissions table with indexes")

            connection.commit()
            print("Migration completed successfully!")

            # Verify
            print("\nVerifying migration...")
            table_exists = check_table_exists_sqlite(cursor, 'user_mention_permissions')
            column_exists = check_column_exists_sqlite(cursor, 'users', 'mention_filter_enabled')

            if table_exists and column_exists:
                print("Verified all objects were created successfully!")
                print("\nMention permissions feature is now available.")
                print("Users can now have filtered @mention suggestions in the edit user page.")
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
    print("Mention Permissions Database Migration")
    print("This script will add the necessary table and column for @mention visibility control")

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
