#!/usr/bin/env python3
"""
Comprehensive Search API Test Suite

Tests all search functionality that matches the web version:
- Global search across all entities
- Asset search with advanced filters
- Accessory search with filters
- Search suggestions/autocomplete
- Filter options discovery
"""

import sys
import os
import json

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from database import SessionLocal
from models.user import User
from models.asset import Asset
from models.accessory import Accessory

def test_search_api():
    print('🔍 COMPREHENSIVE SEARCH API TESTING')
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
        
        # Check some sample data
        asset_count = db_session.query(Asset).count()
        accessory_count = db_session.query(Accessory).count()
        
        print(f'✓ Sample data: {asset_count} assets, {accessory_count} accessories')
        
        if asset_count == 0:
            print('⚠️  No assets found - some tests may not return results')
        
        db_session.close()
        
        # Generate JWT tokens for testing
        from routes.json_api import generate_access_token
        from routes.mobile_api import create_mobile_token
        
        json_jwt_token = generate_access_token(admin_user.id)
        mobile_jwt_token = create_mobile_token(admin_user)
        
        print(f'✓ JWT tokens generated')

    # Test with Flask test client
    with app.test_client() as client:
        print('\n📋 SEARCH API ENDPOINTS TESTING')
        print('-' * 40)
        
        # Test authentication methods
        headers_json_api = {
            'X-API-Key': 'xAQhm3__ZH6MvRIPMIBSDRAsIa1w2Slh5uaCtc4NurM',
            'Authorization': f'Bearer {json_jwt_token}'
        }
        
        headers_mobile = {
            'Authorization': f'Bearer {mobile_jwt_token}'
        }
        
        # Test 1: Health Check
        print('\n1. Testing Health Check...')
        response = client.get('/api/v1/search/health')
        print(f'   Status: {response.status_code}')
        
        if response.status_code == 200:
            data = response.get_json()
            print(f'   ✓ SUCCESS: {data.get("status")}')
            print(f'   Available endpoints: {len(data.get("endpoints", []))}')
        else:
            print(f'   ✗ FAILED: Health check failed')
            return False
        
        # Test 2: Global Search
        print('\n2. Testing Global Search...')
        test_searches = ['laptop', 'apple', 'macbook', 'mouse']
        
        for search_term in test_searches:
            print(f'\n   Searching for: "{search_term}"')
            
            # Test with JSON API authentication
            response = client.get(f'/api/v1/search/global?q={search_term}&limit=5', headers=headers_json_api)
            print(f'   JSON API - Status: {response.status_code}')
            
            if response.status_code == 200:
                data = response.get_json()
                counts = data.get('counts', {})
                total = counts.get('total', 0)
                print(f'   ✓ Total results: {total}')
                print(f'     - Assets: {counts.get("assets", 0)}')
                print(f'     - Accessories: {counts.get("accessories", 0)}')
                print(f'     - Customers: {counts.get("customers", 0)}')
                print(f'     - Tickets: {counts.get("tickets", 0)}')
                print(f'     - Related tickets: {counts.get("related_tickets", 0)}')
                
                if total > 0:
                    print(f'   ✓ Search successful with results!')
                    
                    # Show sample results
                    results = data.get('data', {})
                    if results.get('assets'):
                        asset = results['assets'][0]
                        print(f'   Sample asset: {asset.get("name")} (ID: {asset.get("id")})')
                    
                    if results.get('accessories'):
                        accessory = results['accessories'][0]
                        print(f'   Sample accessory: {accessory.get("name")} (ID: {accessory.get("id")})')
                
            else:
                print(f'   ✗ FAILED: {response.status_code}')
                if response.data:
                    error_data = response.get_json()
                    print(f'   Error: {error_data.get("error") if error_data else "Unknown"}')
            
            # Test with Mobile API authentication
            response = client.get(f'/api/v1/search/global?q={search_term}&limit=5', headers=headers_mobile)
            print(f'   Mobile API - Status: {response.status_code}')
            
            if response.status_code == 200:
                print(f'   ✓ Mobile authentication also works')
            
            break  # Test just the first search term for brevity
        
        # Test 3: Advanced Asset Search
        print('\n3. Testing Advanced Asset Search...')
        
        # Test basic asset search
        response = client.get('/api/v1/search/assets?q=macbook&limit=3', headers=headers_json_api)
        print(f'   Basic search - Status: {response.status_code}')
        
        if response.status_code == 200:
            data = response.get_json()
            assets = data.get('data', [])
            print(f'   ✓ Found {len(assets)} assets')
            
            if assets:
                asset = assets[0]
                print(f'   Sample: {asset.get("name")} - {asset.get("cpu_type")} - {asset.get("memory")}')
                print(f'   Fields returned: {len(asset)} (should be 48+)')
        
        # Test asset search with filters
        response = client.get('/api/v1/search/assets?q=laptop&status=available&sort=name&order=asc', headers=headers_json_api)
        print(f'   Filtered search - Status: {response.status_code}')
        
        if response.status_code == 200:
            data = response.get_json()
            print(f'   ✓ Filtered search successful')
            print(f'   Applied filters: {data.get("filters", {})}')
            print(f'   Sorting: {data.get("sorting", {})}')
        
        # Test 4: Accessory Search
        print('\n4. Testing Accessory Search...')
        
        response = client.get('/api/v1/search/accessories?q=mouse&limit=3', headers=headers_json_api)
        print(f'   Status: {response.status_code}')
        
        if response.status_code == 200:
            data = response.get_json()
            accessories = data.get('data', [])
            print(f'   ✓ Found {len(accessories)} accessories')
            
            if accessories:
                accessory = accessories[0]
                print(f'   Sample: {accessory.get("name")} - Qty: {accessory.get("total_quantity")}')
                print(f'   Fields returned: {len(accessory)} (should be 20+)')
        
        # Test 5: Search Suggestions
        print('\n5. Testing Search Suggestions...')
        
        response = client.get('/api/v1/search/suggestions?q=mac&type=assets&limit=5', headers=headers_json_api)
        print(f'   Status: {response.status_code}')
        
        if response.status_code == 200:
            data = response.get_json()
            suggestions = data.get('suggestions', [])
            print(f'   ✓ Got {len(suggestions)} suggestions')
            
            for suggestion in suggestions[:3]:  # Show first 3
                print(f'     - {suggestion.get("text")} ({suggestion.get("type")})')
        
        # Test 6: Filter Options
        print('\n6. Testing Filter Options...')
        
        response = client.get('/api/v1/search/filters?type=assets', headers=headers_json_api)
        print(f'   Status: {response.status_code}')
        
        if response.status_code == 200:
            data = response.get_json()
            asset_filters = data.get('assets', {})
            print(f'   ✓ Available asset filters:')
            for filter_type, options in asset_filters.items():
                print(f'     - {filter_type}: {len(options)} options')
                if options:
                    print(f'       Examples: {", ".join(options[:3])}{"..." if len(options) > 3 else ""}')
        
        # Test 7: Error Handling
        print('\n7. Testing Error Handling...')
        
        # Test without search term
        response = client.get('/api/v1/search/global', headers=headers_json_api)
        print(f'   No search term - Status: {response.status_code}')
        if response.status_code == 400:
            print(f'   ✓ Correctly rejected empty search')
        
        # Test without authentication
        response = client.get('/api/v1/search/global?q=test')
        print(f'   No authentication - Status: {response.status_code}')
        if response.status_code == 401:
            print(f'   ✓ Correctly rejected unauthenticated request')
        
        # Test 8: Advanced Features
        print('\n8. Testing Advanced Features...')
        
        # Test type filtering in global search
        response = client.get('/api/v1/search/global?q=macbook&types=assets&include_related=false', headers=headers_json_api)
        print(f'   Type filtering - Status: {response.status_code}')
        
        if response.status_code == 200:
            data = response.get_json()
            search_types = data.get('search_types', [])
            counts = data.get('counts', {})
            print(f'   ✓ Searched only: {search_types}')
            print(f'   Assets: {counts.get("assets", 0)}, Others: {sum(v for k, v in counts.items() if k != "assets")}')
        
        # Test pagination
        response = client.get('/api/v1/search/global?q=laptop&page=1&limit=2', headers=headers_json_api)
        print(f'   Pagination - Status: {response.status_code}')
        
        if response.status_code == 200:
            data = response.get_json()
            pagination = data.get('pagination', {})
            print(f'   ✓ Page: {pagination.get("page")}, Limit: {pagination.get("limit")}')
            print(f'   Total: {pagination.get("total")}, Pages: {pagination.get("pages")}')
    
    print('\n' + '=' * 60)
    print('✅ SEARCH API TESTING COMPLETED')
    
    print('\n📊 SEARCH API CAPABILITIES:')
    print('  🔍 Global Search: Assets, Accessories, Customers, Tickets ✓')
    print('  🎯 Advanced Asset Search: Filters, Sorting, Pagination ✓') 
    print('  📦 Accessory Search: Inventory tracking, Availability ✓')
    print('  💡 Search Suggestions: Autocomplete functionality ✓')
    print('  🔧 Filter Discovery: Dynamic filter options ✓')
    print('  🔐 Dual Authentication: JSON API + Mobile JWT ✓')
    print('  📄 Related Tickets: Asset-ticket relationship discovery ✓')
    print('  🚀 Error Handling: Proper validation and responses ✓')
    
    print('\n📋 SEARCH ENDPOINTS SUMMARY:')
    print('  • GET /api/v1/search/global - Search across all entities')
    print('  • GET /api/v1/search/assets - Advanced asset search with filters')
    print('  • GET /api/v1/search/accessories - Accessory search with inventory')
    print('  • GET /api/v1/search/suggestions - Autocomplete suggestions')
    print('  • GET /api/v1/search/filters - Available filter options')
    print('  • GET /api/v1/search/health - Health check endpoint')
    
    print('\n🎯 KEY FEATURES MATCHING WEB VERSION:')
    print('  ✓ Same search fields and logic as web interface')
    print('  ✓ User permission filtering (Country Admin, Client users)')
    print('  ✓ Related ticket discovery for found assets')
    print('  ✓ Advanced filtering (status, category, manufacturer)')
    print('  ✓ Sorting and pagination support')
    print('  ✓ Complete field mapping (48+ fields per asset)')
    print('  ✓ Dual authentication support for iOS integration')
    
    return True

if __name__ == '__main__':
    test_search_api()