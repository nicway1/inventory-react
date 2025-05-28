#!/usr/bin/env python3
"""
Test script for customer search functionality
"""

import requests
import json

def test_customer_search():
    """Test the customer search API endpoint"""
    
    base_url = "http://localhost:5001"  # Adjust port if needed
    search_url = f"{base_url}/api/customers/search"
    
    print("🔍 Testing Customer Search API Endpoint")
    print("=" * 40)
    
    # Test cases
    test_queries = ["apple", "john", "test", "company"]
    
    for query in test_queries:
        print(f"\n🔎 Searching for: '{query}'")
        try:
            response = requests.get(search_url, params={'q': query})
            
            if response.status_code == 200:
                results = response.json()
                print(f"✅ Found {len(results)} results:")
                
                for i, customer in enumerate(results[:3], 1):  # Show first 3 results
                    print(f"   {i}. {customer['name']}")
                    print(f"      Company: {customer['company']}")
                    print(f"      Email: {customer['email']}")
                    print(f"      Address: {customer['address'][:50]}{'...' if len(customer['address']) > 50 else ''}")
                    print()
                    
                if len(results) > 3:
                    print(f"   ... and {len(results) - 3} more results")
                    
            elif response.status_code == 401:
                print("❌ Authentication required - need to be logged in")
                break
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
                
        except requests.exceptions.ConnectionError:
            print(f"❌ Cannot connect to {base_url}")
            print("   Make sure the Flask application is running")
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_customer_search() 