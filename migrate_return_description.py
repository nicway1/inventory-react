#!/usr/bin/env python3
"""
Migration script to add return_description column to tickets table
Run this on PythonAnywhere to fix the database schema
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, '/home/nicway1/mysite')  # Adjust this path for PythonAnywhere

from sqlalchemy import text, create_engine
from database import SessionLocal, engine
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database():
    """Add return_description column to tickets table"""
    
    logger.info("Starting database migration...")
    
    # Create a session
    session = SessionLocal()
    
    try:
        # Check if column already exists
        result = session.execute(text("""
            SELECT COUNT(*) 
            FROM pragma_table_info('tickets') 
            WHERE name = 'return_description'
        """))
        
        column_exists = result.scalar() > 0
        
        if column_exists:
            logger.info("✅ return_description column already exists - no migration needed")
            return True
            
        logger.info("🔄 Adding return_description column to tickets table...")
        
        # Add the return_description column
        session.execute(text("""
            ALTER TABLE tickets 
            ADD COLUMN return_description VARCHAR(1000)
        """))
        
        # Commit the changes
        session.commit()
        
        # Verify the column was added
        result = session.execute(text("""
            SELECT COUNT(*) 
            FROM pragma_table_info('tickets') 
            WHERE name = 'return_description'
        """))
        
        column_exists_after = result.scalar() > 0
        
        if column_exists_after:
            logger.info("✅ Migration completed successfully!")
            logger.info("✅ return_description column added to tickets table")
            return True
        else:
            logger.error("❌ Migration failed - column was not added")
            return False
            
    except Exception as e:
        logger.error(f"❌ Migration failed with error: {str(e)}")
        session.rollback()
        return False
        
    finally:
        session.close()

def verify_migration():
    """Verify that the migration was successful"""
    
    logger.info("Verifying migration...")
    session = SessionLocal()
    
    try:
        # Check all columns in tickets table
        result = session.execute(text("""
            SELECT name 
            FROM pragma_table_info('tickets')
            ORDER BY cid
        """))
        
        columns = [row[0] for row in result.fetchall()]
        
        logger.info(f"Current columns in tickets table: {', '.join(columns)}")
        
        if 'return_description' in columns:
            logger.info("✅ Verification successful - return_description column exists")
            return True
        else:
            logger.error("❌ Verification failed - return_description column missing")
            return False
            
    except Exception as e:
        logger.error(f"❌ Verification failed with error: {str(e)}")
        return False
        
    finally:
        session.close()

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("DATABASE MIGRATION: Add return_description column")
    logger.info("=" * 60)
    
    # Run migration
    if migrate_database():
        # Verify migration
        if verify_migration():
            logger.info("🎉 Migration completed successfully!")
            logger.info("You can now reload your PythonAnywhere web app")
        else:
            logger.error("Migration verification failed")
            sys.exit(1)
    else:
        logger.error("Migration failed")
        sys.exit(1) 