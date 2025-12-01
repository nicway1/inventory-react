#!/usr/bin/env python3
"""
Migration script to add the 'preferences' column to the users table.
Run this script on PythonAnywhere to update the database schema.

Usage:
    cd ~/inventory
    source venv/bin/activate
    python migrate_add_preferences.py
"""

from database import engine
from sqlalchemy import text, inspect

def check_column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def migrate():
    """Add preferences column to users table if it doesn't exist"""

    if check_column_exists('users', 'preferences'):
        print("✓ Column 'preferences' already exists in 'users' table. No migration needed.")
        return

    print("Adding 'preferences' column to 'users' table...")

    with engine.connect() as conn:
        conn.execute(text('ALTER TABLE users ADD COLUMN preferences JSON'))
        conn.commit()

    print("✓ Successfully added 'preferences' column to 'users' table!")

if __name__ == '__main__':
    migrate()
