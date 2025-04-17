#!/usr/bin/env python
"""
Migration script to add missing columns to accessory_transactions table
"""
import sqlite3
import os
from datetime import datetime

def run_migration():
    # Connect to the database - adjust the path if needed
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'inventory.db')
    print(f"Attempting to connect to database at: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='accessory_transactions'")
    if not cursor.fetchone():
        print("Table 'accessory_transactions' does not exist. Please create it first.")
        conn.close()
        return False
    
    # Get existing columns
    cursor.execute("PRAGMA table_info(accessory_transactions)")
    existing_columns = [column[1] for column in cursor.fetchall()]
    print(f"Existing columns: {existing_columns}")
    
    # Add missing columns
    columns_to_add = {
        'user_id': 'INTEGER',
        'transaction_number': 'VARCHAR(100) NOT NULL DEFAULT ""',
        'quantity': 'INTEGER NOT NULL DEFAULT 1'
    }
    
    added_columns = []
    for column_name, column_type in columns_to_add.items():
        if column_name not in existing_columns:
            try:
                print(f"Adding column {column_name} ({column_type})...")
                cursor.execute(f"ALTER TABLE accessory_transactions ADD COLUMN {column_name} {column_type}")
                added_columns.append(column_name)
            except sqlite3.OperationalError as e:
                print(f"Error adding column {column_name}: {str(e)}")
    
    # Create indexes for better performance (if needed)
    if 'user_id' in added_columns:
        try:
            cursor.execute('CREATE INDEX idx_accessory_transaction_user_id ON accessory_transactions(user_id)')
            print("Created index for user_id")
        except sqlite3.OperationalError as e:
            print(f"Error creating index for user_id: {str(e)}")
    
    # Add foreign key constraint (SQLite doesn't support adding constraints with ALTER TABLE)
    # This is a limitation, so we're just adding the columns
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    if added_columns:
        print(f"Successfully added columns: {', '.join(added_columns)} at {datetime.now()}")
        return True
    else:
        print("No columns needed to be added.")
        return True

if __name__ == "__main__":
    run_migration() 