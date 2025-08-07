#!/usr/bin/env python3
"""
Add notifications table for user mentions and other notifications
"""

import sqlite3
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_notifications_table():
    """Add the notifications table to the database"""
    try:
        # Connect to database
        db_path = 'inventory.db'
        if not os.path.exists(db_path):
            logger.error(f"Database file {db_path} not found")
            return False
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        logger.info("Adding notifications table...")
        
        # Create notifications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type VARCHAR(50) NOT NULL,
                title VARCHAR(255) NOT NULL,
                message TEXT NOT NULL,
                is_read BOOLEAN DEFAULT 0,
                reference_type VARCHAR(50),
                reference_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                read_at DATETIME,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Create index for better performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notifications_user_id 
            ON notifications(user_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notifications_is_read 
            ON notifications(user_id, is_read)
        """)
        
        conn.commit()
        logger.info("✓ Notifications table created successfully!")
        
        # Verify the table was created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notifications'")
        if cursor.fetchone():
            logger.info("✓ Notifications table verified in database")
        else:
            logger.error("✗ Notifications table not found after creation")
            return False
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error adding notifications table: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == '__main__':
    success = add_notifications_table()
    if success:
        logger.info("Migration completed successfully!")
    else:
        logger.error("Migration failed!")
        exit(1)