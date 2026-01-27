#!/usr/bin/env python3
"""
MySQL Migration: Add legal_hold column to assets table

This script adds the legal_hold column directly to MySQL on PythonAnywhere.
Run this on PythonAnywhere after uploading.

Run: python mysql_add_legal_hold.py
"""

import os
import sys

# Set up database URL for MySQL
os.environ['DATABASE_URL'] = 'mysql+pymysql://nicway2:truelog123%40@nicway2.mysql.pythonanywhere-services.com/nicway2$inventory'

try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    print("PyMySQL not installed. Run: pip install PyMySQL")
    sys.exit(1)

from sqlalchemy import create_engine, inspect, text

DATABASE_URL = os.environ['DATABASE_URL']


def run_migration():
    print("=" * 60)
    print("MySQL Migration: Add legal_hold column")
    print("=" * 60)

    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=280
    )

    inspector = inspect(engine)

    # Check if assets table exists
    existing_tables = inspector.get_table_names()
    if 'assets' not in existing_tables:
        print("Error: assets table does not exist")
        return False

    # Check existing columns
    asset_columns = [c['name'] for c in inspector.get_columns('assets')]
    print(f"\nExisting columns in assets: {len(asset_columns)}")

    with engine.connect() as conn:
        if 'legal_hold' not in asset_columns:
            print("\nAdding legal_hold column to assets table...")
            # MySQL syntax for adding column
            conn.execute(text("ALTER TABLE assets ADD COLUMN legal_hold TINYINT(1) DEFAULT 0"))
            conn.commit()
            print("  ✓ Added legal_hold column")
        else:
            print("\n  ✓ Column legal_hold already exists")

    # Verify
    inspector = inspect(engine)
    asset_columns = [c['name'] for c in inspector.get_columns('assets')]
    if 'legal_hold' in asset_columns:
        print("\n✓ Migration verified - legal_hold column exists")
    else:
        print("\n✗ Migration failed - legal_hold column not found")
        return False

    print("\n" + "=" * 60)
    print("Migration completed successfully!")
    print("=" * 60)
    return True


if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)
