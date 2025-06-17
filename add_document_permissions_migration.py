#!/usr/bin/env python3
"""
Migration script to add document permissions columns to the permissions table.
This fixes the SQLite error: no such column: permissions.can_access_documents

Run this script on PythonAnywhere to update the database schema.
"""

import sqlite3
import os
import sys
from pathlib import Path

def add_document_permissions():
    """Add document permissions columns to the permissions table"""
    
    # Get database path
    db_path = Path(__file__).parent / 'instance' / 'inventory.db'
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        print("Adding document permissions columns to permissions table...")
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(permissions)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        # List of document permission columns to add
        document_columns = [
            ('can_access_documents', 'INTEGER DEFAULT 1'),
            ('can_create_commercial_invoices', 'INTEGER DEFAULT 1'),
            ('can_create_packing_lists', 'INTEGER DEFAULT 1')
        ]
        
        columns_added = 0
        
        for column_name, column_def in document_columns:
            if column_name not in existing_columns:
                try:
                    alter_sql = f"ALTER TABLE permissions ADD COLUMN {column_name} {column_def}"
                    cursor.execute(alter_sql)
                    print(f"✓ Added column: {column_name}")
                    columns_added += 1
                except sqlite3.Error as e:
                    print(f"✗ Error adding column {column_name}: {e}")
            else:
                print(f"✓ Column {column_name} already exists")
        
        # Commit the changes
        conn.commit()
        
        if columns_added > 0:
            print(f"\n✓ Successfully added {columns_added} document permission columns!")
            
            # Update existing permissions with default values for CLIENT users
            print("Updating CLIENT user permissions...")
            cursor.execute("""
                UPDATE permissions 
                SET can_access_documents = 0,
                    can_create_commercial_invoices = 0,
                    can_create_packing_lists = 0
                WHERE user_type = 'CLIENT'
            """)
            conn.commit()
            print("✓ Updated CLIENT permissions")
            
        print("\n✓ Database migration completed successfully!")
        return True
        
    except sqlite3.Error as e:
        print(f"✗ Database error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def main():
    """Main migration function"""
    print("=== Document Permissions Migration ===")
    print("This script will add missing document permission columns to the permissions table.")
    print()
    
    success = add_document_permissions()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("You can now restart your PythonAnywhere web app.")
    else:
        print("\n❌ Migration failed!")
        print("Please check the error messages above and try again.")
        sys.exit(1)

if __name__ == "__main__":
    main() 