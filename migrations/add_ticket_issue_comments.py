#!/usr/bin/env python3
"""
Database Migration: Add Ticket Issue Comments
Creates the ticket_issue_comments table for the Chatter feature on ticket issues.

Run this script to add the issue comments/chatter functionality to your database.
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
    """Run the ticket issue comments migration for SQLite"""

    print("=" * 70)
    print("TICKET ISSUE COMMENTS DATABASE MIGRATION (SQLite)")
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
        table_exists = check_table_exists_sqlite(cursor, 'ticket_issue_comments')

        if table_exists:
            print("ticket_issue_comments table already exists!")
            print("Migration is not needed.")
            return True

        try:
            # Create ticket_issue_comments table
            print("Creating ticket_issue_comments table...")
            cursor.execute("""
                CREATE TABLE ticket_issue_comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    issue_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (issue_id) REFERENCES ticket_issues(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            # Create indexes
            cursor.execute("CREATE INDEX idx_tic_issue_id ON ticket_issue_comments(issue_id)")
            cursor.execute("CREATE INDEX idx_tic_user_id ON ticket_issue_comments(user_id)")
            print("Created ticket_issue_comments table with indexes")

            connection.commit()
            print("Migration completed successfully!")

            # Verify
            print("\nVerifying migration...")
            table_exists = check_table_exists_sqlite(cursor, 'ticket_issue_comments')

            if table_exists:
                print("Verified table was created successfully!")
                print("\nChatter feature for ticket issues is now available.")
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
    print("Ticket Issue Comments Database Migration")
    print("This script will create the ticket_issue_comments table for Chatter")

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
