#!/usr/bin/env python3
"""
Migration: Add return_tracking_status column to tickets table

This adds the return_tracking_status column to track the status of return shipments.

Run: python migrations/add_return_tracking_status.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import inspect, text


def run_migration():
    inspector = inspect(engine)

    # Check if tickets table exists
    existing_tables = inspector.get_table_names()
    if 'tickets' not in existing_tables:
        print("Error: tickets table does not exist")
        return False

    # Check existing columns
    ticket_columns = [c['name'] for c in inspector.get_columns('tickets')]

    with engine.connect() as conn:
        if 'return_tracking_status' not in ticket_columns:
            print("Adding return_tracking_status column to tickets table...")
            conn.execute(text("ALTER TABLE tickets ADD COLUMN return_tracking_status VARCHAR(100) DEFAULT 'Pending'"))
            conn.commit()
            print("  ✓ Added return_tracking_status column")
        else:
            print("  - Column return_tracking_status already exists, skipping")

    print("\nMigration completed successfully!")
    return True


if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)
