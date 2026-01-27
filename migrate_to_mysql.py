#!/usr/bin/env python3
"""
MySQL Migration Script for PythonAnywhere
==========================================
This script migrates all data from the current database (SQLite/PostgreSQL) to MySQL.

Usage:
    1. First, set up your MySQL database on PythonAnywhere
    2. Set the MYSQL_URL environment variable with your MySQL connection string
    3. Run: python migrate_to_mysql.py

The script will:
    - Connect to the source database (current DATABASE_URL)
    - Connect to the target MySQL database (MYSQL_URL)
    - Create all tables in MySQL
    - Migrate all data with proper handling of relationships
"""

import os
import sys
import json
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.base import Base
import models  # Import all models to register them


def get_source_engine():
    """Get the source database engine (current database)."""
    database_url = os.getenv('DATABASE_URL')

    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    elif not database_url:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory.db')
        database_url = f'sqlite:///{db_path}'

    if database_url.startswith('sqlite'):
        return create_engine(database_url, connect_args={"check_same_thread": False})
    return create_engine(database_url)


def get_mysql_engine():
    """Get the MySQL target database engine."""
    mysql_url = os.getenv('MYSQL_URL')

    if not mysql_url:
        print("ERROR: MYSQL_URL environment variable not set!")
        print("\nPlease set MYSQL_URL in your .env file or environment:")
        print("MYSQL_URL=mysql+pymysql://username:password@hostname/database_name")
        print("\nFor PythonAnywhere, it should look like:")
        print("MYSQL_URL=mysql+pymysql://yourusername:yourpassword@yourusername.mysql.pythonanywhere-services.com/yourusername$inventory")
        sys.exit(1)

    # Ensure we're using pymysql driver
    if mysql_url.startswith('mysql://'):
        mysql_url = mysql_url.replace('mysql://', 'mysql+pymysql://', 1)

    return create_engine(
        mysql_url,
        pool_pre_ping=True,
        pool_recycle=280,  # PythonAnywhere has 5-minute timeout
        echo=False
    )


def serialize_value(value):
    """Convert Python values to MySQL-compatible format."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    if isinstance(value, bytes):
        return value
    return value


def get_table_order(metadata):
    """
    Get tables in order respecting foreign key dependencies.
    Tables with no dependencies come first.
    """
    inspector = inspect(metadata.bind)
    tables = list(metadata.sorted_tables)
    return tables


def migrate_table(source_session, target_session, table, batch_size=500):
    """Migrate a single table from source to target."""
    table_name = table.name
    print(f"\n  Migrating table: {table_name}")

    # Get all rows from source
    try:
        result = source_session.execute(text(f"SELECT * FROM {table_name}"))
        rows = result.fetchall()
        columns = result.keys()
    except Exception as e:
        print(f"    Warning: Could not read from {table_name}: {e}")
        return 0

    if not rows:
        print(f"    No data in {table_name}")
        return 0

    print(f"    Found {len(rows)} rows")

    # Prepare column names for INSERT
    column_names = [col for col in columns]

    # Insert in batches
    migrated = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]

        for row in batch:
            # Convert row to dict with serialized values
            row_dict = {}
            for col, val in zip(column_names, row):
                row_dict[col] = serialize_value(val)

            try:
                # Build INSERT statement
                cols = ', '.join([f'`{c}`' for c in row_dict.keys()])
                placeholders = ', '.join([f':{c}' for c in row_dict.keys()])
                insert_sql = text(f"INSERT INTO `{table_name}` ({cols}) VALUES ({placeholders})")
                target_session.execute(insert_sql, row_dict)
                migrated += 1
            except Exception as e:
                # Skip duplicates or constraint violations
                if 'Duplicate' in str(e) or 'UNIQUE' in str(e):
                    continue
                print(f"    Warning: Could not insert row: {e}")
                target_session.rollback()
                continue

        target_session.commit()
        print(f"    Migrated {min(i + batch_size, len(rows))}/{len(rows)} rows...")

    print(f"    Completed: {migrated} rows migrated")
    return migrated


def export_to_json(output_file='data_export.json'):
    """Export all data to JSON for backup/review."""
    print("\n" + "="*60)
    print("EXPORTING DATA TO JSON BACKUP")
    print("="*60)

    source_engine = get_source_engine()
    SourceSession = sessionmaker(bind=source_engine)
    source_session = SourceSession()

    Base.metadata.bind = source_engine

    export_data = {}

    for table in Base.metadata.sorted_tables:
        table_name = table.name
        try:
            result = source_session.execute(text(f"SELECT * FROM {table_name}"))
            rows = result.fetchall()
            columns = list(result.keys())

            export_data[table_name] = []
            for row in rows:
                row_dict = {}
                for col, val in zip(columns, row):
                    if isinstance(val, (datetime, date)):
                        row_dict[col] = val.isoformat()
                    elif isinstance(val, Decimal):
                        row_dict[col] = float(val)
                    elif isinstance(val, bytes):
                        row_dict[col] = val.hex()
                    else:
                        row_dict[col] = val
                export_data[table_name].append(row_dict)

            print(f"  Exported {len(rows)} rows from {table_name}")
        except Exception as e:
            print(f"  Warning: Could not export {table_name}: {e}")

    source_session.close()

    with open(output_file, 'w') as f:
        json.dump(export_data, f, indent=2, default=str)

    print(f"\nData exported to: {output_file}")
    return export_data


def run_migration():
    """Run the full migration from source to MySQL."""
    print("\n" + "="*60)
    print("MySQL MIGRATION SCRIPT")
    print("="*60)

    # First, export data as backup
    export_to_json()

    print("\n" + "="*60)
    print("STARTING MIGRATION TO MYSQL")
    print("="*60)

    # Create engines
    print("\n1. Connecting to databases...")
    source_engine = get_source_engine()
    print(f"   Source: {source_engine.url}")

    target_engine = get_mysql_engine()
    print(f"   Target: {target_engine.url}")

    # Create sessions
    SourceSession = sessionmaker(bind=source_engine)
    TargetSession = sessionmaker(bind=target_engine)

    source_session = SourceSession()
    target_session = TargetSession()

    # Bind metadata to source for table inspection
    Base.metadata.bind = source_engine

    # Create all tables in MySQL
    print("\n2. Creating tables in MySQL...")
    try:
        Base.metadata.create_all(bind=target_engine)
        print("   Tables created successfully!")
    except Exception as e:
        print(f"   Error creating tables: {e}")
        sys.exit(1)

    # Disable foreign key checks for migration
    print("\n3. Disabling foreign key checks...")
    target_session.execute(text("SET FOREIGN_KEY_CHECKS=0"))
    target_session.commit()

    # Get tables in dependency order
    tables = get_table_order(Base.metadata)

    print(f"\n4. Migrating {len(tables)} tables...")

    total_migrated = 0
    for table in tables:
        migrated = migrate_table(source_session, target_session, table)
        total_migrated += migrated

    # Re-enable foreign key checks
    print("\n5. Re-enabling foreign key checks...")
    target_session.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    target_session.commit()

    # Close sessions
    source_session.close()
    target_session.close()

    print("\n" + "="*60)
    print("MIGRATION COMPLETE!")
    print("="*60)
    print(f"\nTotal rows migrated: {total_migrated}")
    print("\nNext steps:")
    print("1. Update your .env file to use MYSQL_URL as DATABASE_URL")
    print("2. Test your application with the new MySQL database")
    print("3. The JSON backup is saved in data_export.json")


def verify_migration():
    """Verify the migration by comparing row counts."""
    print("\n" + "="*60)
    print("VERIFYING MIGRATION")
    print("="*60)

    source_engine = get_source_engine()
    target_engine = get_mysql_engine()

    SourceSession = sessionmaker(bind=source_engine)
    TargetSession = sessionmaker(bind=target_engine)

    source_session = SourceSession()
    target_session = TargetSession()

    Base.metadata.bind = source_engine

    print("\nComparing row counts:\n")
    print(f"{'Table':<40} {'Source':>10} {'MySQL':>10} {'Status':>10}")
    print("-" * 72)

    all_match = True
    for table in Base.metadata.sorted_tables:
        table_name = table.name
        try:
            source_count = source_session.execute(
                text(f"SELECT COUNT(*) FROM {table_name}")
            ).scalar()
            target_count = target_session.execute(
                text(f"SELECT COUNT(*) FROM `{table_name}`")
            ).scalar()

            status = "OK" if source_count == target_count else "MISMATCH"
            if source_count != target_count:
                all_match = False

            print(f"{table_name:<40} {source_count:>10} {target_count:>10} {status:>10}")
        except Exception as e:
            print(f"{table_name:<40} {'ERROR':>10} {'ERROR':>10} {str(e)[:20]}")
            all_match = False

    source_session.close()
    target_session.close()

    if all_match:
        print("\nAll tables verified successfully!")
    else:
        print("\nSome tables have mismatched counts. Please review.")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migrate database to MySQL')
    parser.add_argument('--export-only', action='store_true',
                       help='Only export data to JSON without migrating')
    parser.add_argument('--verify', action='store_true',
                       help='Verify migration by comparing row counts')

    args = parser.parse_args()

    if args.export_only:
        export_to_json()
    elif args.verify:
        verify_migration()
    else:
        run_migration()
        verify_migration()
