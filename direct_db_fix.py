import sqlite3
import sys
import os
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


def fix_database(db_path):
    """Directly add missing columns to the tickets table in the specified database file"""
    if not os.path.exists(db_path):
        logger.info("Error: Database file {db_path} does not exist.")
        return False
    
    conn = None
    try:
        # Connect to database
        logger.info("Connecting to database: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if tickets table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tickets'")
        if not cursor.fetchone():
            logger.info("Error: No 'tickets' table found in {db_path}")
            return False
        
        # Get column information
        cursor.execute("PRAGMA table_info(tickets)")
        columns = [column[1] for column in cursor.fetchall()]
        logger.info("Existing columns in tickets table: {columns}")
        
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
                logger.info("Adding {column} column...")
                cursor.execute(f"ALTER TABLE tickets ADD COLUMN {column} TEXT")
                conn.commit()
                logger.info("Added {column} column successfully!")
            else:
                logger.info("Column {column} already exists.")
        
        logger.info("Database update completed successfully!")
        return True
    
    except Exception as e:
        logger.info("Error updating database: {e}")
        return False
    
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.info("Usage: python direct_db_fix.py <path_to_database_file>")
        logger.info("\nExample:")
        logger.info("  python direct_db_fix.py inventory.db")
        logger.info("  python direct_db_fix.py /home/nicway2/inventory/inventory.db")
        
        # Try to find databases in standard locations
        possible_paths = [
            'inventory.db',
            '/home/nicway2/inventory/inventory.db',
            'app.db',
            '/home/nicway2/inventory/app.db',
            'instance/app.db',
            '/home/nicway2/inventory/instance/app.db',
        ]
        
        logger.info("\nTrying to automatically locate database files:")
        for path in possible_paths:
            if os.path.exists(path):
                logger.info("Found database at: {path}")
                logger.info("Run: python direct_db_fix.py {path}")
        
        sys.exit(1)
    
    db_path = sys.argv[1]
    fix_database(db_path) 