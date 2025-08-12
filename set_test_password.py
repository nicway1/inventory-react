#!/usr/bin/env python3
"""
Script to set the password for the test user to 123456
This ensures the iOS app can authenticate properly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models.user import User
from werkzeug.security import generate_password_hash

def set_test_password():
    """Set password for test user to 123456"""
    db = SessionLocal()
    try:
        # Find test user
        test_user = db.query(User).filter(User.username == 'test').first()
        
        if not test_user:
            print("❌ Test user not found")
            return False
        
        # Set password to 123456
        test_user.set_password('123456')
        db.commit()
        
        print("✅ Test user password set successfully!")
        print(f"👤 Username: test")
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
        print(f"❌ Error setting password: {str(e)}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("🔐 Setting test user password...")
    print("=" * 40)
    
    success = set_test_password()
    
    print("=" * 40)
    if success:
        print("✅ SUCCESS! Test user ready for iOS app login")
        print()
        print("📱 iOS App Login Credentials:")
        print("   Username: test")
        print("   Password: 123456")
    else:
        print("❌ FAILED! Could not set test user password")