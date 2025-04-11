import sqlite3
import sys
import os

def fix_database(db_path):
    """Directly add missing columns to the tickets table in the specified database file"""
    if not os.path.exists(db_path):
        print(f"Error: Database file {db_path} does not exist.")
        return False
    
    conn = None
    try:
        # Connect to database
        print(f"Connecting to database: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if tickets table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tickets'")
        if not cursor.fetchone():
            print(f"Error: No 'tickets' table found in {db_path}")
            return False
        
        # Get column information
        cursor.execute("PRAGMA table_info(tickets)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"Existing columns in tickets table: {columns}")
        
        # Add all required columns
        columns_to_add = [
            'shipping_tracking_2',
            'return_tracking',
            'shipping_carrier',
            'shipping_status',
            'secondary_tracking_carrier',
            'secondary_tracking_status'
        ]
        
        for column in columns_to_add:
            if column not in columns:
                print(f"Adding {column} column...")
                cursor.execute(f"ALTER TABLE tickets ADD COLUMN {column} TEXT")
                conn.commit()
                print(f"Added {column} column successfully!")
            else:
                print(f"Column {column} already exists.")
        
        print("Database update completed successfully!")
        return True
    
    except Exception as e:
        print(f"Error updating database: {e}")
        return False
    
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python direct_db_fix.py <path_to_database_file>")
        print("\nExample:")
        print("  python direct_db_fix.py inventory.db")
        print("  python direct_db_fix.py /home/nicway2/inventory/inventory.db")
        
        # Try to find databases in standard locations
        possible_paths = [
            'inventory.db',
            '/home/nicway2/inventory/inventory.db',
            'app.db',
            '/home/nicway2/inventory/app.db',
            'instance/app.db',
            '/home/nicway2/inventory/instance/app.db',
        ]
        
        print("\nTrying to automatically locate database files:")
        for path in possible_paths:
            if os.path.exists(path):
                print(f"Found database at: {path}")
                print(f"Run: python direct_db_fix.py {path}")
        
        sys.exit(1)
    
    db_path = sys.argv[1]
    fix_database(db_path) 