#!/usr/bin/env python3
"""
Migration script to add accessory_aliases table for storing multiple alias names per accessory.
"""

import sqlite3
import os

def add_accessory_aliases_table():
    """Add the accessory_aliases table to the database"""

    # Get the database path
    db_path = os.path.join(os.path.dirname(__file__), 'inventory.db')

    print(f"Connecting to database at: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='accessory_aliases'
        """)

        if cursor.fetchone():
            print("✓ Table 'accessory_aliases' already exists")
            return

        # Create the accessory_aliases table
        print("Creating accessory_aliases table...")
        cursor.execute("""
            CREATE TABLE accessory_aliases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                accessory_id INTEGER NOT NULL,
                alias_name VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (accessory_id) REFERENCES accessories (id) ON DELETE CASCADE
            )
        """)

        # Create index on accessory_id for faster lookups
        cursor.execute("""
            CREATE INDEX idx_accessory_aliases_accessory_id
            ON accessory_aliases(accessory_id)
        """)

        # Create index on alias_name for search functionality
        cursor.execute("""
            CREATE INDEX idx_accessory_aliases_alias_name
            ON accessory_aliases(alias_name)
        """)

        conn.commit()
        print("✓ Successfully created accessory_aliases table")
        print("✓ Created indexes for accessory_id and alias_name")

    except sqlite3.Error as e:
        print(f"✗ Error: {e}")
        conn.rollback()
        raise

    finally:
        conn.close()

if __name__ == '__main__':
    print("=" * 60)
    print("Adding Accessory Aliases Table Migration")
    print("=" * 60)
    add_accessory_aliases_table()
    print("=" * 60)
    print("Migration completed successfully!")
    print("=" * 60)
