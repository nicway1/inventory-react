#!/usr/bin/env python3
"""
Migration script to add inventory audit permissions to permissions table
"""

import sqlite3
import os
import logging
from models.enums import UserType

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def migrate_database():
    """Add inventory audit permissions to permissions table"""
    
    db_path = "inventory.db"
    
    if not os.path.exists(db_path):
        logger.info("Database file not found. Skipping migration.")
        return
    
    logger.info("🔄 Starting audit permissions migration...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the new columns already exist
        cursor.execute("PRAGMA table_info(permissions)")
        columns = [column[1] for column in cursor.fetchall()]
        
        new_columns = [
            'can_access_inventory_audit',
            'can_start_inventory_audit', 
            'can_view_audit_reports'
        ]
        
        columns_to_add = [col for col in new_columns if col not in columns]
        
        if not columns_to_add:
            logger.info("✅ Audit permission columns already exist. Migration skipped.")
            return
        
        # Add the new columns
        for column in columns_to_add:
            cursor.execute(f"ALTER TABLE permissions ADD COLUMN {column} BOOLEAN DEFAULT 0")
            logger.info(f"✅ Successfully added {column} column to permissions table")
        
        # Update existing permissions with default values based on user type
        permission_defaults = {
            'SUPER_ADMIN': {
                'can_access_inventory_audit': 1,
                'can_start_inventory_audit': 1,
                'can_view_audit_reports': 1
            },
            'COUNTRY_ADMIN': {
                'can_access_inventory_audit': 1,
                'can_start_inventory_audit': 1,
                'can_view_audit_reports': 1
            },
            'SUPERVISOR': {
                'can_access_inventory_audit': 1,
                'can_start_inventory_audit': 1,
                'can_view_audit_reports': 1
            },
            'CLIENT': {
                'can_access_inventory_audit': 0,
                'can_start_inventory_audit': 0,
                'can_view_audit_reports': 0
            }
        }
        
        # Update permissions for each user type
        for user_type, permissions in permission_defaults.items():
            for permission, value in permissions.items():
                if permission in columns_to_add:
                    cursor.execute(f"""
                        UPDATE permissions 
                        SET {permission} = ? 
                        WHERE user_type = ?
                    """, (value, user_type))
                    logger.info(f"✅ Set {permission} = {value} for {user_type}")
        
        conn.commit()
        logger.info("✅ Migration completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()