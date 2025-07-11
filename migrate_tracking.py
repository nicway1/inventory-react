"""
Script to migrate the tracking history table manually
"""
import sqlite3
import os
from sqlalchemy import create_engine

def create_tracking_history_table():
    # Get the database path from environment variable or use the default
    db_path = os.environ.get('DATABASE_PATH', 'inventory.db')
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if the table already exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tracking_history'")
    if cursor.fetchone():
        logger.info("Table 'tracking_history' already exists, skipping creation")
        conn.close()
        return

    # Create the tracking_history table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tracking_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tracking_number VARCHAR(100) NOT NULL,
        carrier VARCHAR(50),
        status VARCHAR(100),
        last_updated TIMESTAMP,
        tracking_data TEXT,
        ticket_id INTEGER,
        tracking_type VARCHAR(20) DEFAULT 'primary',
        FOREIGN KEY (ticket_id) REFERENCES tickets (id) ON DELETE CASCADE
    )
    ''')
    
    # Create index for faster lookups
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS ix_tracking_history_tracking_number 
    ON tracking_history (tracking_number)
    ''')
    
    # Commit changes and close connection
    conn.commit()
    logger.info("Successfully created 'tracking_history' table")
    conn.close()

if __name__ == "__main__":
    create_tracking_history_table()
    logger.info("Migration completed successfully") 