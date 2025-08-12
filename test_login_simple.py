#!/usr/bin/env python3
"""
Simple Login Test Script

Tests the production login system with proper CSRF handling
"""

import requests
import json
from bs4 import BeautifulSoup
import re

BASE_URL = "https://inventory.truelog.com.sg"

def get_csrf_token():
    """Get CSRF token from login page"""
    try:
        response = requests.get(f"{BASE_URL}/auth/login")
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_input = soup.find('input', {'name': 'csrf_token'}) or soup.find('meta', {'name': 'csrf-token'})
            if csrf_input:
                token = csrf_input.get('value') or csrf_input.get('content')
                print(f"✓ CSRF token extracted: {token[:20]}...")
                return token, response.cookies
        print("✗ Could not extract CSRF token")
        return None, None
    except Exception as e:
        print(f"✗ Error getting CSRF token: {e}")
        return None, None

def test_web_login(username, password):
    """Test web-based login"""
    print("\n🌐 Testing Web Login...")
    
    # Get CSRF token
    csrf_token, cookies = get_csrf_token()
    if not csrf_token:
        return False
    
    # Prepare login data
    login_data = {
        'username': username,
        'password': password,
        'csrf_token': csrf_token
    }
    
    # Attempt login
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            data=login_data,
            cookies=cookies,
            allow_redirects=False
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 302:
            location = response.headers.get('Location', '')
            if 'login' in location:
                print("✗ Login failed - redirected back to login")
                return False
            else:
                print(f"✓ Login successful - redirected to: {location}")
                return True
        elif response.status_code == 200:
            if 'invalid' in response.text.lower() or 'error' in response.text.lower():
                print("✗ Login failed - error message in response")
                return False
            else:
                print("✓ Login successful - 200 response")
                return True
        else:
            print(f"✗ Unexpected response: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Login error: {e}")
        return False

def test_api_health():
    """Test API health endpoint"""
    print("\n🔍 Testing API Health...")
    
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

def test_api_login_no_csrf(username, password):
    """Test API login without CSRF (should work for API endpoints)"""
    print("\n🔑 Testing API Login (No CSRF)...")
    
    login_data = {
        'username': username,
        'password': password
    }
    
    try:
        # Try with explicit headers to bypass CSRF
        headers = {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',  # Sometimes helps bypass CSRF
            'Accept': 'application/json'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json=login_data,
            headers=headers,
            timeout=10
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get('success') and data.get('data', {}).get('token'):
                    token = data['data']['token']
                    print(f"✓ API Login successful - Token: {token[:20]}...")
                    return token
                else:
                    print(f"✗ API Login failed - No token in response: {data}")
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

def test_api_with_token(token):
    """Test API endpoints with JWT token"""
    print("\n🛡️  Testing API with Token...")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Test token verification
    try:
        response = requests.get(f"{BASE_URL}/api/v1/auth/verify", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Token verification successful: {data.get('data', {}).get('username', 'Unknown')}")
        else:
            print(f"✗ Token verification failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Token verification error: {e}")
    
    # Test protected endpoint
    try:
        response = requests.get(f"{BASE_URL}/api/v1/tickets?per_page=1", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Protected endpoint access successful")
        else:
            print(f"✗ Protected endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Protected endpoint error: {e}")

def main():
    print("🔐 Simple Login Test")
    print("=" * 50)
    
    # Get credentials
    username = input("Username: ").strip()
    password = input("Password: ").strip()
    
    if not username or not password:
        print("❌ Username and password required")
        return
    
    print(f"\n🎯 Testing with: {username}")
    print(f"🌐 Target: {BASE_URL}")
    
    # Test API health first
    if not test_api_health():
        print("❌ API health check failed - aborting tests")
        return
    
    # Test web login
    web_success = test_web_login(username, password)
    
    # Test API login
    token = test_api_login_no_csrf(username, password)
    
    if token:
        test_api_with_token(token)
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 50)
    print(f"Web Login: {'✓ PASS' if web_success else '✗ FAIL'}")
    print(f"API Login: {'✓ PASS' if token else '✗ FAIL'}")
    print(f"API Token: {'✓ PASS' if token else '✗ FAIL'}")
    
    if web_success or token:
        print("\n🎉 Login system is working!")
    else:
        print("\n❌ Login system has issues")

if __name__ == "__main__":
    main()