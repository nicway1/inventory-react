#!/usr/bin/env python3
"""
Test the dual authentication system for enhanced inventory API
"""

import sys
import os

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from database import SessionLocal
from models.user import User

def test_dual_authentication():
    print('🔐 Testing Dual Authentication for Enhanced Inventory API')
    print('=' * 60)

    app = create_app()

    with app.app_context():
        # Get admin user for testing
        db_session = SessionLocal()
        admin_user = db_session.query(User).filter(User.username == 'admin').first()
        
        if not admin_user:
            print('✗ No admin user found for testing')
            db_session.close()
            return False
            
        print(f'✓ Test user: {admin_user.username} ({admin_user.user_type.value})')
        print(f'✓ Has view assets permission: {admin_user.permissions.can_view_assets if admin_user.permissions else "No permissions"}')
        
        db_session.close()
        
        # Generate JWT tokens for testing
        from routes.json_api import generate_access_token
        from routes.mobile_api import create_mobile_token
        
        json_jwt_token = generate_access_token(admin_user.id)
        mobile_jwt_token = create_mobile_token(admin_user)
        
        print(f'✓ JSON API JWT token generated (length: {len(json_jwt_token)})')
        print(f'✓ Mobile API JWT token generated (length: {len(mobile_jwt_token)})')

    # Test with Flask test client
    with app.test_client() as client:
        print('\n1. Testing with JSON API key + JWT token...')
        
        headers = {
            'X-API-Key': 'xAQhm3__ZH6MvRIPMIBSDRAsIa1w2Slh5uaCtc4NurM',
            'Authorization': f'Bearer {json_jwt_token}'
        }
        
        response = client.get('/api/v1/inventory?limit=1', headers=headers)
        print(f'   Status: {response.status_code}')
        
        if response.status_code == 200:
            data = response.get_json()
            assets = data.get('data', [])
            print(f'   ✓ SUCCESS: Retrieved {len(assets)} assets')
            
            if assets:
                asset = assets[0]
                print(f'   Sample asset: {asset.get("name")}')
                print(f'   Hardware specs: CPU={asset.get("cpu_type")}, Memory={asset.get("memory")}')
                print(f'   Total fields returned: {len(asset)}')
                
        else:
            print(f'   ✗ FAILED: {response.status_code}')
            if response.data:
                error_data = response.get_json()
                print(f'   Error: {error_data.get("error") if error_data else "Unknown"}')
        
        print('\n2. Testing with Mobile JWT token only...')
        
        headers = {
            'Authorization': f'Bearer {mobile_jwt_token}'
        }
        
        response = client.get('/api/v1/inventory?limit=1', headers=headers)
        print(f'   Status: {response.status_code}')
        
        if response.status_code == 200:
            data = response.get_json()
            assets = data.get('data', [])
            print(f'   ✓ SUCCESS: Retrieved {len(assets)} assets')
        else:
            print(f'   ✗ FAILED: {response.status_code}')
            if response.data:
                error_data = response.get_json()
                print(f'   Error: {error_data.get("error") if error_data else "Unknown"}')
        
        print('\n3. Testing accessory endpoint...')
        
        headers = {
            'X-API-Key': 'xAQhm3__ZH6MvRIPMIBSDRAsIa1w2Slh5uaCtc4NurM',
            'Authorization': f'Bearer {json_jwt_token}'
        }
        
        response = client.get('/api/v1/accessories?limit=1', headers=headers)
        print(f'   Status: {response.status_code}')
        
        if response.status_code == 200:
            data = response.get_json()
            accessories = data.get('data', [])
            print(f'   ✓ SUCCESS: Retrieved {len(accessories)} accessories')
            
            if accessories:
                accessory = accessories[0]
                print(f'   Sample accessory: {accessory.get("name")}')
                print(f'   Inventory: Total={accessory.get("total_quantity")}, Available={accessory.get("available_quantity")}')
                
        else:
            print(f'   ✗ FAILED: {response.status_code}')
            if response.data:
                error_data = response.get_json()
                print(f'   Error: {error_data.get("error") if error_data else "Unknown"}')
        
        print('\n4. Testing without authentication (should fail)...')
        
        response = client.get('/api/v1/inventory?limit=1')
        print(f'   Status: {response.status_code}')
        
        if response.status_code == 401:
            print(f'   ✓ SUCCESS: Properly rejected unauthorized request')
        else:
            print(f'   ✗ UNEXPECTED: Should have returned 401')
    
    print('\n' + '=' * 60)
    print('🎯 Dual Authentication Test Complete')
    
    print('\n📋 USAGE INSTRUCTIONS:')
    print('For your production API key, use either:')
    print('')
    print('Option 1 - JSON API Key + JWT:')
    print('  Headers:')
    print('    X-API-Key: xAQhm3__ZH6MvRIPMIBSDRAsIa1w2Slh5uaCtc4NurM')
    print('    Authorization: Bearer <jwt_token>')
    print('  (Get JWT token from /mobile/auth/login endpoint)')
    print('')
    print('Option 2 - Mobile JWT Only:')  
    print('  Headers:')
    print('    Authorization: Bearer <mobile_jwt_token>')
    print('  (Get mobile token from /api/mobile/v1/auth/login endpoint)')
    print('')
    print('Both methods provide access to:')
    print('  • GET /api/v1/inventory - Complete asset information')
    print('  • GET /api/v1/inventory/{id} - Single asset details')
    print('  • GET /api/v1/accessories - Complete accessory tracking')
    print('  • GET /api/v1/accessories/{id} - Single accessory details')

if __name__ == '__main__':
    test_dual_authentication()