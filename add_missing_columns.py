import sqlite3
import os
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


def add_missing_columns():
    """Add missing columns to the tickets table in SQLite database"""
    conn = None
    try:
        # We now know the database file is 'inventory.db' in the root directory
        db_path = 'inventory.db'  # Use the correct path directly
        
        if os.path.exists(db_path):
            logger.info("Found database at: {db_path}")
            conn = sqlite3.connect(db_path)
        else:
            logger.info("Error: Database file {db_path} does not exist.")
            logger.info("Current working directory:", os.getcwd())
            logger.info("Available files in current directory:", sorted(os.listdir()))
            return
        
        cursor = conn.cursor()
        
        # Check if the column already exists
        cursor.execute("PRAGMA table_info(tickets)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add shipping_tracking_2 column if it doesn't exist
        if 'shipping_tracking_2' not in columns:
            logger.info("Adding shipping_tracking_2 column...")
            cursor.execute("ALTER TABLE tickets ADD COLUMN shipping_tracking_2 TEXT")
        else:
            logger.info("Column shipping_tracking_2 already exists.")
        
        # Add return_tracking column if it doesn't exist
        if 'return_tracking' not in columns:
            logger.info("Adding return_tracking column...")
            cursor.execute("ALTER TABLE tickets ADD COLUMN return_tracking TEXT")
        else:
            logger.info("Column return_tracking already exists.")
        
        # Add shipping_carrier column if it doesn't exist
        if 'shipping_carrier' not in columns:
            logger.info("Adding shipping_carrier column...")
            cursor.execute("ALTER TABLE tickets ADD COLUMN shipping_carrier TEXT")
        else:
            logger.info("Column shipping_carrier already exists.")
        
        # Add shipping_status column if it doesn't exist
        if 'shipping_status' not in columns:
            logger.info("Adding shipping_status column...")
            cursor.execute("ALTER TABLE tickets ADD COLUMN shipping_status TEXT")
        else:
            logger.info("Column shipping_status already exists.")
        
        # Add secondary_tracking_carrier column if it doesn't exist
        if 'secondary_tracking_carrier' not in columns:
            logger.info("Adding secondary_tracking_carrier column...")
            cursor.execute("ALTER TABLE tickets ADD COLUMN secondary_tracking_carrier TEXT")
        else:
            logger.info("Column secondary_tracking_carrier already exists.")
        
        # Add secondary_tracking_status column if it doesn't exist
        if 'secondary_tracking_status' not in columns:
            logger.info("Adding secondary_tracking_status column...")
            cursor.execute("ALTER TABLE tickets ADD COLUMN secondary_tracking_status TEXT")
        else:
            logger.info("Column secondary_tracking_status already exists.")
        
        # Commit the changes
        conn.commit()
        logger.info("Database updated successfully!")
        
    except Exception as e:
        logger.info("Error updating database: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    add_missing_columns() 