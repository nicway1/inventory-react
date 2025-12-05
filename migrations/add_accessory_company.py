#!/usr/bin/env python3
"""
Migration script to add company_id column to accessories table.
Run: python migrations/add_accessory_company.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from utils.db_manager import DatabaseManager

def run_migration():
    db = DatabaseManager()
    session = db.get_session()

    print("Adding company_id column to accessories table...")

    try:
        # Check if column already exists
        result = session.execute(text("PRAGMA table_info(accessories)"))
        columns = [row[1] for row in result.fetchall()]

        if 'company_id' in columns:
            print("Column 'company_id' already exists. Skipping.")
        else:
            # Add the column
            session.execute(text("""
                ALTER TABLE accessories
                ADD COLUMN company_id INTEGER REFERENCES companies(id)
            """))
            session.commit()
            print("Column 'company_id' added successfully!")

    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
    finally:
        session.close()

    print("Migration complete!")

if __name__ == '__main__':
    run_migration()
