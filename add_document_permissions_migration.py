#!/usr/bin/env python3
"""
Enhanced migration script to add document permissions columns to the permissions table.
This fixes the SQLite error: no such column: permissions.can_access_documents

Handles cases where the permissions table might not exist yet.
Run this script on PythonAnywhere to update the database schema.
"""

import sqlite3
import os
import sys
from pathlib import Path

def check_table_exists(cursor, table_name):
    """Check if a table exists in the database"""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cursor.fetchone() is not None

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return any(column[1] == column_name for column in columns)

def create_permissions_table(cursor):
    """Create the permissions table with all necessary columns"""
    print("Creating permissions table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_type VARCHAR(50) NOT NULL UNIQUE,
            can_view_assets BOOLEAN DEFAULT TRUE,
            can_edit_assets BOOLEAN DEFAULT TRUE,
            can_delete_assets BOOLEAN DEFAULT TRUE,
            can_create_assets BOOLEAN DEFAULT TRUE,
            can_view_country_assets BOOLEAN DEFAULT TRUE,
            can_edit_country_assets BOOLEAN DEFAULT TRUE,
            can_delete_country_assets BOOLEAN DEFAULT TRUE,
            can_create_country_assets BOOLEAN DEFAULT TRUE,
            can_view_accessories BOOLEAN DEFAULT TRUE,
            can_edit_accessories BOOLEAN DEFAULT TRUE,
            can_delete_accessories BOOLEAN DEFAULT TRUE,
            can_create_accessories BOOLEAN DEFAULT TRUE,
            can_view_companies BOOLEAN DEFAULT TRUE,
            can_edit_companies BOOLEAN DEFAULT TRUE,
            can_delete_companies BOOLEAN DEFAULT TRUE,
            can_create_companies BOOLEAN DEFAULT TRUE,
            can_view_users BOOLEAN DEFAULT TRUE,
            can_edit_users BOOLEAN DEFAULT TRUE,
            can_delete_users BOOLEAN DEFAULT TRUE,
            can_create_users BOOLEAN DEFAULT TRUE,
            can_view_tickets BOOLEAN DEFAULT TRUE,
            can_edit_tickets BOOLEAN DEFAULT TRUE,
            can_delete_tickets BOOLEAN DEFAULT TRUE,
            can_delete_own_tickets BOOLEAN DEFAULT TRUE,
            can_create_tickets BOOLEAN DEFAULT TRUE,
            can_view_reports BOOLEAN DEFAULT TRUE,
            can_generate_reports BOOLEAN DEFAULT TRUE,
            can_import_data BOOLEAN DEFAULT TRUE,
            can_export_data BOOLEAN DEFAULT TRUE,
            can_access_documents BOOLEAN DEFAULT FALSE,
            can_create_commercial_invoices BOOLEAN DEFAULT FALSE,
            can_create_packing_lists BOOLEAN DEFAULT FALSE
        )
    """)
    
    # Insert default permissions for common user types
    cursor.execute("""
        INSERT OR IGNORE INTO permissions (
            user_type, can_access_documents, can_create_commercial_invoices, can_create_packing_lists
        ) VALUES 
        ('SUPER_ADMIN', TRUE, TRUE, TRUE),
        ('ADMIN', TRUE, TRUE, TRUE),
        ('USER', FALSE, FALSE, FALSE),
        ('VIEWER', FALSE, FALSE, FALSE)
    """)
    print("✓ Permissions table created successfully!")

def add_document_permissions():
    """Add document permissions columns to the permissions table"""
    
    # Try multiple possible database paths
    possible_paths = [
        Path(__file__).parent / 'instance' / 'inventory.db',
        Path.home() / 'inventory' / 'instance' / 'inventory.db',
        Path('/home/nicway2/inventory/instance/inventory.db'),
        Path(__file__).parent / 'inventory.db',
        Path.home() / 'inventory.db'
    ]
    
    db_path = None
    for path in possible_paths:
        if path.exists():
            db_path = path
            break
    
    if not db_path:
        print(f"Database not found. Checked paths:")
        for path in possible_paths:
            print(f"  - {path}")
        print("Creating new database at default location...")
        db_path = Path(__file__).parent / 'instance' / 'inventory.db'
        # Create instance directory if it doesn't exist
        db_path.parent.mkdir(exist_ok=True)
    
    print(f"Using database: {db_path}")
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        print("Checking database structure...")
        
        # Check if permissions table exists
        if not check_table_exists(cursor, 'permissions'):
            print("Permissions table not found. Creating it...")
            create_permissions_table(cursor)
        else:
            print("✓ Permissions table exists")
            
            # Check and add missing columns
            columns_to_add = [
                ('can_access_documents', 'FALSE'),
                ('can_create_commercial_invoices', 'FALSE'),
                ('can_create_packing_lists', 'FALSE')
            ]
            
            for column_name, default_value in columns_to_add:
                if not check_column_exists(cursor, 'permissions', column_name):
                    print(f"Adding missing column: {column_name}")
                    try:
                        cursor.execute(f"ALTER TABLE permissions ADD COLUMN {column_name} BOOLEAN DEFAULT {default_value}")
                        print(f"✓ Added column {column_name}")
                    except Exception as e:
                        print(f"✗ Error adding column {column_name}: {e}")
                        return False
                else:
                    print(f"✓ Column {column_name} already exists")
            
            # Update SUPER_ADMIN and ADMIN permissions to have document access
            print("Updating admin permissions for document access...")
            cursor.execute("""
                UPDATE permissions 
                SET can_access_documents = TRUE, 
                    can_create_commercial_invoices = TRUE, 
                    can_create_packing_lists = TRUE 
                WHERE user_type IN ('SUPER_ADMIN', 'ADMIN')
            """)
        
        # Show current permissions structure
        print("\nCurrent permissions table structure:")
        cursor.execute("PRAGMA table_info(permissions)")
        columns = cursor.fetchall()
        for column in columns:
            print(f"  - {column[1]} ({column[2]})")
        
        conn.commit()
        print("✓ Database migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Error during migration: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("🚀 Starting enhanced database migration...")
    print("This script will add missing document permission columns to the permissions table.")
    
    success = add_document_permissions()
    
    if success:
        print("🎉 Migration completed successfully!")
        print("\n📋 Next steps:")
        print("1. Restart your PythonAnywhere web app")
        print("2. Test login functionality")
        print("3. Check that document permissions work correctly")
    else:
        print("❌ Migration failed!")
        sys.exit(1) 