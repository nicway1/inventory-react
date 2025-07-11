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
        
        logger.info("🔧 Fixing permissions table in: {db_path}")
        
        # Add the missing columns one by one
        missing_columns = [
            ('can_access_documents', 'BOOLEAN DEFAULT 0'),
            ('can_create_commercial_invoices', 'BOOLEAN DEFAULT 0'), 
            ('can_create_packing_lists', 'BOOLEAN DEFAULT 0')
        ]
        
        for column_name, column_def in missing_columns:
            try:
                logger.info("➕ Adding column: {column_name}")
                cursor.execute(f"ALTER TABLE permissions ADD COLUMN {column_name} {column_def}")
                logger.info("✅ Successfully added {column_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    logger.info("ℹ️  Column {column_name} already exists, skipping")
                else:
                    logger.info("❌ Error adding {column_name}: {e}")
        
        # Set appropriate defaults for SUPER_ADMIN
        logger.info("🔧 Setting SUPER_ADMIN permissions...")
        cursor.execute("""
            UPDATE permissions 
            SET can_access_documents = 1,
                can_create_commercial_invoices = 1,
                can_create_packing_lists = 1
            WHERE user_type = 'SUPER_ADMIN'
        """)
        
        # Commit changes
        conn.commit()
        logger.info("✅ Database updated successfully!")
        
        # Verify the fix
        logger.info("\n🔍 Verifying permissions table structure:")
        cursor.execute("PRAGMA table_info(permissions)")
        columns = cursor.fetchall()
        
        document_columns = [col for col in columns if 'document' in col[1] or 'commercial' in col[1] or 'packing' in col[1]]
        if document_columns:
            logger.info("✅ Document permission columns found:")
            for col in document_columns:
                logger.info("   - {col[1]} ({col[2]})")
        else:
            logger.info("❌ Document permission columns still missing")
        
        # Show current permissions
        logger.info("\n📊 Current permissions for SUPER_ADMIN:")
        cursor.execute("""
            SELECT can_access_documents, can_create_commercial_invoices, can_create_packing_lists 
            FROM permissions 
            WHERE user_type = 'SUPER_ADMIN'
        """)
        result = cursor.fetchone()
        if result:
            logger.info("   - can_access_documents: {result[0]}")
            logger.info("   - can_create_commercial_invoices: {result[1]}")
            logger.info("   - can_create_packing_lists: {result[2]}")
        
        conn.close()
        logger.info("\n🎉 Fix completed successfully!")
        return True
        
    except Exception as e:
        logger.info("❌ Error: {e}")
        return False

if __name__ == "__main__":
    logger.info("🚀 Starting permissions table fix...")
    success = fix_permissions_table()
    
    if success:
        logger.info("\n✅ SUCCESS: Permissions table has been fixed!")
        logger.info("📝 Next steps:")
        logger.info("   1. Restart your PythonAnywhere web app")
        logger.info("   2. Try logging in again")
    else:
        logger.info("\n❌ FAILED: Could not fix permissions table")
        sys.exit(1) 