#!/usr/bin/env python3
"""
Login System Test Script

This script tests both web-based login and API-based authentication
for the production system at https://inventory.truelog.com.sg/

Tests include:
- Web login form authentication
- API JWT token authentication
- Token verification and refresh
- User permissions and profile retrieval
- Session management

Usage:
    python test_login_system.py

Requirements:
    pip install requests colorama beautifulsoup4
"""

import requests
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import time

try:
    from colorama import init, Fore, Style
    init()
    
    def print_success(message: str):
        print(f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}")
    
    def print_error(message: str):
        print(f"{Fore.RED}✗ {message}{Style.RESET_ALL}")
    
    def print_warning(message: str):
        print(f"{Fore.YELLOW}⚠ {message}{Style.RESET_ALL}")
    
    def print_info(message: str):
        print(f"{Fore.CYAN}ℹ {message}{Style.RESET_ALL}")
        
except ImportError:
    print("Warning: colorama not installed. Install with: pip install colorama")
    
    def print_success(message: str):
        print(f"✓ {message}")
    
    def print_error(message: str):
        print(f"✗ {message}")
    
    def print_warning(message: str):
        print(f"⚠ {message}")
    
    def print_info(message: str):
        print(f"ℹ {message}")

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    print_warning("BeautifulSoup4 not installed. Web form testing will be limited.")
    HAS_BS4 = False

class LoginSystemTester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'LoginSystemTester/1.0'
        })
        
        # Test results tracking
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.test_results = []
        
        # Store tokens and session data
        self.jwt_token = None
        self.csrf_token = None
        self.session_cookies = None
    
    def log_test_result(self, test_name: str, success: bool, message: str, details: Optional[Dict] = None):
        """Log test result for summary"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print_success(f"{test_name}: {message}")
        else:
            self.tests_failed += 1
            print_error(f"{test_name}: {message}")
            
        self.test_results.append({
            'test': test_name,
            'success': success,
            'message': message,
            'details': details or {}
        })
    
    def make_request(self, method: str, endpoint: str, **kwargs) -> Tuple[bool, Optional[Dict], Optional[str], Optional[requests.Response]]:
        """Make HTTP request and return (success, response_data, error_message, response_object)"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(method, url, timeout=30, **kwargs)
            
            # Try to parse JSON response
            try:
                data = response.json()
            except json.JSONDecodeError:
                data = {'raw_response': response.text[:500]}  # Limit response size
            
            if response.status_code < 400:
                return True, data, None, response
            else:
                error_msg = f"HTTP {response.status_code}"
                if isinstance(data, dict) and 'error' in data:
                    error_msg += f": {data['error'].get('message', 'Unknown error')}"
                elif isinstance(data, dict) and 'raw_response' in data:
                    # For HTML responses, try to extract meaningful error
                    if 'error' in data['raw_response'].lower() or 'invalid' in data['raw_response'].lower():
                        error_msg += ": Authentication failed"
                return False, data, error_msg, response
                
        except requests.exceptions.Timeout:
            return False, None, "Request timeout (30s)", None
        except requests.exceptions.ConnectionError:
            return False, None, "Connection error - check if server is running", None
        except requests.exceptions.RequestException as e:
            return False, None, f"Request error: {str(e)}", None
    
    def test_web_login_page_access(self):
        """Test accessing the web login page"""
        print_info("Testing web login page access...")
        
        success, data, error, response = self.make_request('GET', '/login')
        
        if success and response:
            if response.status_code == 200:
                # Check if it's actually a login page
                content = response.text.lower()
                if 'login' in content and ('username' in content or 'email' in content) and 'password' in content:
                    self.log_test_result(
                        "Web Login Page Access",
                        True,
                        "Login page accessible and contains login form"
                    )
                    
                    # Extract CSRF token if available
                    if HAS_BS4:
                        try:
                            soup = BeautifulSoup(response.text, 'html.parser')
                            csrf_input = soup.find('input', {'name': 'csrf_token'}) or soup.find('input', {'name': '_token'})
                            if csrf_input:
                                self.csrf_token = csrf_input.get('value')
                                print_info(f"Extracted CSRF token: {self.csrf_token[:20]}...")
                        except Exception as e:
                            print_warning(f"Could not extract CSRF token: {e}")
                    
                    return True
                else:
                    self.log_test_result(
                        "Web Login Page Access",
                        False,
                        "Page accessible but doesn't appear to be a login form"
                    )
            else:
                self.log_test_result(
                    "Web Login Page Access",
                    False,
                    f"Unexpected redirect or response code: {response.status_code}"
                )
        else:
            self.log_test_result(
                "Web Login Page Access",
                False,
                f"Failed to access login page: {error}"
            )
        
        return False
    
    def test_web_login_invalid_credentials(self):
        """Test web login with invalid credentials"""
        print_info("Testing web login with invalid credentials...")
        
        login_data = {
            'username': 'invalid_user_12345',
            'password': 'invalid_password_12345'
        }
        
        if self.csrf_token:
            login_data['csrf_token'] = self.csrf_token
        
        success, data, error, response = self.make_request(
            'POST', 
            '/login',
            data=login_data,
            allow_redirects=False
        )
        
        # For web login, we expect either a redirect back to login or an error message
        if response:
            if response.status_code in [200, 302]:
                # Check if we're still on login page or redirected to login
                if response.status_code == 302:
                    location = response.headers.get('Location', '')
                    if 'login' in location or location == '/login':
                        self.log_test_result(
                            "Web Login Invalid Credentials",
                            True,
                            "Invalid credentials correctly rejected (redirected to login)"
                        )
                        return True
                
                # If 200, check for error message in content
                content = response.text.lower()
                if 'invalid' in content or 'error' in content or 'incorrect' in content:
                    self.log_test_result(
                        "Web Login Invalid Credentials",
                        True,
                        "Invalid credentials correctly rejected (error message shown)"
                    )
                    return True
                else:
                    self.log_test_result(
                        "Web Login Invalid Credentials",
                        False,
                        "Invalid credentials were unexpectedly accepted"
                    )
            else:
                self.log_test_result(
                    "Web Login Invalid Credentials",
                    False,
                    f"Unexpected response code: {response.status_code}"
                )
        else:
            self.log_test_result(
                "Web Login Invalid Credentials",
                False,
                f"Failed to test invalid credentials: {error}"
            )
        
        return False
    
    def test_api_login_invalid_credentials(self):
        """Test API login with invalid credentials"""
        print_info("Testing API login with invalid credentials...")
        
        login_data = {
            'username': 'invalid_user_12345',
            'password': 'invalid_password_12345'
        }
        
        success, data, error, response = self.make_request(
            'POST',
            '/api/v1/auth/login',
            json=login_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if not success and response and response.status_code == 401:
            self.log_test_result(
                "API Login Invalid Credentials",
                True,
                "Invalid credentials correctly rejected (401 Unauthorized)"
            )
            return True
        elif success:
            self.log_test_result(
                "API Login Invalid Credentials",
                False,
                "Invalid credentials were unexpectedly accepted"
            )
        else:
            self.log_test_result(
                "API Login Invalid Credentials",
                False,
                f"Unexpected response: {error}"
            )
        
        return False
    
    def test_api_login_valid_credentials(self, username: str, password: str):
        """Test API login with valid credentials"""
        print_info(f"Testing API login with credentials: {username}")
        
        login_data = {
            'username': username,
            'password': password
        }
        
        success, data, error, response = self.make_request(
            'POST',
            '/api/v1/auth/login',
            json=login_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if success and data and data.get('success'):
            user_data = data.get('data', {})
            token = user_data.get('token')
            
            if token:
                self.jwt_token = token
                self.log_test_result(
                    "API Login Valid Credentials",
                    True,
                    f"Login successful for user: {user_data.get('username', 'Unknown')}"
                )
                
                # Store token for future requests
                self.session.headers.update({
                    'Authorization': f'Bearer {token}'
                })
                
                return True, user_data
            else:
                self.log_test_result(
                    "API Login Valid Credentials",
                    False,
                    "Login response missing JWT token"
                )
        else:
            self.log_test_result(
                "API Login Valid Credentials",
                False,
                f"Login failed: {error}"
            )
        
        return False, None
    
    def test_jwt_token_verification(self):
        """Test JWT token verification"""
        print_info("Testing JWT token verification...")
        
        if not self.jwt_token:
            self.log_test_result(
                "JWT Token Verification",
                False,
                "No JWT token available for testing"
            )
            return False
        
        success, data, error, response = self.make_request(
            'GET',
            '/api/v1/auth/verify'
        )
        
        if success and data and data.get('success'):
            token_data = data.get('data', {})
            self.log_test_result(
                "JWT Token Verification",
                True,
                f"Token verified for user: {token_data.get('username', 'Unknown')}"
            )
            return True
        else:
            self.log_test_result(
                "JWT Token Verification",
                False,
                f"Token verification failed: {error}"
            )
            return False
    
    def test_user_permissions(self):
        """Test retrieving user permissions"""
        print_info("Testing user permissions retrieval...")
        
        if not self.jwt_token:
            self.log_test_result(
                "User Permissions",
                False,
                "No JWT token available for testing"
            )
            return False
        
        success, data, error, response = self.make_request(
            'GET',
            '/api/v1/auth/permissions'
        )
        
        if success and data and data.get('success'):
            perm_data = data.get('data', {})
            permissions = perm_data.get('permissions', [])
            capabilities = perm_data.get('capabilities', {})
            
            self.log_test_result(
                "User Permissions",
                True,
                f"Retrieved {len(permissions)} permissions and {len(capabilities)} capabilities"
            )
            
            # Log some key permissions
            if permissions:
                print_info(f"  Sample permissions: {', '.join(permissions[:5])}")
            if capabilities:
                key_caps = [k for k, v in capabilities.items() if v][:3]
                if key_caps:
                    print_info(f"  Key capabilities: {', '.join(key_caps)}")
            
            return True
        else:
            self.log_test_result(
                "User Permissions",
                False,
                f"Failed to retrieve permissions: {error}"
            )
            return False
    
    def test_user_profile(self):
        """Test retrieving user profile"""
        print_info("Testing user profile retrieval...")
        
        if not self.jwt_token:
            self.log_test_result(
                "User Profile",
                False,
                "No JWT token available for testing"
            )
            return False
        
        success, data, error, response = self.make_request(
            'GET',
            '/api/v1/auth/profile'
        )
        
        if success and data and data.get('success'):
            profile_data = data.get('data', {})
            self.log_test_result(
                "User Profile",
                True,
                f"Retrieved profile for: {profile_data.get('username', 'Unknown')} ({profile_data.get('user_type', 'Unknown type')})"
            )
            
            # Log some profile details
            if profile_data.get('company_name'):
                print_info(f"  Company: {profile_data['company_name']}")
            if profile_data.get('last_login'):
                print_info(f"  Last login: {profile_data['last_login'][:19]}")
            
            return True
        else:
            self.log_test_result(
                "User Profile",
                False,
                f"Failed to retrieve profile: {error}"
            )
            return False
    
    def test_token_refresh(self):
        """Test JWT token refresh"""
        print_info("Testing JWT token refresh...")
        
        if not self.jwt_token:
            self.log_test_result(
                "Token Refresh",
                False,
                "No JWT token available for testing"
            )
            return False
        
        success, data, error, response = self.make_request(
            'POST',
            '/api/v1/auth/refresh'
        )
        
        if success and data and data.get('success'):
            token_data = data.get('data', {})
            new_token = token_data.get('token')
            
            if new_token and new_token != self.jwt_token:
                self.jwt_token = new_token
                self.session.headers.update({
                    'Authorization': f'Bearer {new_token}'
                })
                
                self.log_test_result(
                    "Token Refresh",
                    True,
                    f"Token refreshed successfully for user: {token_data.get('username', 'Unknown')}"
                )
                return True
            else:
                self.log_test_result(
                    "Token Refresh",
                    False,
                    "Token refresh returned same or invalid token"
                )
        else:
            self.log_test_result(
                "Token Refresh",
                False,
                f"Token refresh failed: {error}"
            )
        
        return False
    
    def test_protected_api_access(self):
        """Test accessing protected API endpoints with JWT token"""
        print_info("Testing protected API access...")
        
        if not self.jwt_token:
            self.log_test_result(
                "Protected API Access",
                False,
                "No JWT token available for testing"
            )
            return False
        
        # Test accessing a protected endpoint
        success, data, error, response = self.make_request(
            'GET',
            '/api/v1/tickets?per_page=1'
        )
        
        if success and data:
            self.log_test_result(
                "Protected API Access",
                True,
                "Successfully accessed protected API endpoint with JWT token"
            )
            return True
        else:
            self.log_test_result(
                "Protected API Access",
                False,
                f"Failed to access protected endpoint: {error}"
            )
            return False
    
    def test_api_without_token(self):
        """Test accessing protected API without token"""
        print_info("Testing protected API access without token...")
        
        # Temporarily remove authorization header
        auth_header = self.session.headers.pop('Authorization', None)
        
        success, data, error, response = self.make_request(
            'GET',
            '/api/v1/tickets'
        )
        
        # Restore authorization header
        if auth_header:
            self.session.headers['Authorization'] = auth_header
        
        if not success and response and response.status_code == 401:
            self.log_test_result(
                "API Access Without Token",
                True,
                "Protected endpoint correctly rejected request without token (401)"
            )
            return True
        elif success:
            self.log_test_result(
                "API Access Without Token",
                False,
                "Protected endpoint unexpectedly allowed access without token"
            )
        else:
            self.log_test_result(
                "API Access Without Token",
                False,
                f"Unexpected response: {error}"
            )
        
        return False
    
    def run_all_tests(self, test_username: str = None, test_password: str = None):
        """Run all login system tests"""
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"🔐 Login System Test Suite")
        print(f"{'='*60}{Style.RESET_ALL}")
        print(f"Base URL: {self.base_url}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Run tests in logical order
        tests = [
            self.test_web_login_page_access,
            self.test_web_login_invalid_credentials,
            self.test_api_login_invalid_credentials,
        ]
        
        # Add valid credential tests if provided
        if test_username and test_password:
            print_info(f"Testing with provided credentials: {test_username}")
            tests.extend([
                lambda: self.test_api_login_valid_credentials(test_username, test_password)[0],
                self.test_jwt_token_verification,
                self.test_user_permissions,
                self.test_user_profile,
                self.test_token_refresh,
                self.test_protected_api_access,
                self.test_api_without_token
            ])
        else:
            print_warning("No test credentials provided - skipping valid login tests")
            print_info("To test with valid credentials, provide username and password")
        
        for test in tests:
            try:
                test()
            except Exception as e:
                test_name = test.__name__.replace('test_', '').replace('_', ' ').title()
                self.log_test_result(
                    test_name,
                    False,
                    f"Test crashed: {str(e)}"
                )
            print()  # Add spacing between tests
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"📊 Login System Test Summary")
        print(f"{'='*60}{Style.RESET_ALL}")
        
        print(f"Total Tests: {self.tests_run}")
        print_success(f"Passed: {self.tests_passed}")
        if self.tests_failed > 0:
            print_error(f"Failed: {self.tests_failed}")
        else:
            print(f"Failed: {self.tests_failed}")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"Success Rate: {success_rate:.1f}%")
        
        if self.tests_failed > 0:
            print(f"\n{Fore.RED}Failed Tests:{Style.RESET_ALL}")
            for result in self.test_results:
                if not result['success']:
                    print_error(f"  - {result['test']}: {result['message']}")
        
        print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if success_rate >= 80:
            print_success(f"\n🎉 Login system is working well! ({success_rate:.1f}% success rate)")
        elif success_rate >= 60:
            print_warning(f"\n⚠️  Login system has some issues ({success_rate:.1f}% success rate)")
        else:
            print_error(f"\n❌ Login system has significant problems ({success_rate:.1f}% success rate)")

def main():
    """Main function to run the login tests"""
    
    # Configuration
    BASE_URL = "https://inventory.truelog.com.sg"
    
    print(f"{Fore.YELLOW}🔐 Login System Test Suite{Style.RESET_ALL}")
    print(f"Testing: {BASE_URL}")
    print()
    
    # Get test credentials
    print("To test login functionality, please provide test credentials:")
    print("(Leave blank to skip valid credential tests)")
    
    username = input("Username: ").strip()
    password = input("Password: ").strip() if username else ""
    
    if username and password:
        print(f"\n{Fore.GREEN}✓ Will test with provided credentials{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.YELLOW}⚠ Will skip valid credential tests{Style.RESET_ALL}")
    
    print(f"\n{Fore.YELLOW}⚠️  WARNING: This script will test the PRODUCTION login system{Style.RESET_ALL}")
    print(f"   - It will attempt login with provided credentials")
    print(f"   - It will test various authentication endpoints")
    print(f"   - Ensure you have permission to run these tests")
    print()
    
    response = input("Do you want to continue? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("Test cancelled.")
        return
    
    # Create tester and run tests
    tester = LoginSystemTester(BASE_URL)
    tester.run_all_tests(username if username else None, password if password else None)
    
    # Exit with appropriate code
    sys.exit(0 if tester.tests_failed == 0 else 1)

if __name__ == "__main__":
    main()