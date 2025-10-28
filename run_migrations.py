#!/usr/bin/env python3
"""
Simple migration runner for SQLite database
Run this script to apply all pending migrations
"""

import sqlite3
import os
import sys
from pathlib import Path

def get_db_path():
    """Get the SQLite database path"""
    # Check if DATABASE_URL is set
    db_url = os.environ.get('DATABASE_URL', '')
    if db_url and db_url.startswith('sqlite:///'):
        return db_url.replace('sqlite:///', '')

    # Default to inventory.db in current directory
    return 'inventory.db'

def run_migration(db_path, migration_file):
    """Run a single migration file"""
    try:
        with open(migration_file, 'r') as f:
            sql = f.read()

        # Split on semicolons and filter out empty statements
        statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        for statement in statements:
            # Skip comment-only lines
            if statement.strip().startswith('--'):
                continue

            try:
                cursor.execute(statement)
            except sqlite3.OperationalError as e:
                # Ignore "duplicate column" or "table already exists" errors
                if 'duplicate column' in str(e).lower() or 'already exists' in str(e).lower():
                    print(f"  ⊳ Skipping (already applied): {statement[:50]}...")
                    continue
                else:
                    raise

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        print(f"  ✗ Failed: {str(e)}")
        return False

def main():
    """Run all migrations in the migrations directory"""
    print("=" * 60)
    print("Running Database Migrations")
    print("=" * 60)

    # Get database path
    db_path = get_db_path()
    print(f"\nDatabase: {db_path}")

    if not os.path.exists(db_path):
        print(f"✗ Database file not found: {db_path}")
        print("  Creating new database...")

    # Get migrations directory
    migrations_dir = Path(__file__).parent / 'migrations'

    if not migrations_dir.exists():
        print(f"✗ Migrations directory not found: {migrations_dir}")
        return 1

    # Get all .sql files in migrations directory
    migration_files = sorted(migrations_dir.glob('*.sql'))

    if not migration_files:
        print("✓ No migration files found")
        return 0

    print(f"\nFound {len(migration_files)} migration file(s):\n")

    # Run each migration
    success_count = 0
    for migration_file in migration_files:
        print(f"→ Running: {migration_file.name}")
        if run_migration(db_path, migration_file):
            print(f"  ✓ Success")
            success_count += 1
        else:
            print(f"  ✗ Failed")

    print("\n" + "=" * 60)
    print(f"Completed: {success_count}/{len(migration_files)} migrations applied")
    print("=" * 60)

    return 0 if success_count == len(migration_files) else 1

if __name__ == '__main__':
    sys.exit(main())
