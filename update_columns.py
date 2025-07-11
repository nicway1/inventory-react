import os
import sqlite3
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def update_database_schema():
    """Add missing shipping tracking columns to tickets table"""
    try:
        # Get database path
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory.db')
        logger.info(f"Using database at: {db_path}")
        
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if columns exist
        cursor.execute("PRAGMA table_info(tickets)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Add columns if they don't exist
        if 'shipping_tracking_2' not in columns:
            logger.info("Adding shipping_tracking_2 column...")
            cursor.execute("ALTER TABLE tickets ADD COLUMN shipping_tracking_2 TEXT")
        else:
            logger.info("Column shipping_tracking_2 already exists")
        
        if 'shipping_carrier_2' not in columns:
            logger.info("Adding shipping_carrier_2 column...")
            cursor.execute("ALTER TABLE tickets ADD COLUMN shipping_carrier_2 TEXT")
        else:
            logger.info("Column shipping_carrier_2 already exists")
        
        if 'shipping_status_2' not in columns:
            logger.info("Adding shipping_status_2 column...")
            cursor.execute("ALTER TABLE tickets ADD COLUMN shipping_status_2 TEXT DEFAULT 'Pending'")
        else:
            logger.info("Column shipping_status_2 already exists")
        
        # Commit the changes
        conn.commit()
        logger.info("Database schema update complete")
        
        # Close the connection
        conn.close()
        return True
    
    except Exception as e:
        logger.error(f"Error updating database schema: {e}")
        return False

if __name__ == "__main__":
    success = update_database_schema()
    if success:
        logger.info("Schema update completed successfully")
    else:
        logger.info("Schema update failed") 