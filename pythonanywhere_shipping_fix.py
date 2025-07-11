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
    
    logger.info("PythonAnywhere Shipping Columns Fix")
    logger.info("Looking for database at: {db_path}")
    
    if not os.path.exists(db_path):
        logger.info("Error: Database file {db_path} not found")
        logger.info("Current directory: {os.getcwd()}")
        logger.info("Files in current directory: {os.listdir('.')}")
        return False
    
    try:
        logger.info("Opening database connection...")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current table structure
        logger.info("Checking current tickets table structure...")
        cursor.execute("PRAGMA table_info(tickets)")
        existing_columns = {column[1]: column for column in cursor.fetchall()}
        
        logger.info("Current tickets table has {len(existing_columns)} columns")
        
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
            logger.info("✓ All shipping tracking columns already exist!")
            return True
        
        logger.info("\n⚠️  Found {len(missing_columns)} missing columns:")
        for column_name, _ in missing_columns:
            logger.info("   - {column_name}")
        
        # Add missing columns one by one
        logger.info("\n🔧 Adding missing columns...")
        successful_additions = 0
        
        for column_name, column_definition in missing_columns:
            sql = f"ALTER TABLE tickets ADD COLUMN {column_name} {column_definition}"
            logger.info("   Executing: ALTER TABLE tickets ADD COLUMN {column_name}...")
            
            try:
                cursor.execute(sql)
                logger.info("   ✓ Successfully added {column_name}")
                successful_additions += 1
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    logger.info("   ⚠️  Column {column_name} already exists (skipping)")
                    successful_additions += 1
                else:
                    logger.info("   ✗ Error adding {column_name}: {e}")
        
        # Commit changes
        if successful_additions > 0:
            conn.commit()
            logger.info("\n✓ Successfully committed {successful_additions} column additions!")
        
        # Verify the fix
        logger.info("\n🔍 Verifying the fix...")
        cursor.execute("PRAGMA table_info(tickets)")
        final_columns = {column[1]: column for column in cursor.fetchall()}
        
        logger.info("Final tickets table has {len(final_columns)} columns")
        
        # Check if the problematic column now exists
        if 'shipping_tracking_3' in final_columns:
            logger.info("✅ shipping_tracking_3 column now exists!")
        else:
            logger.info("❌ shipping_tracking_3 column still missing!")
            return False
        
        return True
    
    except Exception as e:
        logger.info("❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if 'conn' in locals() and conn:
            conn.close()
            logger.info("Database connection closed")

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🚀 PythonAnywhere Shipping Tracking Columns Fix")
    logger.info("=" * 60)
    
    success = fix_pythonanywhere_shipping_columns()
    
    logger.info("\n" + "=" * 60)
    if success:
        logger.info("🎉 SUCCESS! Database migration completed.")
        logger.info("   The 'shipping_tracking_3' error should now be fixed.")
        logger.info("   Please restart your PythonAnywhere web app.")
        sys.exit(0)
    else:
        logger.info("💥 FAILED! Migration could not be completed.")
        logger.info("   Please check the error messages above.")
        sys.exit(1) 