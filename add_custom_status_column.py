#!/usr/bin/env python3
"""
Migration script to add custom_status column to tickets table
"""

from sqlalchemy import create_engine, Column, String, MetaData, Table
from sqlalchemy.sql import text
import os

# Get database URL from environment or use default
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///inventory.db')

def add_custom_status_column():
    """Add custom_status column to tickets table"""
    engine = create_engine(DATABASE_URL)

    with engine.connect() as connection:
        # Check if column already exists
        try:
            result = connection.execute(text("SELECT custom_status FROM tickets LIMIT 1"))
            print("✓ custom_status column already exists")
            return
        except Exception:
            print("custom_status column doesn't exist, adding it...")

        # Add the column
        try:
            connection.execute(text("""
                ALTER TABLE tickets
                ADD COLUMN custom_status VARCHAR(100)
            """))
            connection.commit()
            print("✓ Successfully added custom_status column to tickets table")
        except Exception as e:
            print(f"✗ Error adding column: {e}")
            connection.rollback()
            raise

if __name__ == '__main__':
    print("Adding custom_status column to tickets table...")
    add_custom_status_column()
    print("Done!")
