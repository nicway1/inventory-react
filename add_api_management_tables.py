#!/usr/bin/env python3
"""
Database migration script to add API management tables
"""

import sqlite3
import os
from datetime import datetime

def add_api_management_tables():
    """Add API key and usage tracking tables to the database"""
    
    # Connect to the database
    db_path = 'inventory.db'
    if not os.path.exists(db_path):
        print(f"Database file {db_path} not found!")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("Adding API management tables...")
        
        # Create api_keys table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                key_hash VARCHAR(255) NOT NULL UNIQUE,
                permissions TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME,
                last_used_at DATETIME,
                is_active BOOLEAN DEFAULT 1,
                created_by_id INTEGER,
                request_count INTEGER DEFAULT 0,
                last_request_ip VARCHAR(45),
                FOREIGN KEY (created_by_id) REFERENCES users (id)
            )
        ''')
        
        # Create api_usage table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key_id INTEGER NOT NULL,
                endpoint VARCHAR(255) NOT NULL,
                method VARCHAR(10) NOT NULL,
                status_code INTEGER NOT NULL,
                response_time_ms INTEGER,
                request_ip VARCHAR(45),
                user_agent VARCHAR(255),
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                error_message TEXT,
                FOREIGN KEY (api_key_id) REFERENCES api_keys (id)
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys (key_hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys (is_active)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_api_keys_expires ON api_keys (expires_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_api_usage_key_id ON api_usage (api_key_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_api_usage_timestamp ON api_usage (timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_api_usage_endpoint ON api_usage (endpoint)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_api_usage_status ON api_usage (status_code)')
        
        # Commit the changes
        conn.commit()
        print("✅ API management tables created successfully!")
        
        # Verify tables were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('api_keys', 'api_usage')")
        tables = cursor.fetchall()
        
        if len(tables) == 2:
            print("✅ Verified: Both api_keys and api_usage tables exist")
            
            # Show table structure
            print("\n📋 API Keys table structure:")
            cursor.execute("PRAGMA table_info(api_keys)")
            for row in cursor.fetchall():
                print(f"  - {row[1]} ({row[2]})")
            
            print("\n📋 API Usage table structure:")
            cursor.execute("PRAGMA table_info(api_usage)")
            for row in cursor.fetchall():
                print(f"  - {row[1]} ({row[2]})")
                
            return True
        else:
            print("❌ Error: Not all tables were created properly")
            return False
            
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        conn.rollback()
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 Starting API management tables migration...")
    success = add_api_management_tables()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("You can now use the API management system.")
    else:
        print("\n💥 Migration failed!")
        print("Please check the error messages above and try again.")