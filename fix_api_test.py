#!/usr/bin/env python3
"""
Quick API Fix Test Script

Tests the API endpoints after applying fixes
"""

import requests
import json

BASE_URL = "https://inventory.truelog.com.sg"

def test_api_health():
    """Test API health endpoint"""
    print("🔍 Testing API Health...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ API Health: {data.get('status', 'unknown')}")
            return True
        else:
            print(f"✗ API Health failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ API Health error: {e}")
        return False

def test_api_login():
    """Test API login endpoint"""
    print("\n🔑 Testing API Login...")
    
    login_data = {
        'username': 'test',
        'password': '123456'
    }
    
    try:
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json=login_data,
            headers=headers,
            timeout=10
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get('success') and data.get('data', {}).get('token'):
                    token = data['data']['token']
                    print(f"✓ API Login successful - Token: {token[:20]}...")
                    return token
                else:
                    print(f"✗ API Login failed - Response: {data}")
                    return None
            except json.JSONDecodeError:
                print("✗ API Login failed - Invalid JSON response")
                print(f"Response text: {response.text[:200]}...")
                return None
        else:
            print(f"✗ API Login failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {error_data}")
            except:
                print(f"Response text: {response.text[:200]}...")
            return None
            
    except Exception as e:
        print(f"✗ API Login error: {e}")
        return None

def test_api_with_key():
    """Test API with API key"""
    print("\n🔐 Testing API with Key...")
    
    api_key = "xAQhm3__ZH6MvRIPMIBSDRAsIa1w2Slh5uaCtc4NurM"
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/tickets?per_page=1", headers=headers, timeout=10)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ API Key access successful")
            if data.get('data'):
                print(f"  Retrieved {len(data['data'])} tickets")
            return True
        else:
            print(f"✗ API Key access failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {error_data}")
            except:
                print(f"Response text: {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"✗ API Key test error: {e}")
        return False

def main():
    print("🔧 API Fix Test")
    print("=" * 40)
    
    # Test API health
    health_ok = test_api_health()
    
    # Test API login
    token = test_api_login()
    
    # Test API with key
    key_ok = test_api_with_key()
    
    # Summary
    print("\n📊 Test Results")
    print("=" * 40)
    print(f"API Health: {'✓ PASS' if health_ok else '✗ FAIL'}")
    print(f"API Login:  {'✓ PASS' if token else '✗ FAIL'}")
    print(f"API Key:    {'✓ PASS' if key_ok else '✗ FAIL'}")
    
    if health_ok and (token or key_ok):
        print("\n🎉 API fixes are working!")
    else:
        print("\n❌ API still has issues")

if __name__ == "__main__":
    main()