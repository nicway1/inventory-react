#!/usr/bin/env python3
"""
Check super admins in the database
"""

from database import SessionLocal
from models.user import User, UserType

def check_super_admins():
    """List all super admins"""
    db_session = SessionLocal()
    
    try:
        print("=" * 60)
        print("Checking Super Admins")
        print("=" * 60)
        
        # Get all users
        all_users = db_session.query(User).all()
        print(f"\nTotal users in database: {len(all_users)}")
        
        # Get super admins
        super_admins = db_session.query(User).filter(User.user_type == UserType.SUPER_ADMIN).all()
        
        print(f"Super admins found: {len(super_admins)}\n")
        
        if super_admins:
            print("Super Admin List:")
            print("-" * 60)
            for admin in super_admins:
                print(f"  ID: {admin.id}")
                print(f"  Username: {admin.username}")
                print(f"  Email: {admin.email}")
                print(f"  Type: {admin.user_type.value if hasattr(admin.user_type, 'value') else admin.user_type}")
                print("-" * 60)
        else:
            print("⚠ No super admins found!")
            print("\nAll users and their types:")
            print("-" * 60)
            for user in all_users:
                user_type = user.user_type.value if hasattr(user.user_type, 'value') else user.user_type
                print(f"  {user.username} ({user.email}) - Type: {user_type}")
        
        print("\n" + "=" * 60)
        
    finally:
        db_session.close()

if __name__ == '__main__':
    check_super_admins()
