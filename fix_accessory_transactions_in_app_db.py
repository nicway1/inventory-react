#!/usr/bin/env python
"""
Script to create the accessory_transactions table in the application's database
"""
import sqlite3
import os
from datetime import datetime

def run_migration():
    # Connect to the application's database
    db_path = os.path.join('/home/nicway2/inventory', 'inventory.db')
    logger.info("Connecting to application database at: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if table already exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='accessory_transactions'")
    if cursor.fetchone():
        logger.info("Table 'accessory_transactions' already exists, checking columns...")
        
        # Check for required columns
        cursor.execute("PRAGMA table_info(accessory_transactions)")
        columns = {column[1]: column[2] for column in cursor.fetchall()}
        logger.info("Existing columns: {list(columns.keys())}")
        
        # Add missing columns if needed
        required_columns = {
            'user_id': 'INTEGER',
            'transaction_number': 'VARCHAR(100)',
            'quantity': 'INTEGER'
        }
        
        for col_name, col_type in required_columns.items():
            if col_name not in columns:
                logger.info("Adding missing column: {col_name} ({col_type})")
                try:
                    cursor.execute(f"ALTER TABLE accessory_transactions ADD COLUMN {col_name} {col_type}")
                except sqlite3.OperationalError as e:
                    logger.info("Error adding column {col_name}: {str(e)}")
        
        conn.commit()
        logger.info("Column check and additions completed.")
    else:
        logger.info("Creating accessory_transactions table...")
        
        # Create the accessory_transactions table with all required columns
        cursor.execute('''
        CREATE TABLE accessory_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            accessory_id INTEGER NOT NULL,
            customer_id INTEGER,
            user_id INTEGER,
            transaction_type VARCHAR(50) NOT NULL,
            transaction_number VARCHAR(100),
            quantity INTEGER DEFAULT 1,
            notes TEXT,
            transaction_date DATETIME,
            FOREIGN KEY (accessory_id) REFERENCES accessories (id),
            FOREIGN KEY (customer_id) REFERENCES customer_users (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        
        # Create indexes for better performance
        try:
            cursor.execute('CREATE INDEX idx_accessory_transaction_accessory_id ON accessory_transactions(accessory_id)')
            cursor.execute('CREATE INDEX idx_accessory_transaction_customer_id ON accessory_transactions(customer_id)')
            cursor.execute('CREATE INDEX idx_accessory_transaction_user_id ON accessory_transactions(user_id)')
            
            conn.commit()
            logger.info("Successfully created accessory_transactions table.")
        except sqlite3.OperationalError as e:
            logger.info("Error creating indexes: {str(e)}")
    
    # Close connection
    conn.close()
    logger.info("Migration completed at {datetime.now()}")
    return True

if __name__ == "__main__":
    run_migration() 