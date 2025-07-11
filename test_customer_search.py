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
    
    logger.info("🔍 Testing Customer Search API Endpoint")
    logger.info("=" * 40)
    
    # Test cases
    test_queries = ["apple", "john", "test", "company"]
    
    for query in test_queries:
        logger.info("\n🔎 Searching for: '{query}'")
        try:
            response = requests.get(search_url, params={'q': query})
            
            if response.status_code == 200:
                results = response.json()
                logger.info("✅ Found {len(results)} results:")
                
                for i, customer in enumerate(results[:3], 1):  # Show first 3 results
                    logger.info("   {i}. {customer['name']}")
                    logger.info("      Company: {customer['company']}")
                    logger.info("      Email: {customer['email']}")
                    logger.info("      Address: {customer['address'][:50]}{'...' if len(customer['address']) > 50 else ''}")
                    print()
                    
                if len(results) > 3:
                    logger.info("   ... and {len(results) - 3} more results")
                    
            elif response.status_code == 401:
                logger.info("❌ Authentication required - need to be logged in")
                break
            else:
                logger.info("❌ Error: {response.status_code} - {response.text}")
                
        except requests.exceptions.ConnectionError:
            logger.info("❌ Cannot connect to {base_url}")
            logger.info("   Make sure the Flask application is running")
            break
        except Exception as e:
            logger.info("❌ Error: {str(e)}")

if __name__ == "__main__":
    test_customer_search() 