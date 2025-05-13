import os
import sys
import sqlite3
import logging

# Add the current directory to sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def migrate():
    """
    Add file_size column to ticket_attachments table
    """
    # Path to the database
    db_path = os.path.join(project_root, "inventory.db")
    
    if not os.path.exists(db_path):
        logger.error(f"Database file not found at {db_path}")
        return False
    
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the column already exists
        cursor.execute("PRAGMA table_info(ticket_attachments)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if "file_size" not in columns:
            logger.info("Adding file_size column to ticket_attachments table")
            # Add the column - in SQLite this is a separate operation
            cursor.execute("ALTER TABLE ticket_attachments ADD COLUMN file_size INTEGER")
            conn.commit()
            
            logger.info("Column added successfully, now updating existing attachments")
            
            # Calculate file sizes for existing attachments
            cursor.execute("SELECT id, file_path FROM ticket_attachments")
            attachments = cursor.fetchall()
            
            updated_count = 0
            for attachment_id, file_path in attachments:
                if file_path and os.path.exists(file_path):
                    try:
                        file_size = os.path.getsize(file_path)
                        cursor.execute(
                            "UPDATE ticket_attachments SET file_size = ? WHERE id = ?", 
                            (file_size, attachment_id)
                        )
                        updated_count += 1
                    except Exception as e:
                        logger.warning(f"Could not calculate file size for attachment {attachment_id}: {e}")
            
            # Commit the updates
            conn.commit()
            logger.info(f"Updated file size for {updated_count} out of {len(attachments)} attachments")
            logger.info("Migration completed successfully")
        else:
            logger.info("file_size column already exists in ticket_attachments table")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        # Print the full stack trace for debugging
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1) 