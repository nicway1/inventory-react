#!/usr/bin/env python3
"""
Comprehensive fix for PythonAnywhere database
Ensures all required columns and tables exist
"""

import sqlite3
import os
import sys

def check_and_fix_database():
    """Check and fix all database schema issues"""
    
    db_path = 'inventory.db'
    if not os.path.exists(db_path):
        print(f"✗ Database file not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("=" * 60)
        print("Checking Database Schema")
        print("=" * 60)
        
        # Check 1: bug_reports.case_progress
        print("\n1. Checking bug_reports.case_progress...")
        cursor.execute("PRAGMA table_info(bug_reports)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'case_progress' not in columns:
            print("   ✗ Missing - Adding case_progress to bug_reports...")
            cursor.execute("ALTER TABLE bug_reports ADD COLUMN case_progress INTEGER DEFAULT 0")
            conn.commit()
            print("   ✓ Added case_progress to bug_reports")
        else:
            print("   ✓ Already exists")
        
        # Check 2: feature_requests.case_progress
        print("\n2. Checking feature_requests.case_progress...")
        cursor.execute("PRAGMA table_info(feature_requests)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'case_progress' not in columns:
            print("   ✗ Missing - Adding case_progress to feature_requests...")
            cursor.execute("ALTER TABLE feature_requests ADD COLUMN case_progress INTEGER DEFAULT 0")
            conn.commit()
            print("   ✓ Added case_progress to feature_requests")
        else:
            print("   ✓ Already exists")
        
        # Check 3: test_cases table
        print("\n3. Checking test_cases table...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test_cases'")
        
        if not cursor.fetchone():
            print("   ✗ Missing - Creating test_cases table...")
            cursor.execute("""
                CREATE TABLE test_cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bug_id INTEGER NOT NULL,
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
                    FOREIGN KEY (bug_id) REFERENCES bug_reports(id) ON DELETE CASCADE,
                    FOREIGN KEY (created_by_id) REFERENCES users(id),
                    FOREIGN KEY (tested_by_id) REFERENCES users(id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_test_cases_bug_id ON test_cases(bug_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_test_cases_status ON test_cases(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_test_cases_priority ON test_cases(priority)")
            conn.commit()
            print("   ✓ Created test_cases table")
        else:
            print("   ✓ Already exists")
        
        # Check 4: feature_test_cases table
        print("\n4. Checking feature_test_cases table...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='feature_test_cases'")
        
        if not cursor.fetchone():
            print("   ✗ Missing - Creating feature_test_cases table...")
            cursor.execute("""
                CREATE TABLE feature_test_cases (
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
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_feature_test_cases_feature_id ON feature_test_cases(feature_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_feature_test_cases_status ON feature_test_cases(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_feature_test_cases_priority ON feature_test_cases(priority)")
            conn.commit()
            print("   ✓ Created feature_test_cases table")
        else:
            print("   ✓ Already exists")
        
        print("\n" + "=" * 60)
        print("✓ All database checks completed successfully!")
        print("=" * 60)
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.close()
        return False

if __name__ == '__main__':
    success = check_and_fix_database()
    sys.exit(0 if success else 1)
