import os
import sqlite3
from datetime import datetime

def migrate():
    """Add file_size column to the ticket_attachments table."""
    try:
        # Connect to SQLite database
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'inventory.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(ticket_attachments)")
        columns = [info[1] for info in cursor.fetchall()]
        
        # Add the column if it doesn't exist
        if 'file_size' not in columns:
            cursor.execute("ALTER TABLE ticket_attachments ADD COLUMN file_size INTEGER DEFAULT 0")
            print("Added file_size column to ticket_attachments table")
            
            # Update existing records with file size 0
            cursor.execute("UPDATE ticket_attachments SET file_size = 0 WHERE file_size IS NULL")
            print("Updated existing records with default file size")
            
            conn.commit()
            print("Migration completed successfully")
        else:
            print("file_size column already exists in ticket_attachments table")
            
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate() 