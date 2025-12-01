#!/usr/bin/env python3
"""
Migration script to add missing columns to the database.
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

def add_column_if_missing(table_name, column_name, column_type):
    """Add a column to a table if it doesn't exist"""
    if check_column_exists(table_name, column_name):
        print(f"✓ Column '{column_name}' already exists in '{table_name}' table.")
        return False

    print(f"Adding '{column_name}' column to '{table_name}' table...")
    with engine.connect() as conn:
        conn.execute(text(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}'))
        conn.commit()
    print(f"✓ Successfully added '{column_name}' column to '{table_name}' table!")
    return True

def migrate():
    """Add missing columns to database tables"""

    migrations = [
        # (table_name, column_name, column_type)
        ('users', 'preferences', 'JSON'),
        ('assets', 'image_url', 'VARCHAR(500)'),
    ]

    changes_made = 0
    for table_name, column_name, column_type in migrations:
        if add_column_if_missing(table_name, column_name, column_type):
            changes_made += 1

    if changes_made == 0:
        print("\nNo migrations needed. Database is up to date!")
    else:
        print(f"\n✓ Migration complete! {changes_made} column(s) added.")

if __name__ == '__main__':
    migrate()
