#!/usr/bin/env python3
import sqlite3
import os
import sys
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


def fix_all_shipping_tracking_columns():
    """
    Check for and add ALL missing shipping tracking columns to the SQLite database.
    This includes columns 2, 3, 4, and 5 for multiple package tracking.
    """
    db_path = 'inventory.db'
    
    logger.info("Looking for database at: {db_path}")
    if not os.path.exists(db_path):
        logger.info("Error: Database file {db_path} not found in {os.getcwd()}")
        logger.info("Available files:", os.listdir())
        return False
    
    try:
        logger.info("Opening database connection to {db_path}...")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check table structure
        logger.info("Checking tickets table structure...")
        cursor.execute("PRAGMA table_info(tickets)")
        columns = {column[1]: column for column in cursor.fetchall()}
        
        # Print current columns for diagnosis
        logger.info("\nFound {len(columns)} columns in tickets table")
        
        # Check for missing columns - ALL shipping tracking columns 2-5
        missing_columns = []
        required_columns = [
            # Package 2
            ('shipping_tracking_2', 'TEXT'),
            ('shipping_carrier_2', 'TEXT'),
            ('shipping_status_2', 'TEXT DEFAULT \'Pending\''),
            # Package 3
            ('shipping_tracking_3', 'TEXT'),
            ('shipping_carrier_3', 'TEXT'),
            ('shipping_status_3', 'TEXT DEFAULT \'Pending\''),
            # Package 4
            ('shipping_tracking_4', 'TEXT'),
            ('shipping_carrier_4', 'TEXT'),
            ('shipping_status_4', 'TEXT DEFAULT \'Pending\''),
            # Package 5
            ('shipping_tracking_5', 'TEXT'),
            ('shipping_carrier_5', 'TEXT'),
            ('shipping_status_5', 'TEXT DEFAULT \'Pending\''),
        ]
        
        for column_name, column_definition in required_columns:
            if column_name not in columns:
                missing_columns.append((column_name, column_definition))
        
        if not missing_columns:
            logger.info("\nAll required shipping tracking columns exist. No changes needed.")
            return True
        
        logger.info("\nFound {len(missing_columns)} missing columns:")
        for column_name, column_definition in missing_columns:
            logger.info("  - {column_name}")
        
        # Add missing columns
        logger.info("\nAdding missing columns...")
        for column_name, column_definition in missing_columns:
            sql = f"ALTER TABLE tickets ADD COLUMN {column_name} {column_definition}"
            logger.info("Executing: {sql}")
            try:
                cursor.execute(sql)
                logger.info("  ✓ Added {column_name} column")
            except Exception as e:
                logger.info("  ✗ Error adding {column_name}: {e}")
        
        # Commit changes
        conn.commit()
        logger.info("\nDatabase updated successfully!")
        
        # Verify the changes
        logger.info("\nVerifying updated structure...")
        cursor.execute("PRAGMA table_info(tickets)")
        updated_columns = {column[1]: column for column in cursor.fetchall()}
        
        all_added = True
        for column_name, _ in missing_columns:
            if column_name in updated_columns:
                logger.info("  ✓ Verified {column_name} was added")
            else:
                logger.info("  ✗ Failed to add {column_name}")
                all_added = False
        
        logger.info("\nFinal tickets table has {len(updated_columns)} columns")
        return all_added
    
    except Exception as e:
        logger.info("Error updating database: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if 'conn' in locals() and conn:
            conn.close()
            logger.info("Database connection closed")

if __name__ == "__main__":
    logger.info("=== Fixing ALL Shipping Tracking Columns ===")
    logger.info("Current working directory: {os.getcwd()}")
    
    success = fix_all_shipping_tracking_columns()
    
    if success:
        logger.info("\nFix completed successfully. The application should now work correctly.")
        logger.info("You can now restart your Flask application.")
        sys.exit(0)
    else:
        logger.info("\nFailed to fix all issues. Please check the error messages above.")
        sys.exit(1) 