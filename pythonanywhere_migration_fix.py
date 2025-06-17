#!/usr/bin/env python3
"""
PythonAnywhere-specific migration script to fix the permissions table.
This fixes the SQLite error: no such column: permissions.can_access_documents

Designed specifically for PythonAnywhere environment with detailed diagnostics.
Updated with the correct database path: /home/nicway2/inventory/inventory.db
"""

import sqlite3
import os
import sys
from pathlib import Path

def find_database():
    """Find the correct database file on PythonAnywhere"""
    print("🔍 Searching for database files...")
    
    # User specified path - highest priority
    user_specified_path = Path('/home/nicway2/inventory/inventory.db')
    
    # PythonAnywhere specific paths
    possible_paths = [
        # User specified path (highest priority)
        user_specified_path,
        
        # Backup paths in case the user path doesn't work
        Path.home() / 'inventory' / 'instance' / 'inventory.db',
        Path('/home/nicway2/inventory/instance/inventory.db'),
        
        # Current directory paths
        Path('./inventory.db'),
        Path('./instance/inventory.db'),
        
        # Other possible locations
        Path('/var/www/inventory.db'),
        Path('/tmp/inventory.db'),
    ]
    
    found_databases = []
    
    for path in possible_paths:
        if path.exists():
            size = path.stat().st_size
            found_databases.append((path, size))
            print(f"✓ Found database: {path} ({size} bytes)")
        else:
            print(f"✗ Not found: {path}")
    
    if not found_databases:
        print("❌ No database files found!")
        return None
    
    # Use the user specified path if it exists, otherwise use the largest database
    if user_specified_path.exists():
        selected_db = user_specified_path
        print(f"🎯 Using user-specified database: {selected_db}")
    else:
        # Sort by size and use the largest
        found_databases.sort(key=lambda x: x[1], reverse=True)
        selected_db = found_databases[0][0]
        print(f"🎯 Using largest database: {selected_db}")
    
    return selected_db

def check_table_exists(cursor, table_name):
    """Check if a table exists in the database"""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cursor.fetchone() is not None

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns

def create_permissions_table(cursor):
    """Create the complete permissions table with all columns"""
    print("📋 Creating permissions table with all columns...")
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS permissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_type VARCHAR(20) NOT NULL UNIQUE,
        can_view_assets BOOLEAN DEFAULT 1,
        can_edit_assets BOOLEAN DEFAULT 1,
        can_delete_assets BOOLEAN DEFAULT 1,
        can_create_assets BOOLEAN DEFAULT 1,
        can_view_country_assets BOOLEAN DEFAULT 0,
        can_edit_country_assets BOOLEAN DEFAULT 0,
        can_delete_country_assets BOOLEAN DEFAULT 0,
        can_create_country_assets BOOLEAN DEFAULT 0,
        can_view_accessories BOOLEAN DEFAULT 1,
        can_edit_accessories BOOLEAN DEFAULT 1,
        can_delete_accessories BOOLEAN DEFAULT 1,
        can_create_accessories BOOLEAN DEFAULT 1,
        can_view_companies BOOLEAN DEFAULT 0,
        can_edit_companies BOOLEAN DEFAULT 0,
        can_delete_companies BOOLEAN DEFAULT 0,
        can_create_companies BOOLEAN DEFAULT 0,
        can_view_users BOOLEAN DEFAULT 0,
        can_edit_users BOOLEAN DEFAULT 0,
        can_delete_users BOOLEAN DEFAULT 0,
        can_create_users BOOLEAN DEFAULT 0,
        can_view_tickets BOOLEAN DEFAULT 1,
        can_edit_tickets BOOLEAN DEFAULT 1,
        can_delete_tickets BOOLEAN DEFAULT 0,
        can_delete_own_tickets BOOLEAN DEFAULT 1,
        can_create_tickets BOOLEAN DEFAULT 1,
        can_view_reports BOOLEAN DEFAULT 0,
        can_generate_reports BOOLEAN DEFAULT 0,
        can_import_data BOOLEAN DEFAULT 0,
        can_export_data BOOLEAN DEFAULT 0,
        can_access_documents BOOLEAN DEFAULT 0,
        can_create_commercial_invoices BOOLEAN DEFAULT 0,
        can_create_packing_lists BOOLEAN DEFAULT 0
    )
    """
    
    cursor.execute(create_table_sql)
    print("✓ Permissions table created successfully!")

def seed_permissions_data(cursor):
    """Seed the permissions table with default data"""
    print("🌱 Seeding permissions table with default data...")
    
    # Check if data already exists
    cursor.execute("SELECT COUNT(*) FROM permissions")
    count = cursor.fetchone()[0]
    
    if count > 0:
        print(f"ℹ️  Permissions table already has {count} records, skipping seed data")
        return
    
    # Default permissions for different user types
    default_permissions = [
        ('SUPER_ADMIN', 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1),
        ('ADMIN', 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1),
        ('USER', 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0),
        ('READONLY', 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    ]
    
    insert_sql = """
    INSERT INTO permissions (
        user_type, can_view_assets, can_edit_assets, can_delete_assets, can_create_assets,
        can_view_country_assets, can_edit_country_assets, can_delete_country_assets, can_create_country_assets,
        can_view_accessories, can_edit_accessories, can_delete_accessories, can_create_accessories,
        can_view_companies, can_edit_companies, can_delete_companies, can_create_companies,
        can_view_users, can_edit_users, can_delete_users, can_create_users,
        can_view_tickets, can_edit_tickets, can_delete_tickets, can_delete_own_tickets, can_create_tickets,
        can_view_reports, can_generate_reports, can_import_data, can_export_data,
        can_access_documents, can_create_commercial_invoices, can_create_packing_lists
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    for perm in default_permissions:
        try:
            cursor.execute(insert_sql, perm)
            print(f"✓ Added permissions for {perm[0]}")
        except sqlite3.IntegrityError:
            print(f"ℹ️  Permissions for {perm[0]} already exist")

def add_missing_columns(cursor):
    """Add missing document permission columns to existing permissions table"""
    print("🔧 Adding missing document permission columns...")
    
    columns_to_add = [
        ('can_access_documents', 'BOOLEAN DEFAULT 0'),
        ('can_create_commercial_invoices', 'BOOLEAN DEFAULT 0'),
        ('can_create_packing_lists', 'BOOLEAN DEFAULT 0')
    ]
    
    for column_name, column_def in columns_to_add:
        if not check_column_exists(cursor, 'permissions', column_name):
            try:
                cursor.execute(f"ALTER TABLE permissions ADD COLUMN {column_name} {column_def}")
                print(f"✓ Added column: {column_name}")
                
                # Set appropriate defaults for SUPER_ADMIN
                cursor.execute(f"UPDATE permissions SET {column_name} = 1 WHERE user_type = 'SUPER_ADMIN'")
                print(f"✓ Updated {column_name} = 1 for SUPER_ADMIN")
                
            except sqlite3.Error as e:
                print(f"✗ Error adding column {column_name}: {e}")
        else:
            print(f"ℹ️  Column {column_name} already exists")

def show_database_info(cursor):
    """Show detailed information about the database"""
    print("\n📊 Database Analysis:")
    print("=" * 50)
    
    # Show all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"📋 Tables in database: {', '.join(tables)}")
    
    # Show permissions table structure if it exists
    if 'permissions' in tables:
        print("\n🔍 Permissions table structure:")
        cursor.execute("PRAGMA table_info(permissions)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"   - {col[1]} ({col[2]})")
        
        # Show current permissions data
        print("\n📝 Current permissions data:")
        cursor.execute("SELECT user_type, can_access_documents, can_create_commercial_invoices, can_create_packing_lists FROM permissions")
        perms = cursor.fetchall()
        if perms:
            for perm in perms:
                print(f"   - {perm[0]}: docs={perm[1]}, invoices={perm[2]}, packing={perm[3]}")
        else:
            print("   (No permissions data found)")
    
    print("=" * 50)

def main():
    """Main migration function"""
    print("🚀 PythonAnywhere Database Migration Script")
    print("🎯 Target: /home/nicway2/inventory/inventory.db")
    print("=" * 60)
    
    # Find the database
    db_path = find_database()
    if not db_path:
        print("❌ Migration failed: No database found")
        return False
    
    try:
        # Connect to database
        print(f"\n🔌 Connecting to database: {db_path}")
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Show initial database info
        show_database_info(cursor)
        
        # Check if permissions table exists
        if not check_table_exists(cursor, 'permissions'):
            print("\n⚠️  Permissions table does not exist!")
            create_permissions_table(cursor)
            seed_permissions_data(cursor)
        else:
            print("\n✓ Permissions table exists")
            add_missing_columns(cursor)
        
        # Commit changes
        conn.commit()
        
        # Show final database info
        print("\n🎉 Migration completed successfully!")
        show_database_info(cursor)
        
        conn.close()
        
        print("\n✅ Database migration completed successfully!")
        print("🔄 Please restart your PythonAnywhere web app to apply changes.")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 