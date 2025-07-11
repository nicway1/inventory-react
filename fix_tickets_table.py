import sqlite3
import os
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


def fix_tickets_table():
    """Add missing shipping_tracking_2 column to tickets table in SQLite database"""
    
    # Try multiple database files that might exist on PythonAnywhere
    possible_paths = [
        'inventory.db',
        '/home/nicway2/inventory/inventory.db',
        'app.db',
        '/home/nicway2/inventory/app.db',
        'instance/app.db',
        '/home/nicway2/inventory/instance/app.db',
    ]
    
    success = False
    
    for db_path in possible_paths:
        if not os.path.exists(db_path):
            logger.info("Database not found at: {db_path}")
            continue
            
        logger.info("Trying database at: {db_path}")
        conn = None
        try:
            # Connect to database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tickets'")
            if not cursor.fetchone():
                logger.info("No 'tickets' table found in {db_path}")
                continue
                
            # Check if column exists
            cursor.execute("PRAGMA table_info(tickets)")
            columns = [column[1] for column in cursor.fetchall()]
            logger.info("Existing columns in tickets table: {columns}")
            
            # Add missing column
            if 'shipping_tracking_2' not in columns:
                logger.info("Adding shipping_tracking_2 column to {db_path}...")
                cursor.execute("ALTER TABLE tickets ADD COLUMN shipping_tracking_2 TEXT")
                conn.commit()
                logger.info("Added shipping_tracking_2 column successfully!")
                success = True
            else:
                logger.info("Column shipping_tracking_2 already exists in {db_path}")
                success = True
                
            # Add return_tracking column if needed
            if 'return_tracking' not in columns:
                logger.info("Adding return_tracking column to {db_path}...")
                cursor.execute("ALTER TABLE tickets ADD COLUMN return_tracking TEXT")
                conn.commit()
                logger.info("Added return_tracking column successfully!")
            
            # Add shipping_carrier column if needed
            if 'shipping_carrier' not in columns:
                logger.info("Adding shipping_carrier column to {db_path}...")
                cursor.execute("ALTER TABLE tickets ADD COLUMN shipping_carrier TEXT")
                conn.commit()
                logger.info("Added shipping_carrier column successfully!")
            
            # Add shipping_status column if needed
            if 'shipping_status' not in columns:
                logger.info("Adding shipping_status column to {db_path}...")
                cursor.execute("ALTER TABLE tickets ADD COLUMN shipping_status TEXT")
                conn.commit()
                logger.info("Added shipping_status column successfully!")
                
            # Add secondary_tracking_carrier column if needed
            if 'secondary_tracking_carrier' not in columns:
                logger.info("Adding secondary_tracking_carrier column to {db_path}...")
                cursor.execute("ALTER TABLE tickets ADD COLUMN secondary_tracking_carrier TEXT")
                conn.commit()
                logger.info("Added secondary_tracking_carrier column successfully!")
                
            # Add secondary_tracking_status column if needed
            if 'secondary_tracking_status' not in columns:
                logger.info("Adding secondary_tracking_status column to {db_path}...")
                cursor.execute("ALTER TABLE tickets ADD COLUMN secondary_tracking_status TEXT")
                conn.commit()
                logger.info("Added secondary_tracking_status column successfully!")
            
        except Exception as e:
            logger.info("Error with database {db_path}: {str(e)}")
        finally:
            if conn:
                conn.close()
                
    if not success:
        logger.info("\nCould not find and update any database with tickets table.")
        logger.info("Current directory:", os.getcwd())
        logger.info("Files in current directory:", sorted(os.listdir()))
        if os.path.exists('instance'):
            logger.info("Files in instance directory:", sorted(os.listdir('instance')))

if __name__ == "__main__":
    fix_tickets_table() 