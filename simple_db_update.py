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
    print("=" * 60)
    print("🔄 SIMPLE DATABASE UPDATE SCRIPT")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        print("\n🔄 Setting up database connection...")
        
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
        
        print("✅ Database connection established")
        
        print("\n🔄 Creating CategoryDisplayConfig table...")
        
        # Create the table
        CategoryDisplayConfig.__table__.create(engine, checkfirst=True)
        
        print("✅ CategoryDisplayConfig table created")
        
        print("\n🔄 Initializing predefined categories...")
        
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
                print(f"✅ Initialized {len(TicketCategory)} predefined categories")
            else:
                print(f"✅ Found {existing_count} existing predefined categories - skipping initialization")
            
        finally:
            session.close()
        
        print("\n" + "=" * 60)
        print("✅ DATABASE UPDATE COMPLETED!")
        print("=" * 60)
        
        print("\n📋 FINAL STEP - Manual Action Required:")
        print("   1. Go to your PythonAnywhere Web tab")
        print("   2. Click the 'Reload' button for your web app")
        print("   3. Wait for the green 'Running' status")
        
        print("\n🎉 Your ticket category management is now ready!")
        print("\n📝 What's updated:")
        print("   ✅ CategoryDisplayConfig table created")
        print("   ✅ Predefined categories initialized")
        print("   ✅ Database schema is up to date")
        
        print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return True
        
    except Exception as e:
        print(f"\n❌ DATABASE UPDATE FAILED!")
        print(f"Error: {str(e)}")
        print("\n🔧 Troubleshooting:")
        print("   1. Make sure you're in the correct directory")
        print("   2. Check if database file exists and is writable")
        print("   3. Verify all required model files are present")
        return False

if __name__ == "__main__":
    success = update_database()
    if not success:
        sys.exit(1) 