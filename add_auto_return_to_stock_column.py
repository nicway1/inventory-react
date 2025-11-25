#!/usr/bin/env python3
"""
Migration script to add auto_return_to_stock column to custom_ticket_statuses table
"""

from sqlalchemy import create_engine
from sqlalchemy.sql import text
import os

# Get database URL from environment or use default
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///inventory.db')

def add_auto_return_to_stock_column():
    """Add auto_return_to_stock column to custom_ticket_statuses table"""
    engine = create_engine(DATABASE_URL)

    with engine.connect() as connection:
        # Check if column already exists
        try:
            result = connection.execute(text("SELECT auto_return_to_stock FROM custom_ticket_statuses LIMIT 1"))
            print("✓ auto_return_to_stock column already exists")
            return
        except Exception:
            print("auto_return_to_stock column doesn't exist, adding it...")

        # Add the column
        try:
            connection.execute(text("""
                ALTER TABLE custom_ticket_statuses
                ADD COLUMN auto_return_to_stock BOOLEAN DEFAULT 0
            """))
            connection.commit()
            print("✓ Successfully added auto_return_to_stock column to custom_ticket_statuses table")
        except Exception as e:
            print(f"✗ Error adding column: {e}")
            connection.rollback()
            raise

if __name__ == '__main__':
    print("Adding auto_return_to_stock column to custom_ticket_statuses table...")
    add_auto_return_to_stock_column()
    print("Done!")
