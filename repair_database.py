#!/usr/bin/env python3
"""
Database repair script for corrupted SQLite database
Run this on PythonAnywhere to fix the corrupted database
"""

import sqlite3
import os
import shutil
from datetime import datetime

def repair_database():
    """Repair corrupted SQLite database"""
    
    db_path = "inventory.db"
    backup_path = f"inventory_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    logger.info("🔧 Starting database repair process...")
    
    # Step 1: Create backup of corrupted database
    if os.path.exists(db_path):
        logger.info("📦 Creating backup: {backup_path}")
        try:
            shutil.copy2(db_path, backup_path)
            logger.info("✅ Backup created successfully")
        except Exception as e:
            logger.info("❌ Failed to create backup: {e}")
            return False
    
    # Step 2: Try to repair using .dump and restore
    logger.info("🔄 Attempting to repair database...")
    
    try:
        # Connect to corrupted database
        conn_old = sqlite3.connect(db_path)
        
        # Create new database
        new_db_path = "inventory_repaired.db"
        conn_new = sqlite3.connect(new_db_path)
        
        # Dump and restore
        logger.info("📤 Dumping database content...")
        for line in conn_old.iterdump():
            try:
                conn_new.execute(line)
            except sqlite3.Error as e:
                logger.info("⚠️  Skipping corrupted line: {e}")
                continue
        
        conn_new.commit()
        conn_old.close()
        conn_new.close()
        
        # Replace old database with repaired one
        logger.info("🔄 Replacing corrupted database with repaired version...")
        os.replace(new_db_path, db_path)
        
        logger.info("✅ Database repair completed successfully!")
        return True
        
    except Exception as e:
        logger.info("❌ Database repair failed: {e}")
        return False

def verify_database():
    """Verify the repaired database works"""
    logger.info("🔍 Verifying repaired database...")
    
    try:
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        
        # Test basic queries
        cursor.execute("SELECT COUNT(*) FROM tickets")
        ticket_count = cursor.fetchone()[0]
        logger.info("✅ Tickets table: {ticket_count} records")
        
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        logger.info("✅ Users table: {user_count} records")
        
        cursor.execute("SELECT COUNT(*) FROM assets")
        asset_count = cursor.fetchone()[0]
        logger.info("✅ Assets table: {asset_count} records")
        
        conn.close()
        logger.info("✅ Database verification successful!")
        return True
        
    except Exception as e:
        logger.info("❌ Database verification failed: {e}")
        return False

def clean_temp_files():
    """Clean up temporary database files that might cause corruption"""
    temp_files = ["inventory.db-wal", "inventory.db-shm"]
    
    for temp_file in temp_files:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
                logger.info("🗑️  Removed temp file: {temp_file}")
            except Exception as e:
                logger.info("⚠️  Could not remove {temp_file}: {e}")

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("🔧 SQLite Database Repair Tool")
    logger.info("=" * 50)
    
    # Clean temp files first
    clean_temp_files()
    
    # Repair database
    if repair_database():
        # Verify repair worked
        if verify_database():
            logger.info("\n🎉 Database repair completed successfully!")
            logger.info("Your application should now work properly.")
        else:
            logger.info("\n❌ Database repair verification failed.")
            logger.info("You may need to restore from a backup or recreate the database.")
    else:
        logger.info("\n❌ Database repair failed.")
        logger.info("Consider restoring from a backup or recreating the database.")
    
    logger.info("\n📋 Next steps:")
    logger.info("1. Upload this script to PythonAnywhere")
    logger.info("2. Run: python3 repair_database.py")
    logger.info("3. Restart your web app")
    logger.info("4. Test the application") 