#!/usr/bin/env python3
"""
MySQL Health Check and Migration Script for PythonAnywhere

This script:
1. Tests MySQL connection
2. Verifies all tables exist
3. Adds missing columns (like legal_hold)
4. Reports database status

Run on PythonAnywhere: python mysql_health_check.py
"""

import os
import sys

# Set up database URL for MySQL
os.environ['DATABASE_URL'] = 'mysql+pymysql://nicway2:truelog123%40@nicway2.mysql.pythonanywhere-services.com/nicway2$inventory'

try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    print("ERROR: PyMySQL not installed.")
    print("Run: pip install PyMySQL")
    sys.exit(1)

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError

DATABASE_URL = os.environ['DATABASE_URL']


def test_connection():
    """Test MySQL connection."""
    print("\n1. Testing MySQL Connection...")
    try:
        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_recycle=280
        )
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        print("   ✓ MySQL connection successful")
        return engine
    except OperationalError as e:
        print(f"   ✗ MySQL connection failed: {e}")
        return None


def check_tables(engine):
    """Check all expected tables exist."""
    print("\n2. Checking Tables...")
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"   Found {len(tables)} tables")

    # Key tables to verify (using correct table names from models)
    key_tables = [
        'users', 'assets', 'tickets', 'companies', 'accessories',
        'queues', 'permissions', 'activities', 'ticket_category_configs'
    ]

    missing = []
    for table in key_tables:
        if table in tables:
            print(f"   ✓ {table}")
        else:
            print(f"   ✗ {table} - MISSING")
            missing.append(table)

    return tables, missing


def check_and_add_columns(engine):
    """Check and add missing columns."""
    print("\n3. Checking Required Columns...")
    inspector = inspect(engine)

    # Column migrations to check
    column_checks = [
        ('assets', 'legal_hold', 'TINYINT(1) DEFAULT 0'),
    ]

    with engine.connect() as conn:
        for table, column, col_type in column_checks:
            try:
                columns = [c['name'] for c in inspector.get_columns(table)]
                if column not in columns:
                    print(f"   Adding {table}.{column}...")
                    conn.execute(text(f"ALTER TABLE `{table}` ADD COLUMN `{column}` {col_type}"))
                    conn.commit()
                    print(f"   ✓ Added {table}.{column}")
                else:
                    print(f"   ✓ {table}.{column} exists")
            except Exception as e:
                print(f"   ✗ Error checking {table}.{column}: {e}")


def get_row_counts(engine):
    """Get row counts for main tables."""
    print("\n4. Row Counts...")

    tables = ['users', 'assets', 'tickets', 'companies', 'accessories', 'activities']

    with engine.connect() as conn:
        for table in tables:
            try:
                result = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`"))
                count = result.fetchone()[0]
                print(f"   {table}: {count} rows")
            except Exception as e:
                print(f"   {table}: ERROR - {e}")


def check_status_values(engine):
    """Check for truncated status values."""
    print("\n5. Checking Status Values...")

    with engine.connect() as conn:
        # Check tickets status
        try:
            result = conn.execute(text("SELECT DISTINCT status FROM tickets"))
            statuses = [row[0] for row in result.fetchall()]
            print(f"   Ticket statuses: {statuses}")

            # Check for truncated values
            truncated = [s for s in statuses if s and len(s) < 6 and s not in ['NEW', 'OPEN']]
            if truncated:
                print(f"   ⚠ Possibly truncated statuses: {truncated}")
            else:
                print("   ✓ No truncated status values found")
        except Exception as e:
            print(f"   Error checking statuses: {e}")


def main():
    print("=" * 60)
    print("MySQL Health Check for PythonAnywhere")
    print("=" * 60)
    print(f"\nDatabase: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")

    # Test connection
    engine = test_connection()
    if not engine:
        print("\n✗ Cannot proceed without database connection")
        sys.exit(1)

    # Check tables
    tables, missing_tables = check_tables(engine)

    if missing_tables:
        print(f"\n⚠ WARNING: {len(missing_tables)} key tables missing!")
        print("   You may need to re-import the mysql_dump.sql file")

    # Check and add missing columns
    check_and_add_columns(engine)

    # Get row counts
    get_row_counts(engine)

    # Check status values
    check_status_values(engine)

    print("\n" + "=" * 60)
    print("Health Check Complete")
    print("=" * 60)

    if not missing_tables:
        print("\n✓ Database appears healthy")
        print("\nNext steps:")
        print("  1. Reload the web app on PythonAnywhere")
        print("  2. Check the error log for any remaining issues")
    else:
        print("\n⚠ Issues found - please review above")


if __name__ == '__main__':
    main()
