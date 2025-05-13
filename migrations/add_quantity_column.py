#!/usr/bin/env python
"""
Migration script to add quantity column to accessory_transactions table
"""
import sqlite3
import os
from datetime import datetime

def run_migration():
    # Get the database path - adjust if your database is in a different location
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'inventory.db')
    print(f"Attempting to connect to database at: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='accessory_transactions'")
        if not cursor.fetchone():
            print("Table 'accessory_transactions' does not exist. Please create it first.")
            return False
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(accessory_transactions)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'quantity' not in columns:
            print("Adding quantity column...")
            cursor.execute('''
                ALTER TABLE accessory_transactions 
                ADD COLUMN quantity INTEGER DEFAULT 1
            ''')
            print("Successfully added quantity column")
        else:
            print("quantity column already exists")
            
        conn.commit()
        print("Migration completed successfully")
        return True
        
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    run_migration() 