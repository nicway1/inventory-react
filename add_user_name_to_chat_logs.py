#!/usr/bin/env python3
"""
Script to add user_name column to existing chat_logs table.
Run this on PythonAnywhere if chat_logs table already exists.

Usage: python add_user_name_to_chat_logs.py
"""

import sqlite3
import os

# Determine database path
if os.path.exists('/home/nicway/inventory/inventory.db'):
    DB_PATH = '/home/nicway/inventory/inventory.db'
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory.db')

def add_column():
    print(f"Adding user_name column to chat_logs in: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chat_logs'")
    if not cursor.fetchone():
        print("Table 'chat_logs' does not exist. Run create_chat_logs_table.py first.")
        conn.close()
        return

    # Check if column already exists
    cursor.execute("PRAGMA table_info(chat_logs)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'user_name' in columns:
        print("Column 'user_name' already exists.")
        conn.close()
        return

    # Add the column
    cursor.execute("ALTER TABLE chat_logs ADD COLUMN user_name VARCHAR(100)")
    conn.commit()
    print("Column 'user_name' added successfully!")

    conn.close()
    print("Done!")

if __name__ == '__main__':
    add_column()
