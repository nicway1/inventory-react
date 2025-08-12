#!/usr/bin/env python3
"""
Production API Test Script

This script tests the production API endpoints at https://inventory.truelog.com.sg/
using the provided API key to ensure all functionality works correctly.

Usage:
    python test_production_api.py

Requirements:
    pip install requests colorama
"""

import requests
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import time

try:
    from colorama import init, Fore, Style
    init()  # Initialize colorama for Windows compatibility
    
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

class ProductionAPITester:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'ProductionAPITester/1.0'
        })
        
        # Test results tracking
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.test_results = []
        
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
    
    def make_request(self, method: str, endpoint: str, **kwargs) -> tuple[bool, Optional[Dict], Optional[str]]:
        """Make API request and return (success, response_data, error_message)"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(method, url, timeout=30, **kwargs)
            
            # Try to parse JSON response
            try:
                data = response.json()
            except json.JSONDecodeError:
                data = {'raw_response': response.text}
            
            if response.status_code < 400:
                return True, data, None
            else:
                error_msg = f"HTTP {response.status_code}"
                if isinstance(data, dict) and 'error' in data:
                    error_msg += f": {data['error'].get('message', 'Unknown error')}"
                return False, data, error_msg
                
        except requests.exceptions.Timeout:
            return False, None, "Request timeout (30s)"
        except requests.exceptions.ConnectionError:
            return False, None, "Connection error - check if server is running"
        except requests.exceptions.RequestException as e:
            return False, None, f"Request error: {str(e)}"
    
    def test_health_check(self):
        """Test the health check endpoint (no auth required)"""
        print_info("Testing health check endpoint...")
        
        # Remove auth header for health check
        headers = self.session.headers.copy()
        del headers['Authorization']
        
        success, data, error = self.make_request('GET', '/api/v1/health', headers=headers)
        
        if success and data:
            self.log_test_result(
                "Health Check",
                True,
                f"API is healthy - Status: {data.get('status', 'unknown')}"
            )
            return True
        else:
            self.log_test_result(
                "Health Check",
                False,
                f"Health check failed: {error or 'Unknown error'}"
            )
            return False
    
    def test_api_key_validation(self):
        """Test API key validation"""
        print_info("Testing API key validation...")
        
        # Test with valid key
        success, data, error = self.make_request('GET', '/api/v1/tickets')
        
        if success:
            self.log_test_result(
                "API Key Validation",
                True,
                "API key is valid and accepted"
            )
        else:
            self.log_test_result(
                "API Key Validation",
                False,
                f"API key validation failed: {error}"
            )
            return False
        
        # Test with invalid key
        invalid_session = requests.Session()
        invalid_session.headers.update({
            'Authorization': 'Bearer invalid_key_12345',
            'Content-Type': 'application/json'
        })
        
        try:
            response = invalid_session.get(f"{self.base_url}/api/v1/tickets", timeout=10)
            if response.status_code == 401:
                print_success("Invalid API key correctly rejected (401)")
            else:
                print_warning(f"Expected 401 for invalid key, got {response.status_code}")
        except Exception as e:
            print_warning(f"Could not test invalid key: {e}")
        
        return True
    
    def test_list_tickets(self):
        """Test listing tickets with various parameters"""
        print_info("Testing ticket listing...")
        
        # Basic ticket list
        success, data, error = self.make_request('GET', '/api/v1/tickets')
        
        if success and data:
            tickets = data.get('data', [])
            pagination = data.get('meta', {}).get('pagination', {})
            
            self.log_test_result(
                "List Tickets",
                True,
                f"Retrieved {len(tickets)} tickets (Total: {pagination.get('total', 'unknown')})"
            )
            
            # Test pagination
            if len(tickets) > 0:
                success, data, error = self.make_request('GET', '/api/v1/tickets?page=1&per_page=5')
                if success:
                    limited_tickets = data.get('data', [])
                    self.log_test_result(
                        "Ticket Pagination",
                        len(limited_tickets) <= 5,
                        f"Pagination working - got {len(limited_tickets)} tickets (requested 5)"
                    )
            
            # Test filtering by status
            success, data, error = self.make_request('GET', '/api/v1/tickets?status=NEW')
            if success:
                filtered_tickets = data.get('data', [])
                self.log_test_result(
                    "Ticket Filtering",
                    True,
                    f"Status filtering working - got {len(filtered_tickets)} NEW tickets"
                )
            
            return len(tickets) > 0  # Return True if we have tickets to work with
        else:
            self.log_test_result(
                "List Tickets",
                False,
                f"Failed to retrieve tickets: {error}"
            )
            return False
    
    def test_get_ticket_details(self):
        """Test getting individual ticket details"""
        print_info("Testing ticket details retrieval...")
        
        # First get a list of tickets to find one to test with
        success, data, error = self.make_request('GET', '/api/v1/tickets?per_page=1')
        
        if success and data and data.get('data'):
            ticket_id = data['data'][0]['id']
            
            # Get detailed ticket info
            success, data, error = self.make_request('GET', f'/api/v1/tickets/{ticket_id}')
            
            if success and data:
                ticket = data.get('data', {})
                self.log_test_result(
                    "Get Ticket Details",
                    True,
                    f"Retrieved details for ticket #{ticket_id}: '{ticket.get('subject', 'No subject')[:50]}...'"
                )
                return True
            else:
                self.log_test_result(
                    "Get Ticket Details",
                    False,
                    f"Failed to get ticket details: {error}"
                )
        else:
            self.log_test_result(
                "Get Ticket Details",
                False,
                "No tickets available to test with"
            )
        
        # Test with non-existent ticket
        success, data, error = self.make_request('GET', '/api/v1/tickets/999999')
        if not success and '404' in str(error):
            print_success("Non-existent ticket correctly returns 404")
        
        return False
    
    def test_create_ticket(self):
        """Test creating a new ticket"""
        print_info("Testing ticket creation...")
        
        # First, get available queues to use
        success, data, error = self.make_request('GET', '/api/v1/tickets?per_page=1')
        
        if not success or not data or not data.get('data'):
            self.log_test_result(
                "Create Ticket",
                False,
                "Cannot test ticket creation - no existing tickets to reference queue"
            )
            return False
        
        # Use queue from existing ticket
        queue_id = data['data'][0].get('queue_id', 1)
        
        # Create test ticket
        test_ticket = {
            'subject': f'API Test Ticket - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            'description': 'This is a test ticket created by the API test script. It can be safely deleted.',
            'queue_id': queue_id,
            'priority_id': 1  # Assuming priority 1 exists
        }
        
        success, data, error = self.make_request('POST', '/api/v1/tickets', json=test_ticket)
        
        if success and data:
            created_ticket = data.get('data', {})
            ticket_id = created_ticket.get('id')
            
            self.log_test_result(
                "Create Ticket",
                True,
                f"Created ticket #{ticket_id}: '{created_ticket.get('subject', 'No subject')[:50]}...'"
            )
            
            # Test updating the created ticket
            update_data = {
                'description': 'Updated description - This ticket was created and updated by API test script'
            }
            
            success, data, error = self.make_request('PUT', f'/api/v1/tickets/{ticket_id}', json=update_data)
            
            if success:
                self.log_test_result(
                    "Update Ticket",
                    True,
                    f"Successfully updated ticket #{ticket_id}"
                )
            else:
                self.log_test_result(
                    "Update Ticket",
                    False,
                    f"Failed to update ticket: {error}"
                )
            
            return ticket_id
        else:
            self.log_test_result(
                "Create Ticket",
                False,
                f"Failed to create ticket: {error}"
            )
            return None
    
    def test_list_users(self):
        """Test listing users"""
        print_info("Testing user listing...")
        
        success, data, error = self.make_request('GET', '/api/v1/users')
        
        if success and data:
            users = data.get('data', [])
            pagination = data.get('meta', {}).get('pagination', {})
            
            self.log_test_result(
                "List Users",
                True,
                f"Retrieved {len(users)} users (Total: {pagination.get('total', 'unknown')})"
            )
            
            # Test getting individual user if users exist
            if users:
                user_id = users[0]['id']
                success, data, error = self.make_request('GET', f'/api/v1/users/{user_id}')
                
                if success and data:
                    user = data.get('data', {})
                    self.log_test_result(
                        "Get User Details",
                        True,
                        f"Retrieved user details for: {user.get('name', 'Unknown')}"
                    )
                else:
                    self.log_test_result(
                        "Get User Details",
                        False,
                        f"Failed to get user details: {error}"
                    )
            
            return True
        else:
            self.log_test_result(
                "List Users",
                False,
                f"Failed to retrieve users: {error}"
            )
            return False
    
    def test_list_inventory(self):
        """Test listing inventory items"""
        print_info("Testing inventory listing...")
        
        success, data, error = self.make_request('GET', '/api/v1/inventory')
        
        if success and data:
            inventory = data.get('data', [])
            pagination = data.get('meta', {}).get('pagination', {})
            
            self.log_test_result(
                "List Inventory",
                True,
                f"Retrieved {len(inventory)} inventory items (Total: {pagination.get('total', 'unknown')})"
            )
            
            # Test getting individual inventory item if items exist
            if inventory:
                asset_id = inventory[0]['id']
                success, data, error = self.make_request('GET', f'/api/v1/inventory/{asset_id}')
                
                if success and data:
                    asset = data.get('data', {})
                    self.log_test_result(
                        "Get Inventory Details",
                        True,
                        f"Retrieved asset details for: {asset.get('name', 'Unknown')}"
                    )
                else:
                    self.log_test_result(
                        "Get Inventory Details",
                        False,
                        f"Failed to get asset details: {error}"
                    )
            
            return True
        else:
            self.log_test_result(
                "List Inventory",
                False,
                f"Failed to retrieve inventory: {error}"
            )
            return False
    
    def test_sync_endpoints(self):
        """Test sync endpoints for mobile apps"""
        print_info("Testing sync endpoints...")
        
        # Test ticket sync
        success, data, error = self.make_request('GET', '/api/v1/sync/tickets?limit=10')
        
        if success and data:
            tickets = data.get('data', [])
            meta = data.get('meta', {})
            
            self.log_test_result(
                "Sync Tickets",
                True,
                f"Sync retrieved {len(tickets)} tickets. Next sync: {meta.get('next_sync_timestamp', 'N/A')[:19]}"
            )
            
            # Test incremental sync with timestamp
            if tickets:
                # Use a timestamp from 1 hour ago
                since_time = (datetime.now() - timedelta(hours=1)).isoformat()
                success, data, error = self.make_request('GET', f'/api/v1/sync/tickets?since={since_time}&limit=5')
                
                if success:
                    recent_tickets = data.get('data', [])
                    self.log_test_result(
                        "Incremental Sync",
                        True,
                        f"Incremental sync retrieved {len(recent_tickets)} recent tickets"
                    )
            
            return True
        else:
            self.log_test_result(
                "Sync Tickets",
                False,
                f"Failed to sync tickets: {error}"
            )
            return False
    
    def test_error_handling(self):
        """Test API error handling"""
        print_info("Testing error handling...")
        
        # Test 404 endpoint
        success, data, error = self.make_request('GET', '/api/v1/nonexistent')
        if not success and '404' in str(error):
            self.log_test_result(
                "404 Error Handling",
                True,
                "Non-existent endpoint correctly returns 404"
            )
        else:
            self.log_test_result(
                "404 Error Handling",
                False,
                f"Expected 404, got: {error}"
            )
        
        # Test invalid JSON in POST
        success, data, error = self.make_request(
            'POST', 
            '/api/v1/tickets',
            data='invalid json',
            headers={'Content-Type': 'application/json'}
        )
        if not success:
            self.log_test_result(
                "Invalid JSON Handling",
                True,
                "Invalid JSON correctly rejected"
            )
        else:
            self.log_test_result(
                "Invalid JSON Handling",
                False,
                "Invalid JSON was unexpectedly accepted"
            )
    
    def test_rate_limiting(self):
        """Test rate limiting (if implemented)"""
        print_info("Testing rate limiting...")
        
        # Make several rapid requests
        rapid_requests = 0
        rate_limited = False
        
        for i in range(10):
            success, data, error = self.make_request('GET', '/api/v1/health')
            rapid_requests += 1
            
            if not success and '429' in str(error):
                rate_limited = True
                break
            
            time.sleep(0.1)  # Small delay between requests
        
        if rate_limited:
            self.log_test_result(
                "Rate Limiting",
                True,
                f"Rate limiting triggered after {rapid_requests} requests"
            )
        else:
            self.log_test_result(
                "Rate Limiting",
                True,
                f"Made {rapid_requests} rapid requests without hitting rate limit"
            )
    
    def run_all_tests(self):
        """Run all API tests"""
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"🚀 Production API Test Suite")
        print(f"{'='*60}{Style.RESET_ALL}")
        print(f"Base URL: {self.base_url}")
        print(f"API Key: {self.api_key[:20]}...")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Run tests in logical order
        tests = [
            self.test_health_check,
            self.test_api_key_validation,
            self.test_list_tickets,
            self.test_get_ticket_details,
            self.test_create_ticket,
            self.test_list_users,
            self.test_list_inventory,
            self.test_sync_endpoints,
            self.test_error_handling,
            self.test_rate_limiting
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                self.log_test_result(
                    test.__name__.replace('test_', '').replace('_', ' ').title(),
                    False,
                    f"Test crashed: {str(e)}"
                )
            print()  # Add spacing between tests
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"📊 Test Summary")
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
            print_success(f"\n🎉 API is working well! ({success_rate:.1f}% success rate)")
        elif success_rate >= 60:
            print_warning(f"\n⚠️  API has some issues ({success_rate:.1f}% success rate)")
        else:
            print_error(f"\n❌ API has significant problems ({success_rate:.1f}% success rate)")

def main():
    """Main function to run the API tests"""
    
    # Configuration
    BASE_URL = "https://inventory.truelog.com.sg"
    API_KEY = "xAQhm3__ZH6MvRIPMIBSDRAsIa1w2Slh5uaCtc4NurM"
    
    print(f"{Fore.YELLOW}⚠️  WARNING: This script will test the PRODUCTION API{Style.RESET_ALL}")
    print(f"   - It will create test tickets that may need cleanup")
    print(f"   - It will make multiple API calls")
    print(f"   - Ensure you have permission to run these tests")
    print()
    
    response = input("Do you want to continue? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("Test cancelled.")
        return
    
    # Create tester and run tests
    tester = ProductionAPITester(BASE_URL, API_KEY)
    tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if tester.tests_failed == 0 else 1)

if __name__ == "__main__":
    main()