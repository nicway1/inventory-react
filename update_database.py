#!/usr/bin/env python3
"""
Database Update Script for PythonAnywhere
Run this script to update your database schema with the new CategoryDisplayConfig table.
"""

import sys
from datetime import datetime

def update_database():
    """Update database schema"""
    logger.info("=" * 60)
    logger.info("🔄 DATABASE UPDATE SCRIPT")
    logger.info("=" * 60)
    logger.info("Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        logger.info("\n🔄 Initializing database with new schema...")
        
        # Import and run database initialization
        from app import app
        from database import init_db
        
        with app.app_context():
            init_db()
            logger.info("✅ Database schema updated successfully!")
            
        logger.info("\n" + "=" * 60)
        logger.info("✅ DATABASE UPDATE COMPLETED!")
        logger.info("=" * 60)
        
        logger.info("\n📋 FINAL STEP - Manual Action Required:")
        logger.info("   1. Go to your PythonAnywhere Web tab")
        logger.info("   2. Click the 'Reload' button for your web app")
        logger.info("   3. Wait for the green 'Running' status")
        
        logger.info("\n🎉 Your ticket category management is now ready!")
        logger.info("\n📝 What's updated:")
        logger.info("   ✅ New CategoryDisplayConfig table created")
        logger.info("   ✅ 15 predefined categories initialized")
        logger.info("   ✅ Categories can be enabled/disabled properly")
        logger.info("   ✅ Database is ready for the new features")
        
        logger.info("\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return True
        
    except Exception as e:
        logger.info("\n❌ DATABASE UPDATE FAILED!")
        logger.info("Error: {str(e)}")
        logger.info("\n🔧 Troubleshooting:")
        logger.info("   1. Make sure you're in the correct directory")
        logger.info("   2. Check if all Python dependencies are installed")
        logger.info("   3. Verify database permissions")
        return False

if __name__ == "__main__":
    success = update_database()
    if not success:
        sys.exit(1) 