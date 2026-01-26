#!/usr/bin/env python3
"""
Migration: Add legal_hold column to assets table

This adds the legal_hold boolean column to the assets table for tracking
assets that are under legal hold and should not be wiped or disposed.

Run: python migrations/add_asset_legal_hold.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import inspect, text


def run_migration():
    inspector = inspect(engine)

    # Check if assets table exists
    existing_tables = inspector.get_table_names()
    if 'assets' not in existing_tables:
        print("Error: assets table does not exist")
        return False

    # Check existing columns
    asset_columns = [c['name'] for c in inspector.get_columns('assets')]

    with engine.connect() as conn:
        if 'legal_hold' not in asset_columns:
            print("Adding legal_hold column to assets table...")
            conn.execute(text("ALTER TABLE assets ADD COLUMN legal_hold BOOLEAN DEFAULT 0"))
            conn.commit()
            print("  ✓ Added legal_hold column")
        else:
            print("  - Column legal_hold already exists, skipping")

    print("\nMigration completed successfully!")
    return True


if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)
