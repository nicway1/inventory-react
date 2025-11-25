#!/usr/bin/env python3
"""
Migration script to add work_location column to developer_schedules table
"""

from sqlalchemy import create_engine, text
import os

# Get database URL from environment or use default
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///inventory.db')

def add_work_location_column():
    """Add work_location column to developer_schedules table"""
    engine = create_engine(DATABASE_URL)

    with engine.connect() as connection:
        # Check if column already exists
        try:
            result = connection.execute(text("SELECT work_location FROM developer_schedules LIMIT 1"))
            print("work_location column already exists")
            return
        except Exception:
            print("work_location column doesn't exist, adding it...")

        # Add the column
        try:
            connection.execute(text("""
                ALTER TABLE developer_schedules
                ADD COLUMN work_location VARCHAR(10) DEFAULT 'WFO'
            """))
            connection.commit()
            print("Successfully added work_location column to developer_schedules table")
        except Exception as e:
            print(f"Error adding column: {e}")
            connection.rollback()
            raise

if __name__ == '__main__':
    print("Adding work_location column to developer_schedules table...")
    add_work_location_column()
    print("Done!")
