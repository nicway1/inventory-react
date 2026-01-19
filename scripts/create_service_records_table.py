#!/usr/bin/env python3
"""
Script to create/update the service_records table for tracking services on assets.

Run this script once to create the table:
    python scripts/create_service_records_table.py
"""

import sys
import os

# Add the parent directory to the path so we can import from the app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, SessionLocal
from sqlalchemy import text


def create_service_records_table():
    """Create the service_records table if it doesn't exist."""

    create_table_sql = """
    CREATE TABLE IF NOT EXISTS service_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER NOT NULL,
        asset_id INTEGER,
        service_type VARCHAR(100) NOT NULL,
        description TEXT,
        status VARCHAR(50) DEFAULT 'Requested',
        requested_by_id INTEGER NOT NULL,
        completed_by_id INTEGER,
        completed_at DATETIME,
        performed_by_id INTEGER,
        performed_at DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (ticket_id) REFERENCES tickets(id),
        FOREIGN KEY (asset_id) REFERENCES assets(id),
        FOREIGN KEY (requested_by_id) REFERENCES users(id),
        FOREIGN KEY (completed_by_id) REFERENCES users(id),
        FOREIGN KEY (performed_by_id) REFERENCES users(id)
    )
    """

    # Create indexes for faster lookups
    create_indexes = [
        "CREATE INDEX IF NOT EXISTS idx_service_records_ticket_id ON service_records(ticket_id)",
        "CREATE INDEX IF NOT EXISTS idx_service_records_asset_id ON service_records(asset_id)",
        "CREATE INDEX IF NOT EXISTS idx_service_records_requested_by ON service_records(requested_by_id)",
        "CREATE INDEX IF NOT EXISTS idx_service_records_status ON service_records(status)"
    ]

    db_session = SessionLocal()
    try:
        # Check if table already exists
        result = db_session.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='service_records'"
        ))
        table_exists = result.fetchone() is not None

        if table_exists:
            print("Table 'service_records' already exists. Checking for missing columns...")

            # Get existing columns
            columns_result = db_session.execute(text("PRAGMA table_info(service_records)"))
            existing_columns = {row[1] for row in columns_result.fetchall()}

            # Add missing columns if needed
            new_columns = {
                'status': "ALTER TABLE service_records ADD COLUMN status VARCHAR(50) DEFAULT 'Requested'",
                'requested_by_id': "ALTER TABLE service_records ADD COLUMN requested_by_id INTEGER",
                'completed_by_id': "ALTER TABLE service_records ADD COLUMN completed_by_id INTEGER",
                'completed_at': "ALTER TABLE service_records ADD COLUMN completed_at DATETIME"
            }

            for col_name, alter_sql in new_columns.items():
                if col_name not in existing_columns:
                    print(f"Adding column '{col_name}'...")
                    try:
                        db_session.execute(text(alter_sql))
                        db_session.commit()
                        print(f"  Added column '{col_name}'")
                    except Exception as e:
                        print(f"  Warning: Could not add column '{col_name}': {e}")

            # If requested_by_id was just added and is NULL, copy from performed_by_id
            if 'requested_by_id' not in existing_columns:
                print("Migrating performed_by_id to requested_by_id...")
                try:
                    db_session.execute(text(
                        "UPDATE service_records SET requested_by_id = performed_by_id WHERE requested_by_id IS NULL"
                    ))
                    db_session.commit()
                    print("  Migration complete")
                except Exception as e:
                    print(f"  Warning: Migration failed: {e}")

            return True

        # Create the table
        db_session.execute(text(create_table_sql))
        db_session.commit()
        print("Created table 'service_records'")

        # Create indexes
        for index_sql in create_indexes:
            db_session.execute(text(index_sql))
        db_session.commit()
        print("Created indexes on 'service_records'")

        return True

    except Exception as e:
        print(f"Error: {str(e)}")
        db_session.rollback()
        return False
    finally:
        db_session.close()


if __name__ == '__main__':
    print("Creating/updating service_records table...")
    success = create_service_records_table()
    if success:
        print("Done!")
    else:
        print("Failed.")
        sys.exit(1)
