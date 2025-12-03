#!/usr/bin/env python3
"""
Database Migration: Add Developer Work Plans Table
Creates the table for developer weekly work plans.

Run this script to add the work plans functionality to your database.
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
    """Run the work plans migration for SQLite"""

    print("=" * 70)
    print("DEVELOPER WORK PLANS DATABASE MIGRATION (SQLite)")
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
        table_exists = check_table_exists_sqlite(cursor, 'developer_work_plans')

        if table_exists:
            print("developer_work_plans table already exists!")
            print("Migration is not needed.")
            return True

        try:
            # Create developer_work_plans table
            print("Creating developer_work_plans table...")
            cursor.execute("""
                CREATE TABLE developer_work_plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    week_start DATE NOT NULL,
                    plan_summary TEXT,
                    monday_plan TEXT,
                    tuesday_plan TEXT,
                    wednesday_plan TEXT,
                    thursday_plan TEXT,
                    friday_plan TEXT,
                    blockers TEXT,
                    notes TEXT,
                    status VARCHAR(20) DEFAULT 'draft',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME,
                    submitted_at DATETIME,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # Create indexes
            cursor.execute("CREATE INDEX idx_dwp_user_id ON developer_work_plans(user_id)")
            cursor.execute("CREATE INDEX idx_dwp_week_start ON developer_work_plans(week_start)")
            cursor.execute("CREATE UNIQUE INDEX idx_dwp_user_week ON developer_work_plans(user_id, week_start)")

            print("Created developer_work_plans table with indexes")

            connection.commit()
            print("Migration completed successfully!")

            # Verify
            print("\nVerifying migration...")
            table_exists = check_table_exists_sqlite(cursor, 'developer_work_plans')

            if table_exists:
                print("Verified table was created successfully!")
                print("\nDeveloper Work Plans feature is now available.")
                print("Developers can set their weekly work plans from the Development Console.")
                print("Super Admins can view all developers' work plans.")
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
    print("Developer Work Plans Database Migration")
    print("This script will create the developer_work_plans table")

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
