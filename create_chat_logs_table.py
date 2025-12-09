#!/usr/bin/env python3
"""
Script to create the chat_logs table for chatbot training data collection.
Run this once on PythonAnywhere after pulling the code.

Usage: python create_chat_logs_table.py
"""

import sqlite3
import os

# Determine database path
if os.path.exists('/home/nicway/inventory/inventory.db'):
    DB_PATH = '/home/nicway/inventory/inventory.db'
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory.db')

def create_table():
    print(f"Creating chat_logs table in: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if table already exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chat_logs'")
    if cursor.fetchone():
        print("Table 'chat_logs' already exists.")
        conn.close()
        return

    # Create the table
    cursor.execute("""
        CREATE TABLE chat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_name VARCHAR(100),
            session_id VARCHAR(100),
            query TEXT NOT NULL,
            response TEXT,
            response_type VARCHAR(50),
            matched_question VARCHAR(500),
            match_score INTEGER,
            was_helpful BOOLEAN,
            feedback TEXT,
            action_type VARCHAR(50),
            action_executed BOOLEAN DEFAULT 0,
            ip_address VARCHAR(50),
            user_agent VARCHAR(500),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Create indexes for common queries
    cursor.execute("CREATE INDEX idx_chat_logs_user_id ON chat_logs(user_id)")
    cursor.execute("CREATE INDEX idx_chat_logs_response_type ON chat_logs(response_type)")
    cursor.execute("CREATE INDEX idx_chat_logs_created_at ON chat_logs(created_at)")

    conn.commit()
    print("Table 'chat_logs' created successfully!")
    print("Indexes created for user_id, response_type, and created_at")

    conn.close()
    print("Done!")

if __name__ == '__main__':
    create_table()
