#!/usr/bin/env python3
"""
Simple Database Update Script for PythonAnywhere
This script bypasses app imports to avoid missing function issues.
"""

import sys
import os
from datetime import datetime

def update_database():
    """Update database schema without importing the full app"""
    logger.info("=" * 60)
    logger.info("🔄 SIMPLE DATABASE UPDATE SCRIPT")
    logger.info("=" * 60)
    logger.info("Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        logger.info("\n🔄 Setting up database connection...")
        
        # Add the project directory to Python path
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Import database components directly
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker
        from models.ticket_category_config import CategoryDisplayConfig
        from models.ticket import TicketCategory
        
        # Create database engine (adjust path if needed)
        DATABASE_URL = 'sqlite:///inventory.db'  # Adjust this path if needed
        engine = create_engine(DATABASE_URL)
        
        logger.info("✅ Database connection established")
        
        logger.info("\n🔄 Creating CategoryDisplayConfig table...")
        
        # Create the table
        CategoryDisplayConfig.__table__.create(engine, checkfirst=True)
        
        logger.info("✅ CategoryDisplayConfig table created")
        
        logger.info("\n🔄 Initializing predefined categories...")
        
        # Create session
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # Check if categories already exist
            existing_count = session.query(CategoryDisplayConfig).filter_by(is_predefined=True).count()
            
            if existing_count == 0:
                # Initialize predefined categories
                for i, category in enumerate(TicketCategory, 1):
                    config = CategoryDisplayConfig(
                        category_key=category.name,
                        display_name=category.value,
                        is_enabled=True,
                        is_predefined=True,
                        sort_order=i
                    )
                    session.add(config)
                
                session.commit()
                logger.info("✅ Initialized {len(TicketCategory)} predefined categories")
            else:
                logger.info("✅ Found {existing_count} existing predefined categories - skipping initialization")
            
        finally:
            session.close()
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ DATABASE UPDATE COMPLETED!")
        logger.info("=" * 60)
        
        logger.info("\n📋 FINAL STEP - Manual Action Required:")
        logger.info("   1. Go to your PythonAnywhere Web tab")
        logger.info("   2. Click the 'Reload' button for your web app")
        logger.info("   3. Wait for the green 'Running' status")
        
        logger.info("\n🎉 Your ticket category management is now ready!")
        logger.info("\n📝 What's updated:")
        logger.info("   ✅ CategoryDisplayConfig table created")
        logger.info("   ✅ Predefined categories initialized")
        logger.info("   ✅ Database schema is up to date")
        
        logger.info("\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return True
        
    except Exception as e:
        logger.info("\n❌ DATABASE UPDATE FAILED!")
        logger.info("Error: {str(e)}")
        logger.info("\n🔧 Troubleshooting:")
        logger.info("   1. Make sure you're in the correct directory")
        logger.info("   2. Check if database file exists and is writable")
        logger.info("   3. Verify all required model files are present")
        return False

if __name__ == "__main__":
    success = update_database()
    if not success:
        sys.exit(1) 