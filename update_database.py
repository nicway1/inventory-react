#!/usr/bin/env python3
"""
Database Update Script for PythonAnywhere
Run this script to update your database schema with the new CategoryDisplayConfig table.
"""

import sys
from datetime import datetime

def update_database():
    """Update database schema"""
    print("=" * 60)
    print("🔄 DATABASE UPDATE SCRIPT")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        print("\n🔄 Initializing database with new schema...")
        
        # Import and run database initialization
        from app import app
        from database import init_db
        
        with app.app_context():
            init_db()
            print("✅ Database schema updated successfully!")
            
        print("\n" + "=" * 60)
        print("✅ DATABASE UPDATE COMPLETED!")
        print("=" * 60)
        
        print("\n📋 FINAL STEP - Manual Action Required:")
        print("   1. Go to your PythonAnywhere Web tab")
        print("   2. Click the 'Reload' button for your web app")
        print("   3. Wait for the green 'Running' status")
        
        print("\n🎉 Your ticket category management is now ready!")
        print("\n📝 What's updated:")
        print("   ✅ New CategoryDisplayConfig table created")
        print("   ✅ 15 predefined categories initialized")
        print("   ✅ Categories can be enabled/disabled properly")
        print("   ✅ Database is ready for the new features")
        
        print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return True
        
    except Exception as e:
        print(f"\n❌ DATABASE UPDATE FAILED!")
        print(f"Error: {str(e)}")
        print("\n🔧 Troubleshooting:")
        print("   1. Make sure you're in the correct directory")
        print("   2. Check if all Python dependencies are installed")
        print("   3. Verify database permissions")
        return False

if __name__ == "__main__":
    success = update_database()
    if not success:
        sys.exit(1) 