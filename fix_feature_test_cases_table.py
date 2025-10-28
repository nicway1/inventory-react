#!/usr/bin/env python3
"""
Fix script to ensure feature_test_cases table exists
This handles the case where the migration failed
"""

import sqlite3
import os
import sys

def fix_feature_test_cases_table():
    """Create feature_test_cases table if it doesn't exist"""
    
    # Find database file
    db_path = 'inventory.db'
    if not os.path.exists(db_path):
        print(f"✗ Database file not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='feature_test_cases'
        """)
        
        exists = cursor.fetchone()
        
        if exists:
            print("✓ Table 'feature_test_cases' already exists")
            cursor.close()
            conn.close()
            return True
        
        print("Creating 'feature_test_cases' table...")
        
        # Create the table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feature_test_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feature_id INTEGER NOT NULL,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                preconditions TEXT,
                test_steps TEXT NOT NULL,
                expected_result TEXT NOT NULL,
                actual_result TEXT,
                status VARCHAR(20) DEFAULT 'Pending',
                priority VARCHAR(20) DEFAULT 'Medium',
                test_data TEXT,
                created_by_id INTEGER NOT NULL,
                tested_by_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME,
                tested_at DATETIME,
                FOREIGN KEY (feature_id) REFERENCES feature_requests(id) ON DELETE CASCADE,
                FOREIGN KEY (created_by_id) REFERENCES users(id),
                FOREIGN KEY (tested_by_id) REFERENCES users(id)
            )
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_feature_test_cases_feature_id 
            ON feature_test_cases(feature_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_feature_test_cases_status 
            ON feature_test_cases(status)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_feature_test_cases_priority 
            ON feature_test_cases(priority)
        """)
        
        conn.commit()
        print("✓ Table 'feature_test_cases' created successfully!")
        print("✓ Indexes created successfully!")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        if 'conn' in locals():
            conn.close()
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("Fix Feature Test Cases Table")
    print("=" * 60)
    success = fix_feature_test_cases_table()
    print("=" * 60)
    sys.exit(0 if success else 1)
