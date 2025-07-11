"""
Migration script to add user_id column to asset_transactions table
Run this script directly on PythonAnywhere to fix the missing column error
"""

import sqlite3
import os

def add_user_id_column():
    # Change this to your database path on PythonAnywhere if needed
    db_path = "inventory.db"
    
    # Check if database exists
    if not os.path.exists(db_path):
        logger.info("Error: Database not found at {db_path}")
        return False
    
    # Connect to database
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the column already exists
        cursor.execute("PRAGMA table_info(asset_transactions)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if "user_id" in columns:
            logger.info("Column user_id already exists in asset_transactions table")
            return True
        
        # Add the user_id column
        logger.info("Adding user_id column to asset_transactions table...")
        cursor.execute("ALTER TABLE asset_transactions ADD COLUMN user_id INTEGER REFERENCES users(id)")
        
        conn.commit()
        logger.info("Successfully added user_id column")
        return True
        
    except sqlite3.Error as e:
        logger.info("SQLite error: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    logger.info("==== Adding user_id column to asset_transactions table ====")
    
    if add_user_id_column():
        logger.info("\nSuccessfully added user_id column to asset_transactions table")
        logger.info("Please restart your web application for the changes to take effect")
    else:
        logger.info("\nFailed to add user_id column. You may need to check the database connection or permissions.") 