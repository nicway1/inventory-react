#!/usr/bin/env python3
"""
Database recreation script - use if repair fails
This will recreate the database schema from scratch
"""

import os
import sys
import sqlite3
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def backup_corrupted_db():
    """Backup the corrupted database before recreation"""
    db_path = "inventory.db"
    if os.path.exists(db_path):
        backup_path = f"inventory_corrupted_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        try:
            os.rename(db_path, backup_path)
            logger.info("📦 Corrupted database backed up as: {backup_path}")
            return True
        except Exception as e:
            logger.info("❌ Failed to backup corrupted database: {e}")
            return False
    return True

def recreate_database():
    """Recreate database from scratch using the app's initialization"""
    logger.info("🔄 Recreating database from scratch...")
    
    try:
        # Remove any existing database files
        db_files = ["inventory.db", "inventory.db-wal", "inventory.db-shm"]
        for db_file in db_files:
            if os.path.exists(db_file):
                os.remove(db_file)
                logger.info("🗑️  Removed: {db_file}")
        
        # Import and initialize the app
        from app import create_app
        from utils.db_setup import init_db
        
        logger.info("🏗️  Creating new database...")
        app = create_app()
        
        with app.app_context():
            # Initialize database
            init_db()
            logger.info("✅ Database schema created successfully!")
            
            # Create default admin user
            from models.user import User, UserType
            from utils.store_instances import db_manager
            
            db_session = db_manager.get_session()
            
            # Check if admin user exists
            admin_user = db_session.query(User).filter_by(username='admin').first()
            if not admin_user:
                logger.info("👤 Creating default admin user...")
                admin_user = User(
                    username='admin',
                    email='admin@lunacomputer.com',
                    password_hash='$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6hsxq5/Qe.',  # password: admin
                    user_type=UserType.SUPER_ADMIN,
                    is_verified=True,
                    first_name='Admin',
                    last_name='User'
                )
                db_session.add(admin_user)
                db_session.commit()
                logger.info("✅ Default admin user created (username: admin, password: admin)")
            
            db_session.close()
            
        logger.info("✅ Database recreation completed successfully!")
        return True
        
    except Exception as e:
        logger.info("❌ Database recreation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_new_database():
    """Verify the new database works"""
    logger.info("🔍 Verifying new database...")
    
    try:
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        
        expected_tables = ['users', 'tickets', 'assets', 'customer_users', 'companies']
        
        for table in expected_tables:
            if table in table_names:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                logger.info("✅ {table} table: {count} records")
            else:
                logger.info("⚠️  {table} table: missing")
        
        conn.close()
        logger.info("✅ Database verification completed!")
        return True
        
    except Exception as e:
        logger.info("❌ Database verification failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("🔄 Database Recreation Tool")
    logger.info("=" * 50)
    logger.info("⚠️  WARNING: This will delete all existing data!")
    logger.info("Only use this if database repair failed.")
    logger.info("=" * 50)
    
    # Backup corrupted database
    if backup_corrupted_db():
        # Recreate database
        if recreate_database():
            # Verify new database
            if verify_new_database():
                logger.info("\n🎉 Database recreation completed successfully!")
                logger.info("📋 Next steps:")
                logger.info("1. Restart your PythonAnywhere web app")
                logger.info("2. Login with username: admin, password: admin")
                logger.info("3. Create new users and import your data")
            else:
                logger.info("\n❌ Database verification failed.")
        else:
            logger.info("\n❌ Database recreation failed.")
    else:
        logger.info("\n❌ Failed to backup corrupted database.") 