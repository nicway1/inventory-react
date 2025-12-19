#!/usr/bin/env python3
"""
Migration: Add queue_folders table and update queues table with folder support

Run this migration to add queue folder grouping:
    python migrations/add_queue_folders.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, SessionLocal
from models.queue_folder import QueueFolder
from models.base import Base
from sqlalchemy import inspect, text


def run_migration():
    """Create queue_folders table and add columns to queues table"""
    inspector = inspect(engine)

    # Step 1: Create queue_folders table if it doesn't exist
    if 'queue_folders' not in inspector.get_table_names():
        print("Creating queue_folders table...")
        QueueFolder.__table__.create(engine)
        print("Table queue_folders created successfully!")
    else:
        print("Table queue_folders already exists, skipping...")

    # Step 2: Add folder_id and display_order columns to queues table
    queues_columns = [col['name'] for col in inspector.get_columns('queues')]

    with engine.connect() as conn:
        # Add folder_id column
        if 'folder_id' not in queues_columns:
            print("Adding folder_id column to queues table...")
            conn.execute(text("""
                ALTER TABLE queues ADD COLUMN folder_id INTEGER
                REFERENCES queue_folders(id) ON DELETE SET NULL
            """))
            conn.commit()
            print("Column folder_id added successfully!")
        else:
            print("Column folder_id already exists, skipping...")

        # Add display_order column
        if 'display_order' not in queues_columns:
            print("Adding display_order column to queues table...")
            conn.execute(text("""
                ALTER TABLE queues ADD COLUMN display_order INTEGER DEFAULT 0
            """))
            conn.commit()
            print("Column display_order added successfully!")
        else:
            print("Column display_order already exists, skipping...")

    print("\nMigration completed successfully!")


if __name__ == '__main__':
    run_migration()
