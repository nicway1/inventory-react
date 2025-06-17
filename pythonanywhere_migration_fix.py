#!/usr/bin/env python3
"""
PythonAnywhere-specific migration script to fix the permissions table.
This fixes the SQLite error: no such column: permissions.can_access_documents

Designed specifically for PythonAnywhere environment with detailed diagnostics.
"""

import sqlite3
import os
import sys
from pathlib import Path

def find_database():
    """Find the correct database file on PythonAnywhere"""
    print("🔍 Searching for database files...")
    
    # PythonAnywhere specific paths
    possible_paths = [
        # Most likely PythonAnywhere paths
        Path.home() / 'inventory' / 'instance' / 'inventory.db',
        Path('/home/nicway2/inventory/instance/inventory.db'),
        Path('/home/nicway2/inventory.db'),
        
        # Current directory paths
        Path(__file__).parent / 'instance' / 'inventory.db',
        Path(__file__).parent / 'inventory.db',
        
        # Alternative paths
        Path.home() / 'inventory.db',
        Path('/var/www/nicway2_pythonanywhere_com_wsgi.py/../inventory.db'),
        Path('/var/www/nicway2_pythonanywhere_com_wsgi.py/../instance/inventory.db'),
    ]
    
    found_dbs = []
    for path in possible_paths:
        if path.exists():
            size = path.stat().st_size
            print(f"✅ Found: {path} (size: {size} bytes)")
            found_dbs.append((path, size))
        else:
            print(f"❌ Not found: {path}")
    
    if not found_dbs:
        print("⚠️  No database files found!")
        return None
    
    # Return the largest database file (most likely to be the real one)
    largest_db = max(found_dbs, key=lambda x: x[1])
    print(f"📍 Using largest database: {largest_db[0]} ({largest_db[1]} bytes)")
    return largest_db[0]

def analyze_database(db_path):
    """Analyze the database structure"""
    print(f"\n🔬 Analyzing database: {db_path}")
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # List all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"📋 Found {len(tables)} tables:")
        for table in tables:
            print(f"  - {table[0]}")
        
        # Check if permissions table exists
        if ('permissions',) in tables:
            print("\n✅ Permissions table exists!")
            
            # Show current structure
            cursor.execute("PRAGMA table_info(permissions)")
            columns = cursor.fetchall()
            print(f"📊 Permissions table has {len(columns)} columns:")
            
            document_columns = ['can_access_documents', 'can_create_commercial_invoices', 'can_create_packing_lists']
            missing_columns = []
            
            for column in columns:
                col_name = column[1]
                is_document_col = col_name in document_columns
                status = "🔥 MISSING DOC COLUMN" if col_name in document_columns else ""
                print(f"  - {col_name} ({column[2]}) {status}")
            
            # Check for missing document columns
            existing_columns = [col[1] for col in columns]
            missing_columns = [col for col in document_columns if col not in existing_columns]
            
            if missing_columns:
                print(f"\n❌ Missing document columns: {missing_columns}")
                return conn, missing_columns
            else:
                print("\n✅ All document columns present!")
                return conn, []
        else:
            print("\n❌ Permissions table does NOT exist!")
            return conn, None
            
    except Exception as e:
        print(f"❌ Error analyzing database: {e}")
        return None, None

def fix_permissions_table(conn, missing_columns):
    """Fix the permissions table by adding missing columns"""
    print(f"\n🔧 Fixing permissions table...")
    
    try:
        cursor = conn.cursor()
        
        if missing_columns is None:
            # Create the entire table
            print("Creating permissions table from scratch...")
            cursor.execute("""
                CREATE TABLE permissions (
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
            
            # Insert default permissions
            cursor.execute("""
                INSERT OR IGNORE INTO permissions (
                    user_type, can_access_documents, can_create_commercial_invoices, can_create_packing_lists
                ) VALUES 
                ('SUPER_ADMIN', TRUE, TRUE, TRUE),
                ('ADMIN', TRUE, TRUE, TRUE),
                ('USER', FALSE, FALSE, FALSE),
                ('VIEWER', FALSE, FALSE, FALSE)
            """)
            print("✅ Created permissions table with document columns!")
            
        elif missing_columns:
            # Add missing columns
            for column in missing_columns:
                print(f"Adding column: {column}")
                default_value = "TRUE" if "SUPER_ADMIN" in str(cursor.execute("SELECT user_type FROM permissions").fetchall()) else "FALSE"
                cursor.execute(f"ALTER TABLE permissions ADD COLUMN {column} BOOLEAN DEFAULT FALSE")
                print(f"✅ Added column: {column}")
            
            # Update admin permissions
            print("Updating admin permissions...")
            cursor.execute("""
                UPDATE permissions 
                SET can_access_documents = TRUE, 
                    can_create_commercial_invoices = TRUE, 
                    can_create_packing_lists = TRUE 
                WHERE user_type IN ('SUPER_ADMIN', 'ADMIN')
            """)
            print("✅ Updated admin permissions!")
        
        conn.commit()
        print("✅ Database fix completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing database: {e}")
        return False

def main():
    print("🚀 PythonAnywhere Database Migration Fix")
    print("=" * 50)
    
    # Find database
    db_path = find_database()
    if not db_path:
        print("❌ No database found. Cannot proceed.")
        sys.exit(1)
    
    # Analyze database
    conn, missing_columns = analyze_database(db_path)
    if conn is None:
        print("❌ Failed to analyze database.")
        sys.exit(1)
    
    try:
        # Fix if needed
        if missing_columns is None or missing_columns:
            print(f"\n🔧 Database needs fixing...")
            success = fix_permissions_table(conn, missing_columns)
            if success:
                print("\n🎉 Migration completed successfully!")
                print("\n📋 Next steps:")
                print("1. Restart your PythonAnywhere web app")
                print("2. Test login functionality")
            else:
                print("\n❌ Migration failed!")
                sys.exit(1)
        else:
            print("\n✅ Database is already up to date!")
    
    finally:
        conn.close()

if __name__ == "__main__":
    main() 