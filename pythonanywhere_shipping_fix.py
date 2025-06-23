#!/usr/bin/env python3
"""
PythonAnywhere Database Migration Script
Adds missing shipping tracking columns (3, 4, 5) to the tickets table.

Run this script on PythonAnywhere to fix the "no such column: tickets.shipping_tracking_3" error.
"""
import sqlite3
import os
import sys

def fix_pythonanywhere_shipping_columns():
    """
    Add missing shipping tracking columns to PythonAnywhere database
    """
    # PythonAnywhere database path
    db_path = '/home/nicway2/inventory/inventory.db'
    
    print(f"PythonAnywhere Shipping Columns Fix")
    print(f"Looking for database at: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"Error: Database file {db_path} not found")
        print(f"Current directory: {os.getcwd()}")
        print(f"Files in current directory: {os.listdir('.')}")
        return False
    
    try:
        print(f"Opening database connection...")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current table structure
        print("Checking current tickets table structure...")
        cursor.execute("PRAGMA table_info(tickets)")
        existing_columns = {column[1]: column for column in cursor.fetchall()}
        
        print(f"Current tickets table has {len(existing_columns)} columns")
        
        # Define all shipping tracking columns that should exist
        required_columns = [
            # Package 2 (might already exist)
            ('shipping_tracking_2', 'TEXT'),
            ('shipping_carrier_2', 'TEXT'),
            ('shipping_status_2', 'TEXT DEFAULT \'Pending\''),
            # Package 3 (likely missing - this is the error column)
            ('shipping_tracking_3', 'TEXT'),
            ('shipping_carrier_3', 'TEXT'),
            ('shipping_status_3', 'TEXT DEFAULT \'Pending\''),
            # Package 4 (likely missing)
            ('shipping_tracking_4', 'TEXT'),
            ('shipping_carrier_4', 'TEXT'),
            ('shipping_status_4', 'TEXT DEFAULT \'Pending\''),
            # Package 5 (likely missing)
            ('shipping_tracking_5', 'TEXT'),
            ('shipping_carrier_5', 'TEXT'),
            ('shipping_status_5', 'TEXT DEFAULT \'Pending\''),
        ]
        
        # Find missing columns
        missing_columns = []
        for column_name, column_definition in required_columns:
            if column_name not in existing_columns:
                missing_columns.append((column_name, column_definition))
        
        if not missing_columns:
            print("✓ All shipping tracking columns already exist!")
            return True
        
        print(f"\n⚠️  Found {len(missing_columns)} missing columns:")
        for column_name, _ in missing_columns:
            print(f"   - {column_name}")
        
        # Add missing columns one by one
        print(f"\n🔧 Adding missing columns...")
        successful_additions = 0
        
        for column_name, column_definition in missing_columns:
            sql = f"ALTER TABLE tickets ADD COLUMN {column_name} {column_definition}"
            print(f"   Executing: ALTER TABLE tickets ADD COLUMN {column_name}...")
            
            try:
                cursor.execute(sql)
                print(f"   ✓ Successfully added {column_name}")
                successful_additions += 1
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print(f"   ⚠️  Column {column_name} already exists (skipping)")
                    successful_additions += 1
                else:
                    print(f"   ✗ Error adding {column_name}: {e}")
        
        # Commit changes
        if successful_additions > 0:
            conn.commit()
            print(f"\n✓ Successfully committed {successful_additions} column additions!")
        
        # Verify the fix
        print(f"\n🔍 Verifying the fix...")
        cursor.execute("PRAGMA table_info(tickets)")
        final_columns = {column[1]: column for column in cursor.fetchall()}
        
        print(f"Final tickets table has {len(final_columns)} columns")
        
        # Check if the problematic column now exists
        if 'shipping_tracking_3' in final_columns:
            print("✅ shipping_tracking_3 column now exists!")
        else:
            print("❌ shipping_tracking_3 column still missing!")
            return False
        
        return True
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if 'conn' in locals() and conn:
            conn.close()
            print("Database connection closed")

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 PythonAnywhere Shipping Tracking Columns Fix")
    print("=" * 60)
    
    success = fix_pythonanywhere_shipping_columns()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 SUCCESS! Database migration completed.")
        print("   The 'shipping_tracking_3' error should now be fixed.")
        print("   Please restart your PythonAnywhere web app.")
        sys.exit(0)
    else:
        print("💥 FAILED! Migration could not be completed.")
        print("   Please check the error messages above.")
        sys.exit(1) 