#!/usr/bin/env python3
"""
Script to create an API key for mobile app access
This creates an API key with the permissions needed for the iOS app
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models.api_key import APIKey
from models.user import User
from utils.api_key_manager import APIKeyManager
from datetime import datetime

def create_mobile_api_key():
    """Create an API key for mobile app access"""
    db = SessionLocal()
    try:
        api_manager = APIKeyManager()
        
        # Get admin user (or create if doesn't exist)
        admin_user = db.query(User).filter(User.username == 'admin').first()
        if not admin_user:
            print("❌ Admin user not found. Please create an admin user first.")
            return None
        
        # Define mobile app permissions
        mobile_permissions = [
            'tickets:read',
            'tickets:write', 
            'users:read',
            'inventory:read',
            'sync:read'
        ]
        
        # Create API key
        success, message, api_key_obj = api_manager.generate_key(
            name="iOS Mobile App",
            permissions=mobile_permissions,
            created_by_id=admin_user.id,
            expires_at=None  # No expiration
        )
        
        if success and api_key_obj:
            print("✅ Mobile API key created successfully!")
            print(f"📱 API Key: {api_key_obj.key}")
            print(f"🔑 Key ID: {api_key_obj.id}")
            print(f"👤 Created by: {admin_user.username}")
            print(f"📅 Created: {datetime.now().isoformat()}")
            print(f"🔐 Permissions: {', '.join(mobile_permissions)}")
            print()
            print("🎯 Use this API key in your iOS app:")
            print(f"   X-API-Key: {api_key_obj.key}")
            print()
            return api_key_obj.key
        else:
            print(f"❌ Failed to create API key: {message}")
            return None
            
    except Exception as e:
        print(f"❌ Error creating API key: {str(e)}")
        return None
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Creating mobile API key...")
    print("=" * 50)
    
    api_key = create_mobile_api_key()
    
    if api_key:
        print("=" * 50)
        print("✅ SUCCESS! Your iOS app is ready to use the API.")
        print()
        print("📋 Test your API key:")
        print(f"curl -H \"X-API-Key: {api_key}\" https://inventory.truelog.com.sg/api/v1/health")
    else:
        print("=" * 50) 
        print("❌ FAILED! Could not create API key.")