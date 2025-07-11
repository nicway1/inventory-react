import sys
import os
import sqlite3
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


def add_ticket_permissions():
    """Add ticket permission columns to the permissions table in the database."""
    try:
        # Connect to SQLite database
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(permissions)")
        columns = [info[1] for info in cursor.fetchall()]
        
        # Add the columns if they don't exist
        if 'can_view_tickets' not in columns:
            cursor.execute("ALTER TABLE permissions ADD COLUMN can_view_tickets BOOLEAN DEFAULT 1")
            logger.info("Added column: can_view_tickets")
            
        if 'can_edit_tickets' not in columns:
            cursor.execute("ALTER TABLE permissions ADD COLUMN can_edit_tickets BOOLEAN DEFAULT 0")
            logger.info("Added column: can_edit_tickets")
            
        if 'can_delete_tickets' not in columns:
            cursor.execute("ALTER TABLE permissions ADD COLUMN can_delete_tickets BOOLEAN DEFAULT 0")
            logger.info("Added column: can_delete_tickets")
            
        if 'can_delete_own_tickets' not in columns:
            cursor.execute("ALTER TABLE permissions ADD COLUMN can_delete_own_tickets BOOLEAN DEFAULT 0")
            logger.info("Added column: can_delete_own_tickets")
            
        if 'can_create_tickets' not in columns:
            cursor.execute("ALTER TABLE permissions ADD COLUMN can_create_tickets BOOLEAN DEFAULT 1")
            logger.info("Added column: can_create_tickets")
        
        # Set default values based on user type
        cursor.execute("UPDATE permissions SET can_view_tickets=1, can_edit_tickets=1, can_delete_tickets=1, can_delete_own_tickets=1, can_create_tickets=1 WHERE user_type='SUPER_ADMIN'")
        cursor.execute("UPDATE permissions SET can_view_tickets=1, can_edit_tickets=1, can_delete_tickets=0, can_delete_own_tickets=1, can_create_tickets=1 WHERE user_type='COUNTRY_ADMIN'")
        cursor.execute("UPDATE permissions SET can_view_tickets=1, can_edit_tickets=0, can_delete_tickets=0, can_delete_own_tickets=0, can_create_tickets=1 WHERE user_type='CLIENT'")
        cursor.execute("UPDATE permissions SET can_view_tickets=1, can_edit_tickets=1, can_delete_tickets=0, can_delete_own_tickets=1, can_create_tickets=1 WHERE user_type='SUPERVISOR'")
        
        # Commit the changes
        conn.commit()
        logger.info("Successfully updated permissions table with ticket permissions")
        
    except Exception as e:
        logger.info("Error updating database: {str(e)}")
        return False
    finally:
        conn.close()
    
    return True

if __name__ == "__main__":
    if add_ticket_permissions():
        logger.info("Database update completed successfully")
    else:
        logger.info("Database update failed")
        sys.exit(1) 