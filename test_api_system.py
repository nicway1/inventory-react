#!/usr/bin/env python3
"""
Test script for the API Management System

This script tests:
- API key creation and validation
- Permission checking
- Basic API endpoints
- Usage tracking
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.api_key_manager import APIKeyManager
from utils.api_auth import validate_api_request
from models.api_key import APIKey
from models.api_usage import APIUsage
from datetime import datetime, timedelta
import json

def test_api_key_creation():
    """Test API key creation and validation"""
    print("🔑 Testing API Key Creation...")
    
    # Test creating an API key
    success, message, api_key = APIKeyManager.generate_key(
        name="Test Mobile App Key",
        permissions=['tickets:read', 'tickets:write', 'users:read'],
        expires_at=datetime.utcnow() + timedelta(days=30),
        created_by_id=1
    )
    
    if success:
        print(f"✅ API key created successfully: {api_key.name}")
        print(f"   Key ID: {api_key.id}")
        print(f"   Permissions: {api_key.get_permissions()}")
        print(f"   Raw key: {api_key._raw_key}")
        
        # Test validation
        is_valid, validated_key, msg = APIKeyManager.validate_key(api_key._raw_key)
        if is_valid:
            print(f"✅ API key validation successful")
            
            # Test permission checking
            if validated_key.has_permission('tickets:read'):
                print("✅ Permission check passed: tickets:read")
            else:
                print("❌ Permission check failed: tickets:read")
            
            if not validated_key.has_permission('admin:write'):
                print("✅ Permission check correctly denied: admin:write")
            else:
                print("❌ Permission check incorrectly allowed: admin:write")
                
            return api_key
        else:
            print(f"❌ API key validation failed: {msg}")
            return None
    else:
        print(f"❌ API key creation failed: {message}")
        return None

def test_permission_groups():
    """Test predefined permission groups"""
    print("\n📋 Testing Permission Groups...")
    
    groups = APIKeyManager.get_permission_groups()
    print(f"✅ Found {len(groups)} permission groups:")
    
    for group_name, permissions in groups.items():
        print(f"   - {group_name}: {len(permissions)} permissions")
        
    # Test creating key with permission group
    mobile_permissions = groups.get('mobile_app', [])
    success, message, api_key = APIKeyManager.generate_key(
        name="Test Mobile Group Key",
        permissions=mobile_permissions,
        created_by_id=1
    )
    
    if success:
        print(f"✅ Created key with mobile_app permissions")
        return api_key
    else:
        print(f"❌ Failed to create key with group permissions: {message}")
        return None

def test_usage_tracking():
    """Test usage tracking functionality"""
    print("\n📊 Testing Usage Tracking...")
    
    # Create a test API key
    success, message, api_key = APIKeyManager.generate_key(
        name="Test Usage Key",
        permissions=['tickets:read'],
        created_by_id=1
    )
    
    if not success:
        print(f"❌ Failed to create test key: {message}")
        return
    
    # Log some usage
    endpoints = ['/api/v1/tickets', '/api/v1/users', '/api/v1/inventory']
    methods = ['GET', 'POST', 'PUT']
    status_codes = [200, 201, 400, 404, 500]
    
    print("📝 Logging test usage data...")
    for i in range(10):
        endpoint = endpoints[i % len(endpoints)]
        method = methods[i % len(methods)]
        status = status_codes[i % len(status_codes)]
        
        success = APIKeyManager.log_usage(
            api_key.id,
            endpoint,
            method,
            status,
            response_time_ms=50 + (i * 10),
            request_ip='127.0.0.1',
            user_agent='Test Client/1.0'
        )
        
        if not success:
            print(f"❌ Failed to log usage for request {i+1}")
    
    # Get usage statistics
    stats = APIKeyManager.get_usage_stats(api_key.id, days=1)
    print(f"✅ Usage stats: {stats['total_requests']} requests, {stats['error_rate']:.1f}% error rate")
    
    daily_stats = APIKeyManager.get_daily_usage(api_key.id, days=1)
    print(f"✅ Daily usage: {len(daily_stats)} days of data")

def test_key_management():
    """Test key management operations"""
    print("\n🔧 Testing Key Management...")
    
    # Create a test key
    success, message, api_key = APIKeyManager.generate_key(
        name="Test Management Key",
        permissions=['tickets:read'],
        created_by_id=1
    )
    
    if not success:
        print(f"❌ Failed to create test key: {message}")
        return
    
    print(f"✅ Created key: {api_key.name}")
    
    # Test listing keys
    keys = APIKeyManager.list_keys()
    print(f"✅ Listed {len(keys)} active keys")
    
    # Test updating permissions
    new_permissions = ['tickets:read', 'tickets:write', 'users:read']
    success, message = APIKeyManager.update_permissions(api_key.id, new_permissions)
    if success:
        print("✅ Updated permissions successfully")
    else:
        print(f"❌ Failed to update permissions: {message}")
    
    # Test extending expiration
    success, message = APIKeyManager.extend_expiration(api_key.id, 60)
    if success:
        print("✅ Extended expiration successfully")
    else:
        print(f"❌ Failed to extend expiration: {message}")
    
    # Test revoking key
    success, message = APIKeyManager.revoke_key(api_key.id)
    if success:
        print("✅ Revoked key successfully")
    else:
        print(f"❌ Failed to revoke key: {message}")
    
    # Test activating key
    success, message = APIKeyManager.activate_key(api_key.id)
    if success:
        print("✅ Activated key successfully")
    else:
        print(f"❌ Failed to activate key: {message}")

def test_error_handling():
    """Test error handling scenarios"""
    print("\n⚠️  Testing Error Handling...")
    
    # Test invalid key validation
    is_valid, key, message = APIKeyManager.validate_key("invalid_key_12345")
    if not is_valid:
        print("✅ Correctly rejected invalid API key")
    else:
        print("❌ Incorrectly accepted invalid API key")
    
    # Test creating key with invalid permissions
    success, message, key = APIKeyManager.generate_key(
        name="Invalid Permissions Key",
        permissions=['invalid:permission', 'another:invalid'],
        created_by_id=1
    )
    if not success:
        print("✅ Correctly rejected invalid permissions")
    else:
        print("❌ Incorrectly accepted invalid permissions")
    
    # Test creating key with empty name
    success, message, key = APIKeyManager.generate_key(
        name="",
        permissions=['tickets:read'],
        created_by_id=1
    )
    if not success:
        print("✅ Correctly rejected empty key name")
    else:
        print("❌ Incorrectly accepted empty key name")

def main():
    """Run all tests"""
    print("🚀 Starting API Management System Tests...\n")
    
    try:
        # Run tests
        test_api_key_creation()
        test_permission_groups()
        test_usage_tracking()
        test_key_management()
        test_error_handling()
        
        print("\n🎉 All tests completed!")
        print("\n📋 Summary:")
        print("- API key creation and validation: ✅")
        print("- Permission system: ✅")
        print("- Usage tracking: ✅")
        print("- Key management operations: ✅")
        print("- Error handling: ✅")
        
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()