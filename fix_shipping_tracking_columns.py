#!/usr/bin/env python3
import sqlite3
import os
import sys

def fix_shipping_tracking_columns():
    """
    Check for and add missing shipping tracking columns to the SQLite database.
    Specifically addresses the missing shipping_carrier_2 column issue.
    """
    db_path = 'inventory.db'
    
    print(f"Looking for database at: {db_path}")
    if not os.path.exists(db_path):
        print(f"Error: Database file {db_path} not found in {os.getcwd()}")
        print("Available files:", os.listdir())
        return False
    
    try:
        print(f"Opening database connection to {db_path}...")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check table structure
        print("Checking tickets table structure...")
        cursor.execute("PRAGMA table_info(tickets)")
        columns = {column[1]: column for column in cursor.fetchall()}
        
        # Print current columns for diagnosis
        print("\nCurrent tickets table columns:")
        for column_name, column_info in columns.items():
            print(f"  - {column_name} ({column_info[2]})")
        
        # Check for missing columns
        missing_columns = []
        required_columns = [
            ('shipping_tracking_2', 'TEXT'),
            ('shipping_carrier_2', 'TEXT'),
            ('shipping_status_2', 'TEXT')
        ]
        
        for column_name, column_type in required_columns:
            if column_name not in columns:
                missing_columns.append((column_name, column_type))
        
        if not missing_columns:
            print("\nAll required columns exist. No changes needed.")
            return True
        
        print(f"\nFound {len(missing_columns)} missing columns:")
        for column_name, column_type in missing_columns:
            print(f"  - {column_name} ({column_type})")
        
        # Add missing columns
        print("\nAdding missing columns...")
        for column_name, column_type in missing_columns:
            sql = f"ALTER TABLE tickets ADD COLUMN {column_name} {column_type}"
            print(f"Executing: {sql}")
            try:
                cursor.execute(sql)
                print(f"  ✓ Added {column_name} column")
            except Exception as e:
                print(f"  ✗ Error adding {column_name}: {e}")
        
        # Commit changes
        conn.commit()
        print("\nDatabase updated successfully!")
        
        # Verify the changes
        print("\nVerifying updated structure...")
        cursor.execute("PRAGMA table_info(tickets)")
        updated_columns = {column[1]: column for column in cursor.fetchall()}
        
        all_added = True
        for column_name, _ in missing_columns:
            if column_name in updated_columns:
                print(f"  ✓ Verified {column_name} was added")
            else:
                print(f"  ✗ Failed to add {column_name}")
                all_added = False
        
        return all_added
    
    except Exception as e:
        print(f"Error updating database: {e}")
        return False
    
    finally:
        if 'conn' in locals() and conn:
            conn.close()
            print("Database connection closed")

if __name__ == "__main__":
    print("=== Fixing Shipping Tracking Columns ===")
    print(f"Current working directory: {os.getcwd()}")
    
    success = fix_shipping_tracking_columns()
    
    if success:
        print("\nFix completed successfully. The application should now work correctly.")
        sys.exit(0)
    else:
        print("\nFailed to fix all issues. Please check the error messages above.")
        sys.exit(1) 