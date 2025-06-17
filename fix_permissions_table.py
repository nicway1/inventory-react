#!/usr/bin/env python3
"""
Simple fix for missing document permissions columns in PythonAnywhere database.
Adds the three missing columns: can_access_documents, can_create_commercial_invoices, can_create_packing_lists
"""

import sqlite3
import sys
from pathlib import Path

def fix_permissions_table():
    """Add missing document permission columns to the permissions table"""
    
    db_path = '/home/nicway2/inventory/inventory.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"🔧 Fixing permissions table in: {db_path}")
        
        # Add the missing columns one by one
        missing_columns = [
            ('can_access_documents', 'BOOLEAN DEFAULT 0'),
            ('can_create_commercial_invoices', 'BOOLEAN DEFAULT 0'), 
            ('can_create_packing_lists', 'BOOLEAN DEFAULT 0')
        ]
        
        for column_name, column_def in missing_columns:
            try:
                print(f"➕ Adding column: {column_name}")
                cursor.execute(f"ALTER TABLE permissions ADD COLUMN {column_name} {column_def}")
                print(f"✅ Successfully added {column_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    print(f"ℹ️  Column {column_name} already exists, skipping")
                else:
                    print(f"❌ Error adding {column_name}: {e}")
        
        # Set appropriate defaults for SUPER_ADMIN
        print("🔧 Setting SUPER_ADMIN permissions...")
        cursor.execute("""
            UPDATE permissions 
            SET can_access_documents = 1,
                can_create_commercial_invoices = 1,
                can_create_packing_lists = 1
            WHERE user_type = 'SUPER_ADMIN'
        """)
        
        # Commit changes
        conn.commit()
        print("✅ Database updated successfully!")
        
        # Verify the fix
        print("\n🔍 Verifying permissions table structure:")
        cursor.execute("PRAGMA table_info(permissions)")
        columns = cursor.fetchall()
        
        document_columns = [col for col in columns if 'document' in col[1] or 'commercial' in col[1] or 'packing' in col[1]]
        if document_columns:
            print("✅ Document permission columns found:")
            for col in document_columns:
                print(f"   - {col[1]} ({col[2]})")
        else:
            print("❌ Document permission columns still missing")
        
        # Show current permissions
        print("\n📊 Current permissions for SUPER_ADMIN:")
        cursor.execute("""
            SELECT can_access_documents, can_create_commercial_invoices, can_create_packing_lists 
            FROM permissions 
            WHERE user_type = 'SUPER_ADMIN'
        """)
        result = cursor.fetchone()
        if result:
            print(f"   - can_access_documents: {result[0]}")
            print(f"   - can_create_commercial_invoices: {result[1]}")
            print(f"   - can_create_packing_lists: {result[2]}")
        
        conn.close()
        print("\n🎉 Fix completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting permissions table fix...")
    success = fix_permissions_table()
    
    if success:
        print("\n✅ SUCCESS: Permissions table has been fixed!")
        print("📝 Next steps:")
        print("   1. Restart your PythonAnywhere web app")
        print("   2. Try logging in again")
    else:
        print("\n❌ FAILED: Could not fix permissions table")
        sys.exit(1) 