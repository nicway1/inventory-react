#!/usr/bin/env python
"""
Script to create the accessory_transactions table
"""
import sqlite3
import os
from datetime import datetime
import uuid

def run_migration():
    # Connect to the database - adjust the path if needed
    db_path = '/home/nicway2/inventory.db'  # Direct path to the database
    logger.info("Attempting to connect to database at: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if table already exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='accessory_transactions'")
    if cursor.fetchone():
        logger.info("Table 'accessory_transactions' already exists, skipping creation.")
        conn.close()
        return
    
    logger.info("Creating accessory_transactions table...")
    
    # Create the accessory_transactions table with all required columns
    cursor.execute('''
    CREATE TABLE accessory_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        accessory_id INTEGER NOT NULL,
        customer_id INTEGER,
        user_id INTEGER,
        transaction_type VARCHAR(50) NOT NULL,
        transaction_number VARCHAR(100) NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        notes TEXT,
        transaction_date DATETIME NOT NULL,
        FOREIGN KEY (accessory_id) REFERENCES accessories (id),
        FOREIGN KEY (customer_id) REFERENCES customer_users (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Create indexes for better performance
    cursor.execute('CREATE INDEX idx_accessory_transaction_accessory_id ON accessory_transactions(accessory_id)')
    cursor.execute('CREATE INDEX idx_accessory_transaction_customer_id ON accessory_transactions(customer_id)')
    cursor.execute('CREATE INDEX idx_accessory_transaction_user_id ON accessory_transactions(user_id)')
    cursor.execute('CREATE INDEX idx_accessory_transaction_type ON accessory_transactions(transaction_type)')
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    logger.info("Successfully created accessory_transactions table at {datetime.now()}")
    return True

if __name__ == "__main__":
    run_migration() 