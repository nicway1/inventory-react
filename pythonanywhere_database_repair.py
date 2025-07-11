#!/usr/bin/env python3
"""
PythonAnywhere Database Repair Script
Diagnoses and repairs corrupted SQLite database issues.

This script addresses the "file is not a database" error by:
1. Checking database file integrity
2. Attempting to recover from corruption
3. Restoring from backup if necessary
4. Recreating database structure if needed

Run this script on PythonAnywhere to fix database corruption issues.
"""
import sqlite3
import os
import sys
import shutil
from datetime import datetime

def check_file_exists_and_size(db_path):
    """Check if database file exists and get its size"""
    logger.info("🔍 Checking database file: {db_path}")
    
    if not os.path.exists(db_path):
        logger.info("❌ Database file does not exist: {db_path}")
        return False, 0
    
    file_size = os.path.getsize(db_path)
    logger.info("📁 File exists, size: {file_size} bytes")
    
    if file_size == 0:
        logger.info("⚠️  WARNING: Database file is empty (0 bytes)")
        return True, 0
    elif file_size < 1024:
        logger.info("⚠️  WARNING: Database file is very small (< 1KB)")
    
    return True, file_size

def test_database_integrity(db_path):
    """Test if the database file can be opened and is valid"""
    logger.info("🔍 Testing database integrity...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Try a simple query
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        logger.info("✅ Database is readable, found {len(tables)} tables")
        for table in tables[:5]:  # Show first 5 tables
            logger.info("   - {table[0]}")
        if len(tables) > 5:
            logger.info("   ... and {len(tables) - 5} more tables")
        
        conn.close()
        return True, len(tables)
        
    except sqlite3.DatabaseError as e:
        logger.info("❌ Database corruption detected: {e}")
        return False, 0
    except Exception as e:
        logger.info("❌ Unexpected error reading database: {e}")
        return False, 0

def find_backup_files():
    """Find available backup files"""
    logger.info("🔍 Looking for backup files...")
    
    backup_patterns = [
        '/home/nicway2/inventory/backups/',
        '/home/nicway2/inventory/',
        './'
    ]
    
    backup_files = []
    
    for backup_dir in backup_patterns:
        if os.path.exists(backup_dir):
            logger.info("   Checking: {backup_dir}")
            for file in os.listdir(backup_dir):
                if 'backup' in file.lower() and file.endswith('.db'):
                    full_path = os.path.join(backup_dir, file)
                    file_size = os.path.getsize(full_path)
                    backup_files.append((full_path, file_size))
                    logger.info("   Found backup: {file} ({file_size} bytes)")
    
    # Sort by file size (larger is probably better)
    backup_files.sort(key=lambda x: x[1], reverse=True)
    
    return backup_files

def restore_from_backup(backup_path, target_path):
    """Restore database from backup file"""
    logger.info("🔄 Restoring database from backup...")
    logger.info("   Source: {backup_path}")
    logger.info("   Target: {target_path}")
    
    try:
        # Test the backup file first
        is_valid, table_count = test_database_integrity(backup_path)
        if not is_valid:
            logger.info("❌ Backup file is also corrupted: {backup_path}")
            return False
        
        logger.info("✅ Backup file is valid ({table_count} tables)")
        
        # Create backup of corrupted file
        corrupted_backup = f"{target_path}.corrupted.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if os.path.exists(target_path):
            shutil.move(target_path, corrupted_backup)
            logger.info("📦 Moved corrupted file to: {corrupted_backup}")
        
        # Copy backup to target location
        shutil.copy2(backup_path, target_path)
        logger.info("✅ Restored database from backup")
        
        # Verify the restored database
        is_valid, table_count = test_database_integrity(target_path)
        if is_valid:
            logger.info("✅ Restored database is working ({table_count} tables)")
            return True
        else:
            logger.info("❌ Restored database is still corrupted")
            return False
            
    except Exception as e:
        logger.info("❌ Error during backup restoration: {e}")
        return False

def create_minimal_database(db_path):
    """Create a minimal database with basic structure"""
    logger.info("🔧 Creating minimal database structure...")
    
    try:
        # Remove corrupted file
        if os.path.exists(db_path):
            corrupted_backup = f"{db_path}.corrupted.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.move(db_path, corrupted_backup)
            logger.info("📦 Moved corrupted file to: {corrupted_backup}")
        
        # Create new database with basic tables
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create essential tables - you'll need to add the complete schema
        essential_tables = [
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                user_type TEXT DEFAULT 'regular',
                company_id INTEGER,
                assigned_country TEXT,
                role TEXT DEFAULT 'user',
                theme_preference TEXT DEFAULT 'light',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME
            )
            """,
            """
            CREATE TABLE tickets (
                id INTEGER PRIMARY KEY,
                subject TEXT NOT NULL,
                description TEXT,
                requester_id INTEGER NOT NULL,
                status TEXT DEFAULT 'NEW',
                priority TEXT DEFAULT 'MEDIUM',
                category TEXT,
                asset_id INTEGER,
                assigned_to_id INTEGER,
                queue_id INTEGER,
                accessory_id INTEGER,
                rma_status TEXT,
                repair_status TEXT,
                country TEXT,
                damage_description TEXT,
                apple_diagnostics TEXT,
                image_path TEXT,
                return_description TEXT,
                return_tracking TEXT,
                return_carrier TEXT DEFAULT 'singpost',
                replacement_tracking TEXT,
                warranty_number TEXT,
                serial_number TEXT,
                shipping_address TEXT,
                shipping_tracking TEXT,
                shipping_carrier TEXT DEFAULT 'singpost',
                customer_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME,
                shipping_status TEXT DEFAULT 'Pending',
                return_status TEXT DEFAULT 'Pending',
                replacement_status TEXT DEFAULT 'Pending',
                shipping_tracking_2 TEXT,
                shipping_carrier_2 TEXT,
                shipping_status_2 TEXT DEFAULT 'Pending',
                shipping_tracking_3 TEXT,
                shipping_carrier_3 TEXT,
                shipping_status_3 TEXT DEFAULT 'Pending',
                shipping_tracking_4 TEXT,
                shipping_carrier_4 TEXT,
                shipping_status_4 TEXT DEFAULT 'Pending',
                shipping_tracking_5 TEXT,
                shipping_carrier_5 TEXT,
                shipping_status_5 TEXT DEFAULT 'Pending',
                packing_list_path TEXT,
                asset_csv_path TEXT,
                notes TEXT
            )
            """,
            """
            CREATE TABLE package_items (
                id INTEGER PRIMARY KEY,
                ticket_id INTEGER NOT NULL,
                package_number INTEGER NOT NULL,
                asset_id INTEGER,
                accessory_id INTEGER,
                quantity INTEGER DEFAULT 1,
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME
            )
            """
        ]
        
        for table_sql in essential_tables:
            cursor.execute(table_sql)
            logger.info("   ✅ Created table")
        
        # Create admin user
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, user_type, role)
            VALUES ('admin', 'admin@truelog.com.sg', 'scrypt:32768:8:1$J8wJ7LzK8j6rXK8w$9ea1b7a8d4f5c6e7b8a9d0c1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7e8f9a0b1c2d3e4', 'admin', 'admin')
        """)
        
        conn.commit()
        conn.close()
        
        logger.info("✅ Created minimal database with essential tables")
        return True
        
    except Exception as e:
        logger.info("❌ Error creating minimal database: {e}")
        return False

def repair_database():
    """Main database repair function"""
    # PythonAnywhere database path
    db_path = '/home/nicway2/inventory/inventory.db'
    
    logger.info("=" * 70)
    logger.info("🚀 PythonAnywhere Database Repair Tool")
    logger.info("   Fixes: 'file is not a database' corruption errors")
    logger.info("=" * 70)
    
    # Step 1: Check file existence and size
    file_exists, file_size = check_file_exists_and_size(db_path)
    
    if not file_exists:
        logger.info("\n🔧 Database file missing, will create new one...")
        return create_minimal_database(db_path)
    
    # Step 2: Test database integrity
    is_valid, table_count = test_database_integrity(db_path)
    
    if is_valid:
        logger.info("\n✅ Database is actually working fine!")
        logger.info("   The error might be intermittent or already resolved.")
        return True
    
    # Step 3: Database is corrupted, try to find backups
    logger.info("\n💥 Database is corrupted, looking for backups...")
    backup_files = find_backup_files()
    
    if backup_files:
        logger.info("\n🔄 Found {len(backup_files)} backup files, trying restoration...")
        for backup_path, backup_size in backup_files:
            logger.info("\n   Trying backup: {os.path.basename(backup_path)} ({backup_size} bytes)")
            if restore_from_backup(backup_path, db_path):
                logger.info("✅ Successfully restored from backup!")
                return True
            else:
                logger.info("❌ This backup didn't work, trying next...")
    
    # Step 4: No good backups, create minimal database
    logger.info("\n⚠️  No usable backups found, creating minimal database...")
    return create_minimal_database(db_path)

if __name__ == "__main__":
    success = repair_database()
    
    logger.info("\n" + "=" * 70)
    if success:
        logger.info("🎉 SUCCESS! Database has been repaired.")
        logger.info("\n📝 Next steps:")
        logger.info("   1. Restart your PythonAnywhere web app")
        logger.info("   2. Test the application")
        logger.info("   3. You may need to recreate some data if restored from old backup")
        logger.info("   4. Consider setting up automated backups")
        sys.exit(0)
    else:
        logger.info("💥 FAILED! Could not repair the database.")
        logger.info("\n📝 Manual intervention required:")
        logger.info("   1. Check PythonAnywhere disk space")
        logger.info("   2. Contact PythonAnywhere support if needed")
        logger.info("   3. Consider uploading a working database from local development")
        sys.exit(1) 