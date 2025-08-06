#!/usr/bin/env python3
"""
Update knowledge_attachments table to allow nullable article_id
"""

import sqlite3
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_knowledge_attachments_table():
    """Update the knowledge_attachments table to allow nullable article_id"""
    try:
        # Connect to database
        db_path = 'inventory.db'
        if not os.path.exists(db_path):
            logger.error(f"Database file {db_path} not found")
            return False
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_attachments'")
        if not cursor.fetchone():
            logger.info("knowledge_attachments table doesn't exist yet, no migration needed")
            conn.close()
            return True
        
        logger.info("Updating knowledge_attachments table...")
        
        # SQLite doesn't support ALTER COLUMN directly, so we need to recreate the table
        # First, get the current table structure
        cursor.execute("PRAGMA table_info(knowledge_attachments)")
        columns = cursor.fetchall()
        logger.info(f"Current table structure: {columns}")
        
        # Create new table with nullable article_id
        cursor.execute("""
            CREATE TABLE knowledge_attachments_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER,
                filename VARCHAR(255) NOT NULL,
                original_filename VARCHAR(255) NOT NULL,
                file_path VARCHAR(500) NOT NULL,
                file_size BIGINT,
                mime_type VARCHAR(100),
                uploaded_by INTEGER NOT NULL,
                created_at DATETIME,
                FOREIGN KEY (article_id) REFERENCES knowledge_articles(id),
                FOREIGN KEY (uploaded_by) REFERENCES users(id)
            )
        """)
        
        # Copy data from old table to new table
        cursor.execute("""
            INSERT INTO knowledge_attachments_new 
            SELECT * FROM knowledge_attachments
        """)
        
        # Drop old table and rename new table
        cursor.execute("DROP TABLE knowledge_attachments")
        cursor.execute("ALTER TABLE knowledge_attachments_new RENAME TO knowledge_attachments")
        
        conn.commit()
        logger.info("✓ knowledge_attachments table updated successfully!")
        
        # Verify the change
        cursor.execute("PRAGMA table_info(knowledge_attachments)")
        new_columns = cursor.fetchall()
        logger.info(f"New table structure: {new_columns}")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error updating knowledge_attachments table: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == '__main__':
    success = update_knowledge_attachments_table()
    if success:
        logger.info("Migration completed successfully!")
    else:
        logger.error("Migration failed!")
        exit(1)