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
    
    print("🔧 Starting database repair process...")
    
    # Step 1: Create backup of corrupted database
    if os.path.exists(db_path):
        print(f"📦 Creating backup: {backup_path}")
        try:
            shutil.copy2(db_path, backup_path)
            print("✅ Backup created successfully")
        except Exception as e:
            print(f"❌ Failed to create backup: {e}")
            return False
    
    # Step 2: Try to repair using .dump and restore
    print("🔄 Attempting to repair database...")
    
    try:
        # Connect to corrupted database
        conn_old = sqlite3.connect(db_path)
        
        # Create new database
        new_db_path = "inventory_repaired.db"
        conn_new = sqlite3.connect(new_db_path)
        
        # Dump and restore
        print("📤 Dumping database content...")
        for line in conn_old.iterdump():
            try:
                conn_new.execute(line)
            except sqlite3.Error as e:
                print(f"⚠️  Skipping corrupted line: {e}")
                continue
        
        conn_new.commit()
        conn_old.close()
        conn_new.close()
        
        # Replace old database with repaired one
        print("🔄 Replacing corrupted database with repaired version...")
        os.replace(new_db_path, db_path)
        
        print("✅ Database repair completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database repair failed: {e}")
        return False

def verify_database():
    """Verify the repaired database works"""
    print("🔍 Verifying repaired database...")
    
    try:
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        
        # Test basic queries
        cursor.execute("SELECT COUNT(*) FROM tickets")
        ticket_count = cursor.fetchone()[0]
        print(f"✅ Tickets table: {ticket_count} records")
        
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"✅ Users table: {user_count} records")
        
        cursor.execute("SELECT COUNT(*) FROM assets")
        asset_count = cursor.fetchone()[0]
        print(f"✅ Assets table: {asset_count} records")
        
        conn.close()
        print("✅ Database verification successful!")
        return True
        
    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        return False

def clean_temp_files():
    """Clean up temporary database files that might cause corruption"""
    temp_files = ["inventory.db-wal", "inventory.db-shm"]
    
    for temp_file in temp_files:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
                print(f"🗑️  Removed temp file: {temp_file}")
            except Exception as e:
                print(f"⚠️  Could not remove {temp_file}: {e}")

if __name__ == "__main__":
    print("=" * 50)
    print("🔧 SQLite Database Repair Tool")
    print("=" * 50)
    
    # Clean temp files first
    clean_temp_files()
    
    # Repair database
    if repair_database():
        # Verify repair worked
        if verify_database():
            print("\n🎉 Database repair completed successfully!")
            print("Your application should now work properly.")
        else:
            print("\n❌ Database repair verification failed.")
            print("You may need to restore from a backup or recreate the database.")
    else:
        print("\n❌ Database repair failed.")
        print("Consider restoring from a backup or recreating the database.")
    
    print("\n📋 Next steps:")
    print("1. Upload this script to PythonAnywhere")
    print("2. Run: python3 repair_database.py")
    print("3. Restart your web app")
    print("4. Test the application") 