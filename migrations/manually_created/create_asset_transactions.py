#!/usr/bin/env python
"""
Manual migration script to create the asset_transactions table
"""
import sqlite3
import os
from datetime import datetime

def run_migration():
    # Connect to the database
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    
    # Check if table already exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='asset_transactions'")
    if cursor.fetchone():
        print("Table 'asset_transactions' already exists, skipping creation.")
        conn.close()
        return
    
    # Create the asset_transactions table
    cursor.execute('''
    CREATE TABLE asset_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_number VARCHAR(50) NOT NULL UNIQUE,
        asset_id INTEGER NOT NULL,
        customer_id INTEGER,
        transaction_date DATETIME NOT NULL,
        transaction_type VARCHAR(50) NOT NULL,
        notes TEXT,
        FOREIGN KEY (asset_id) REFERENCES assets (id),
        FOREIGN KEY (customer_id) REFERENCES customer_users (id)
    )
    ''')
    
    # Create an index for better performance
    cursor.execute('CREATE INDEX idx_asset_transaction_asset_id ON asset_transactions(asset_id)')
    cursor.execute('CREATE INDEX idx_asset_transaction_customer_id ON asset_transactions(customer_id)')
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print(f"Successfully created asset_transactions table at {datetime.now()}")

if __name__ == "__main__":
    run_migration() 