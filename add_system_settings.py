#!/usr/bin/env python3
"""
Create system_settings table and add initial settings
"""
import sqlite3
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_system_settings_table():
    """Create system_settings table and add initial settings"""
    db_path = os.path.join(os.path.dirname(__file__), 'inventory.db')

    if not os.path.exists(db_path):
        logger.error(f"Database not found at {db_path}")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if table already exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='system_settings'")
        if cursor.fetchone():
            logger.info("system_settings table already exists")
        else:
            # Create the table
            logger.info("Creating system_settings table...")
            cursor.execute("""
                CREATE TABLE system_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setting_key VARCHAR(100) UNIQUE NOT NULL,
                    setting_value VARCHAR(500),
                    setting_type VARCHAR(20) DEFAULT 'string',
                    description VARCHAR(500)
                )
            """)
            logger.info("✓ Created system_settings table")

        # Check if show_queue_cards setting exists
        cursor.execute("SELECT * FROM system_settings WHERE setting_key = 'show_queue_cards'")
        if cursor.fetchone():
            logger.info("show_queue_cards setting already exists")
        else:
            # Add the initial setting (default hidden)
            logger.info("Adding show_queue_cards setting...")
            cursor.execute("""
                INSERT INTO system_settings (setting_key, setting_value, setting_type, description)
                VALUES (?, ?, ?, ?)
            """, ('show_queue_cards', 'false', 'boolean', 'Show queue cards on tickets list page'))
            logger.info("✓ Added show_queue_cards setting (default: hidden)")

        conn.commit()
        logger.info("✓ Migration completed successfully")

        conn.close()
        return True

    except Exception as e:
        logger.error(f"Error in migration: {str(e)}")
        if 'conn' in locals():
            conn.close()
        return False

if __name__ == '__main__':
    logger.info("Starting migration: Create system_settings table")
    success = create_system_settings_table()
    if success:
        logger.info("Migration completed successfully!")
    else:
        logger.error("Migration failed!")
