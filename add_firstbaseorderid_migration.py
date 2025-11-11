#!/usr/bin/env python3
"""
Migration script to add firstbaseorderid column to tickets table
"""

import sqlite3
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def migrate_database():
    """Add firstbaseorderid column to tickets table"""
    
    db_path = "inventory.db"
    
    if not os.path.exists(db_path):
        logger.info("Database file not found. Skipping migration.")
        return
    
    logger.info("🔄 Starting firstbaseorderid migration...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(tickets)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'firstbaseorderid' in columns:
            logger.info("✅ firstbaseorderid column already exists. Migration skipped.")
            return
        
        # Add the column
        cursor.execute("ALTER TABLE tickets ADD COLUMN firstbaseorderid VARCHAR(100)")
        
        logger.info("✅ Successfully added firstbaseorderid column to tickets table")
        
        # Create index for better query performance on duplicate checking
        try:
            cursor.execute("CREATE INDEX idx_tickets_firstbaseorderid ON tickets(firstbaseorderid)")
            logger.info("✅ Successfully created index on firstbaseorderid column")
        except Exception as e:
            logger.info(f"⚠️ Index creation failed (may already exist): {e}")
        
        conn.commit()
        logger.info("✅ Migration completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()


