#!/usr/bin/env python3
"""
Script to create the test user for iOS app authentication
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models.user import User, UserType
from models.permission import Permission

def create_test_user():
    """Create test user with username 'test' and password '123456'"""
    db = SessionLocal()
    try:
        # Check if test user already exists
        existing_user = db.query(User).filter(User.username == 'test').first()
        if existing_user:
            print("✅ Test user already exists, updating password...")
            existing_user.set_password('123456')
            db.commit()
            
            print(f"👤 Username: {existing_user.username}")
            print(f"🔑 Password: 123456")
            print(f"📋 User Type: {existing_user.user_type.value}")
            print(f"🆔 User ID: {existing_user.id}")
            
            return True
        
        # Create new test user
        test_user = User(
            username='test',
            email='test@example.com',
            user_type=UserType.CLIENT
        )
        test_user.set_password('123456')
        
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        
        print("✅ Test user created successfully!")
        print(f"👤 Username: {test_user.username}")
        print(f"📧 Email: {test_user.email}")
        print(f"🔑 Password: 123456")
        print(f"📋 User Type: {test_user.user_type.value}")
        print(f"🆔 User ID: {test_user.id}")
        
        # Test password verification
        if test_user.check_password('123456'):
            print("✅ Password verification successful!")
            return True
        else:
            print("❌ Password verification failed!")
            return False
        
    except Exception as e:
        print(f"❌ Error creating user: {str(e)}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("👤 Creating test user for iOS app...")
    print("=" * 50)
    
    success = create_test_user()
    
    print("=" * 50)
    if success:
        print("✅ SUCCESS! Test user ready for iOS app")
        print()
        print("📱 iOS App Login Credentials:")
        print("   Username: test")
        print("   Password: 123456")
        print("   User Type: CLIENT")
    else:
        print("❌ FAILED! Could not create test user")