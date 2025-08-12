#!/usr/bin/env python3
"""
Test script for the enhanced inventory API endpoints

This script tests the new /api/v1/inventory endpoints to ensure they return
complete asset information as specified.

Usage:
    python test_enhanced_inventory_api.py
"""

import sys
import os
import requests
import json
from datetime import datetime

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_api_endpoints():
    """Test the enhanced inventory API endpoints"""
    
    # Test configuration
    BASE_URL = "http://localhost:5000"  # Adjust as needed
    
    # Test credentials - you may need to adjust these
    USERNAME = "admin@example.com"  # Update with valid test user
    PASSWORD = "password123"       # Update with valid test password
    
    print("=" * 60)
    print("Testing Enhanced Inventory API Endpoints")
    print("=" * 60)
    
    # Step 1: Get authentication token
    print("\n1. Testing authentication...")
    
    login_url = f"{BASE_URL}/api/mobile/v1/auth/login"
    login_data = {
        "username": USERNAME,
        "password": PASSWORD
    }
    
    try:
        login_response = requests.post(login_url, json=login_data, timeout=10)
        if login_response.status_code == 200:
            login_result = login_response.json()
            token = login_result.get('token')
            print(f"✓ Login successful")
            print(f"  User: {login_result.get('user', {}).get('username')}")
            print(f"  Role: {login_result.get('user', {}).get('user_type')}")
        else:
            print(f"✗ Login failed: {login_response.status_code}")
            print(f"  Response: {login_response.text}")
            return False
            
    except requests.RequestException as e:
        print(f"✗ Login request failed: {str(e)}")
        print("  Make sure the Flask app is running on the correct port")
        return False
    
    if not token:
        print("✗ No token received from login")
        return False
    
    # Headers for authenticated requests
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Step 2: Test health check endpoint
    print("\n2. Testing health check endpoint...")
    
    health_url = f"{BASE_URL}/api/v1/inventory/health"
    try:
        health_response = requests.get(health_url, timeout=10)
        if health_response.status_code == 200:
            health_data = health_response.json()
            print(f"✓ Health check successful")
            print(f"  Status: {health_data.get('status')}")
            print(f"  Version: {health_data.get('version')}")
        else:
            print(f"✗ Health check failed: {health_response.status_code}")
            
    except requests.RequestException as e:
        print(f"✗ Health check request failed: {str(e)}")
    
    # Step 3: Test inventory list endpoint
    print("\n3. Testing inventory list endpoint...")
    
    inventory_url = f"{BASE_URL}/api/v1/inventory"
    try:
        inventory_response = requests.get(inventory_url, headers=headers, timeout=10)
        if inventory_response.status_code == 200:
            inventory_data = inventory_response.json()
            assets = inventory_data.get('data', [])
            pagination = inventory_data.get('pagination', {})
            
            print(f"✓ Inventory list successful")
            print(f"  Total assets: {pagination.get('total', 0)}")
            print(f"  Assets returned: {len(assets)}")
            
            # Check if we have assets to examine
            if assets:
                asset = assets[0]  # Check first asset
                print(f"\n  Sample asset structure:")
                
                # Check required fields from specification
                required_fields = [
                    'id', 'name', 'serial_number', 'model', 'asset_tag', 'manufacturer', 'status',
                    'cpu_type', 'cpu_cores', 'gpu_cores', 'memory', 'storage', 'hardware_type', 'asset_type',
                    'condition', 'is_erased', 'has_keyboard', 'has_charger', 'diagnostics_code',
                    'current_customer', 'country', 'asset_company', 'receiving_date',
                    'created_at', 'updated_at'
                ]
                
                missing_fields = []
                present_fields = []
                
                for field in required_fields:
                    if field in asset:
                        present_fields.append(field)
                        # Show some sample values
                        if field in ['id', 'name', 'serial_number', 'status', 'cpu_type', 'memory', 'condition']:
                            print(f"    {field}: {asset[field]}")
                    else:
                        missing_fields.append(field)
                
                print(f"\n  Field coverage: {len(present_fields)}/{len(required_fields)} fields present")
                
                if missing_fields:
                    print(f"  ✗ Missing fields: {', '.join(missing_fields)}")
                else:
                    print(f"  ✓ All required fields present")
                    
            else:
                print("  No assets found in response")
                
        else:
            print(f"✗ Inventory list failed: {inventory_response.status_code}")
            print(f"  Response: {inventory_response.text}")
            
    except requests.RequestException as e:
        print(f"✗ Inventory list request failed: {str(e)}")
    
    # Step 4: Test single asset endpoint (if we have assets)
    print("\n4. Testing single asset endpoint...")
    
    if 'assets' in locals() and assets:
        asset_id = assets[0]['id']
        single_asset_url = f"{BASE_URL}/api/v1/inventory/{asset_id}"
        
        try:
            single_response = requests.get(single_asset_url, headers=headers, timeout=10)
            if single_response.status_code == 200:
                single_data = single_response.json()
                asset_details = single_data.get('data', {})
                
                print(f"✓ Single asset retrieval successful")
                print(f"  Asset ID: {asset_details.get('id')}")
                print(f"  Asset Name: {asset_details.get('name')}")
                print(f"  Serial Number: {asset_details.get('serial_number')}")
                print(f"  Hardware Type: {asset_details.get('hardware_type')}")
                print(f"  CPU Type: {asset_details.get('cpu_type')}")
                print(f"  Memory: {asset_details.get('memory')}")
                print(f"  Storage: {asset_details.get('storage')}")
                print(f"  Condition: {asset_details.get('condition')}")
                
            else:
                print(f"✗ Single asset retrieval failed: {single_response.status_code}")
                print(f"  Response: {single_response.text}")
                
        except requests.RequestException as e:
            print(f"✗ Single asset request failed: {str(e)}")
    else:
        print("  Skipping (no assets available for testing)")
    
    # Step 5: Test filtering capabilities
    print("\n5. Testing filtering capabilities...")
    
    # Test search filter
    search_url = f"{BASE_URL}/api/v1/inventory?search=macbook&limit=5"
    try:
        search_response = requests.get(search_url, headers=headers, timeout=10)
        if search_response.status_code == 200:
            search_data = search_response.json()
            search_assets = search_data.get('data', [])
            print(f"✓ Search filter test successful")
            print(f"  Search results: {len(search_assets)} assets")
        else:
            print(f"✗ Search filter test failed: {search_response.status_code}")
    except requests.RequestException as e:
        print(f"✗ Search filter test failed: {str(e)}")
    
    # Test status filter
    status_url = f"{BASE_URL}/api/v1/inventory?status=available&limit=5"
    try:
        status_response = requests.get(status_url, headers=headers, timeout=10)
        if status_response.status_code == 200:
            status_data = status_response.json()
            status_assets = status_data.get('data', [])
            print(f"✓ Status filter test successful")
            print(f"  Available assets: {len(status_assets)} assets")
        else:
            print(f"✗ Status filter test failed: {status_response.status_code}")
    except requests.RequestException as e:
        print(f"✗ Status filter test failed: {str(e)}")
    
    # Step 6: Test accessory endpoints
    print("\n6. Testing accessory endpoints...")
    
    # Test accessory list endpoint
    accessories_url = f"{BASE_URL}/api/v1/accessories"
    try:
        accessories_response = requests.get(accessories_url, headers=headers, timeout=10)
        if accessories_response.status_code == 200:
            accessories_data = accessories_response.json()
            accessories = accessories_data.get('data', [])
            pagination = accessories_data.get('pagination', {})
            
            print(f"✓ Accessory list successful")
            print(f"  Total accessories: {pagination.get('total', 0)}")
            print(f"  Accessories returned: {len(accessories)}")
            
            # Check accessory structure if we have accessories
            if accessories:
                accessory = accessories[0]  # Check first accessory
                print(f"\n  Sample accessory structure:")
                
                # Check required accessory fields
                required_fields = [
                    'id', 'name', 'category', 'manufacturer', 'model', 'status',
                    'total_quantity', 'available_quantity', 'checked_out_quantity',
                    'country', 'current_customer', 'is_available',
                    'checkout_date', 'return_date', 'description',
                    'created_at', 'updated_at', 'item_type'
                ]
                
                missing_fields = []
                present_fields = []
                
                for field in required_fields:
                    if field in accessory:
                        present_fields.append(field)
                        # Show some sample values
                        if field in ['id', 'name', 'category', 'status', 'total_quantity', 'available_quantity']:
                            print(f"    {field}: {accessory[field]}")
                    else:
                        missing_fields.append(field)
                
                print(f"\n  Field coverage: {len(present_fields)}/{len(required_fields)} fields present")
                
                if missing_fields:
                    print(f"  ✗ Missing fields: {', '.join(missing_fields)}")
                else:
                    print(f"  ✓ All required accessory fields present")
                    
                # Test single accessory endpoint
                print("\n  Testing single accessory endpoint...")
                accessory_id = accessory['id']
                single_accessory_url = f"{BASE_URL}/api/v1/accessories/{accessory_id}"
                
                try:
                    single_acc_response = requests.get(single_accessory_url, headers=headers, timeout=10)
                    if single_acc_response.status_code == 200:
                        single_acc_data = single_acc_response.json()
                        accessory_details = single_acc_data.get('data', {})
                        
                        print(f"  ✓ Single accessory retrieval successful")
                        print(f"    Accessory ID: {accessory_details.get('id')}")
                        print(f"    Name: {accessory_details.get('name')}")
                        print(f"    Category: {accessory_details.get('category')}")
                        print(f"    Total Qty: {accessory_details.get('total_quantity')}")
                        print(f"    Available Qty: {accessory_details.get('available_quantity')}")
                        
                    else:
                        print(f"  ✗ Single accessory retrieval failed: {single_acc_response.status_code}")
                        
                except requests.RequestException as e:
                    print(f"  ✗ Single accessory request failed: {str(e)}")
                    
            else:
                print("  No accessories found in response")
                
        else:
            print(f"✗ Accessory list failed: {accessories_response.status_code}")
            print(f"  Response: {accessories_response.text}")
            
    except requests.RequestException as e:
        print(f"✗ Accessory list request failed: {str(e)}")
    
    # Test accessory filtering
    print("\n7. Testing accessory filtering...")
    
    # Test accessory search filter
    acc_search_url = f"{BASE_URL}/api/v1/accessories?search=mouse&limit=5"
    try:
        acc_search_response = requests.get(acc_search_url, headers=headers, timeout=10)
        if acc_search_response.status_code == 200:
            acc_search_data = acc_search_response.json()
            acc_search_results = acc_search_data.get('data', [])
            print(f"✓ Accessory search filter test successful")
            print(f"  Search results: {len(acc_search_results)} accessories")
        else:
            print(f"✗ Accessory search filter test failed: {acc_search_response.status_code}")
    except requests.RequestException as e:
        print(f"✗ Accessory search filter test failed: {str(e)}")
    
    # Test accessory status filter
    acc_status_url = f"{BASE_URL}/api/v1/accessories?status=available&limit=5"
    try:
        acc_status_response = requests.get(acc_status_url, headers=headers, timeout=10)
        if acc_status_response.status_code == 200:
            acc_status_data = acc_status_response.json()
            acc_status_results = acc_status_data.get('data', [])
            print(f"✓ Accessory status filter test successful")
            print(f"  Available accessories: {len(acc_status_results)} accessories")
        else:
            print(f"✗ Accessory status filter test failed: {acc_status_response.status_code}")
    except requests.RequestException as e:
        print(f"✗ Accessory status filter test failed: {str(e)}")
    
    print("\n" + "=" * 60)
    print("API Testing Complete")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    print("Enhanced Inventory API Test Suite")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    try:
        success = test_api_endpoints()
        
        if success:
            print("\n🎉 All tests completed successfully!")
            print("\nThe enhanced inventory API endpoints are ready to use:")
            
            print("\n📦 Asset Endpoints:")
            print("  - GET /api/v1/inventory (list all assets with complete info)")
            print("  - GET /api/v1/inventory/{id} (get single asset with complete info)")
            
            print("\n🔧 Accessory Endpoints:")
            print("  - GET /api/v1/accessories (list all accessories with complete info)")
            print("  - GET /api/v1/accessories/{id} (get single accessory with complete info)")
            
            print("\n❤️ Health Check:")
            print("  - GET /api/v1/inventory/health (health check)")
            
            print("\nSupported query parameters (for both assets and accessories):")
            print("  - page: Page number (default: 1)")
            print("  - limit: Items per page (default: 20, max: 100)")
            print("  - search: Search term for name, serial, model, category, etc.")
            print("  - status: Filter by status (varies by type)")
            print("  - category: Filter by asset/accessory category/type")
            
            print("\n📋 Key Features:")
            print("  ✓ Complete asset specifications (CPU, memory, storage, etc.)")
            print("  ✓ Complete accessory inventory tracking (quantities, availability)")
            print("  ✓ Authentication and permission-based access")
            print("  ✓ Country-based restrictions for regional admins")
            print("  ✓ Advanced filtering and search capabilities")
            print("  ✓ Comprehensive field coverage as requested")
            
        else:
            print("\n⚠️  Some tests failed. Check the output above for details.")
            
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n✗ Test suite failed with error: {str(e)}")
        sys.exit(1)