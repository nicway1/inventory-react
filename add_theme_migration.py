#!/usr/bin/env python3
"""
Migration script to add theme_preference column to users table
"""

import sqlite3
import os

def migrate_database():
    """Add theme_preference column to users table"""
    
    db_path = "inventory.db"
    
    if not os.path.exists(db_path):
        print("Database file not found. Skipping migration.")
        return
    
    print("🔄 Starting theme preference migration...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'theme_preference' in columns:
            print("✅ theme_preference column already exists. Migration skipped.")
            return
        
        # Add the column
        cursor.execute("ALTER TABLE users ADD COLUMN theme_preference VARCHAR(20) DEFAULT 'light'")
        
        # Update all existing users to have light theme by default
        cursor.execute("UPDATE users SET theme_preference = 'light' WHERE theme_preference IS NULL")
        
        conn.commit()
        print("✅ Successfully added theme_preference column to users table")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database() 