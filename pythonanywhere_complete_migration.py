#!/usr/bin/env python3
"""
Complete PythonAnywhere Database Migration Script
Fixes all missing tables and columns for the inventory system.

This script addresses:
1. Missing shipping_tracking_3, 4, 5 columns
2. Missing package_items table
3. Any other schema mismatches

Run this script on PythonAnywhere to fix all database schema issues.
"""
import sqlite3
import os
import sys

def create_package_items_table(cursor):
    """Create the package_items table if it doesn't exist"""
    logger.info("🔧 Creating package_items table...")
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS package_items (
        id INTEGER NOT NULL PRIMARY KEY,
        ticket_id INTEGER NOT NULL,
        package_number INTEGER NOT NULL,
        asset_id INTEGER,
        accessory_id INTEGER,
        quantity INTEGER DEFAULT 1,
        notes TEXT,
        created_at DATETIME,
        updated_at DATETIME,
        FOREIGN KEY(ticket_id) REFERENCES tickets (id),
        FOREIGN KEY(asset_id) REFERENCES assets (id),
        FOREIGN KEY(accessory_id) REFERENCES accessories (id)
    )
    """
    
    try:
        cursor.execute(create_table_sql)
        logger.info("   ✓ Successfully created package_items table")
        return True
    except Exception as e:
        logger.info("   ✗ Error creating package_items table: {e}")
        return False

def add_shipping_tracking_columns(cursor):
    """Add missing shipping tracking columns to tickets table"""
    logger.info("🔧 Adding shipping tracking columns...")
    
    # Define all shipping tracking columns that should exist
    required_columns = [
        # Package 2 (might already exist)
        ('shipping_tracking_2', 'TEXT'),
        ('shipping_carrier_2', 'TEXT'),
        ('shipping_status_2', 'TEXT DEFAULT \'Pending\''),
        # Package 3 (likely missing - this was the original error column)
        ('shipping_tracking_3', 'TEXT'),
        ('shipping_carrier_3', 'TEXT'),
        ('shipping_status_3', 'TEXT DEFAULT \'Pending\''),
        # Package 4 (likely missing)
        ('shipping_tracking_4', 'TEXT'),
        ('shipping_carrier_4', 'TEXT'),
        ('shipping_status_4', 'TEXT DEFAULT \'Pending\''),
        # Package 5 (likely missing)
        ('shipping_tracking_5', 'TEXT'),
        ('shipping_carrier_5', 'TEXT'),
        ('shipping_status_5', 'TEXT DEFAULT \'Pending\''),
    ]
    
    # Check existing columns
    cursor.execute("PRAGMA table_info(tickets)")
    existing_columns = {column[1]: column for column in cursor.fetchall()}
    
    # Find missing columns
    missing_columns = []
    for column_name, column_definition in required_columns:
        if column_name not in existing_columns:
            missing_columns.append((column_name, column_definition))
    
    if not missing_columns:
        logger.info("   ✓ All shipping tracking columns already exist")
        return True
    
    logger.info("   Found {len(missing_columns)} missing columns")
    
    # Add missing columns
    successful_additions = 0
    for column_name, column_definition in missing_columns:
        sql = f"ALTER TABLE tickets ADD COLUMN {column_name} {column_definition}"
        logger.info("   Adding: {column_name}...")
        
        try:
            cursor.execute(sql)
            logger.info("   ✓ Successfully added {column_name}")
            successful_additions += 1
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                logger.info("   ⚠️  Column {column_name} already exists (skipping)")
                successful_additions += 1
            else:
                logger.info("   ✗ Error adding {column_name}: {e}")
    
    return successful_additions == len(missing_columns)

def verify_tables_and_columns(cursor):
    """Verify that all required tables and columns exist"""
    logger.info("🔍 Verifying database schema...")
    
    issues = []
    
    # Check if package_items table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='package_items'")
    if not cursor.fetchone():
        issues.append("package_items table missing")
    else:
        logger.info("   ✓ package_items table exists")
    
    # Check shipping tracking columns in tickets table
    cursor.execute("PRAGMA table_info(tickets)")
    columns = {column[1]: column for column in cursor.fetchall()}
    
    critical_columns = ['shipping_tracking_3', 'shipping_tracking_4', 'shipping_tracking_5']
    for col in critical_columns:
        if col not in columns:
            issues.append(f"tickets.{col} column missing")
        else:
            logger.info("   ✓ tickets.{col} exists")
    
    return issues

def fix_pythonanywhere_database():
    """Complete database migration for PythonAnywhere"""
    # PythonAnywhere database path
    db_path = '/home/nicway2/inventory/inventory.db'
    
    logger.info("🎯 PythonAnywhere Complete Database Migration")
    logger.info("Database path: {db_path}")
    
    if not os.path.exists(db_path):
        logger.info("❌ Error: Database file {db_path} not found")
        logger.info("Current directory: {os.getcwd()}")
        return False
    
    try:
        logger.info("🔌 Opening database connection...")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current issues
        issues = verify_tables_and_columns(cursor)
        if not issues:
            logger.info("✅ Database schema is already up to date!")
            return True
        
        logger.info("⚠️  Found {len(issues)} schema issues:")
        for issue in issues:
            logger.info("   - {issue}")
        
        logger.info("\n🛠️  Starting migration...")
        
        migration_success = True
        
        # 1. Create missing tables
        if any("package_items table" in issue for issue in issues):
            if not create_package_items_table(cursor):
                migration_success = False
        
        # 2. Add missing columns
        if any("shipping_tracking" in issue for issue in issues):
            if not add_shipping_tracking_columns(cursor):
                migration_success = False
        
        if not migration_success:
            logger.info("❌ Some migrations failed")
            return False
        
        # Commit all changes
        conn.commit()
        logger.info("💾 All changes committed successfully!")
        
        # Final verification
        logger.info("\n🔍 Final verification...")
        final_issues = verify_tables_and_columns(cursor)
        
        if not final_issues:
            logger.info("🎉 All database schema issues have been resolved!")
            return True
        else:
            logger.info("⚠️  Still have {len(final_issues)} unresolved issues:")
            for issue in final_issues:
                logger.info("   - {issue}")
            return False
    
    except Exception as e:
        logger.info("❌ Migration error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if 'conn' in locals() and conn:
            conn.close()
            logger.info("🔌 Database connection closed")

if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("🚀 PythonAnywhere Complete Database Migration")
    logger.info("   Fixes: package_items table + shipping_tracking columns")
    logger.info("=" * 70)
    
    success = fix_pythonanywhere_database()
    
    logger.info("\n" + "=" * 70)
    if success:
        logger.info("🎉 SUCCESS! All database migrations completed.")
        logger.info("   • package_items table created")
        logger.info("   • shipping_tracking_3, 4, 5 columns added")
        logger.info("   • Database schema is now up to date")
        logger.info("\n📝 Next steps:")
        logger.info("   1. Restart your PythonAnywhere web app")
        logger.info("   2. Test opening tickets - errors should be resolved")
        sys.exit(0)
    else:
        logger.info("💥 FAILED! Migration could not be completed.")
        logger.info("   Please check the error messages above.")
        logger.info("   You may need to manually fix remaining issues.")
        sys.exit(1) 