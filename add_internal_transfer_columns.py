#!/usr/bin/env python3
"""
Migration script to add Internal Transfer fields to tickets table
"""

from sqlalchemy import create_engine
from sqlalchemy.sql import text
import os

# Get database URL from environment or use default
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///inventory.db')

def add_internal_transfer_columns():
    """Add Internal Transfer columns to tickets table"""
    engine = create_engine(DATABASE_URL)

    columns_to_add = [
        ('offboarding_customer_id', 'INTEGER'),
        ('onboarding_customer_id', 'INTEGER'),
        ('offboarding_details', 'TEXT'),
        ('offboarding_address', 'VARCHAR(500)'),
        ('onboarding_address', 'VARCHAR(500)')
    ]

    with engine.connect() as connection:
        for column_name, column_type in columns_to_add:
            # Check if column already exists
            try:
                result = connection.execute(text(f"SELECT {column_name} FROM tickets LIMIT 1"))
                print(f"✓ {column_name} column already exists")
            except Exception:
                # Column doesn't exist, add it
                print(f"Adding {column_name} column...")
                try:
                    connection.execute(text(f"""
                        ALTER TABLE tickets
                        ADD COLUMN {column_name} {column_type}
                    """))
                    connection.commit()
                    print(f"✓ Successfully added {column_name} column")
                except Exception as e:
                    print(f"✗ Error adding {column_name}: {e}")
                    connection.rollback()
                    raise

if __name__ == '__main__':
    print("Adding Internal Transfer columns to tickets table...")
    add_internal_transfer_columns()
    print("Done!")
