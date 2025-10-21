#!/usr/bin/env python3
"""
Test script for Queue API endpoints
Run this to verify queue functionality is working correctly
"""

import requests
import json
from typing import Optional

# Configuration
BASE_URL = "https://inventory.truelog.com.sg"
API_KEY = None  # Will be set from user input or environment

def print_header(text):
    """Print a formatted header"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def print_response(response):
    """Print formatted response"""
    print(f"\nStatus Code: {response.status_code}")
    print("\nResponse:")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)

def test_queues_endpoint(api_key: str):
    """Test GET /api/v1/queues endpoint"""
    print_header("Testing GET /api/v1/queues")

    url = f"{BASE_URL}/api/v1/queues"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    print(f"URL: {url}")
    print(f"Headers: {headers}")

    try:
        response = requests.get(url, headers=headers)
        print_response(response)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                queues = data.get('data', [])
                print(f"\n✅ SUCCESS: Found {len(queues)} queues")
                return queues
            else:
                print(f"\n❌ FAILED: {data.get('message', 'Unknown error')}")
        else:
            print(f"\n❌ FAILED: HTTP {response.status_code}")
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")

    return None

def test_tickets_with_queue_filter(api_key: str, queue_id: Optional[int] = None):
    """Test GET /api/v1/tickets with queue filtering"""

    if queue_id:
        print_header(f"Testing GET /api/v1/tickets?queue_id={queue_id}")
        url = f"{BASE_URL}/api/v1/tickets?queue_id={queue_id}"
    else:
        print_header("Testing GET /api/v1/tickets (All Queues)")
        url = f"{BASE_URL}/api/v1/tickets"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    print(f"URL: {url}")

    try:
        response = requests.get(url, headers=headers)
        print_response(response)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                tickets = data.get('data', [])
                print(f"\n✅ SUCCESS: Found {len(tickets)} tickets")

                # Check if queue fields are present
                if tickets:
                    first_ticket = tickets[0]
                    has_queue_id = 'queue_id' in first_ticket
                    has_queue_name = 'queue_name' in first_ticket

                    print(f"\nQueue Fields Present:")
                    print(f"  - queue_id: {'✅' if has_queue_id else '❌'}")
                    print(f"  - queue_name: {'✅' if has_queue_name else '❌'}")

                    if has_queue_id or has_queue_name:
                        print(f"\n  Example: queue_id={first_ticket.get('queue_id')}, queue_name={first_ticket.get('queue_name')}")

                return tickets
            else:
                print(f"\n❌ FAILED: {data.get('message', 'Unknown error')}")
        else:
            print(f"\n❌ FAILED: HTTP {response.status_code}")
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")

    return None

def test_single_ticket(api_key: str, ticket_id: int):
    """Test GET /api/v1/tickets/{id}"""
    print_header(f"Testing GET /api/v1/tickets/{ticket_id}")

    url = f"{BASE_URL}/api/v1/tickets/{ticket_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    print(f"URL: {url}")

    try:
        response = requests.get(url, headers=headers)
        print_response(response)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                ticket = data.get('data', {})
                has_queue_id = 'queue_id' in ticket
                has_queue_name = 'queue_name' in ticket

                print(f"\n✅ SUCCESS: Retrieved ticket {ticket_id}")
                print(f"\nQueue Fields Present:")
                print(f"  - queue_id: {'✅' if has_queue_id else '❌'}")
                print(f"  - queue_name: {'✅' if has_queue_name else '❌'}")

                if has_queue_id or has_queue_name:
                    print(f"\n  Values: queue_id={ticket.get('queue_id')}, queue_name={ticket.get('queue_name')}")

                return ticket
            else:
                print(f"\n❌ FAILED: {data.get('message', 'Unknown error')}")
        else:
            print(f"\n❌ FAILED: HTTP {response.status_code}")
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")

    return None

def test_sync_tickets(api_key: str):
    """Test GET /api/v1/sync/tickets"""
    print_header("Testing GET /api/v1/sync/tickets")

    url = f"{BASE_URL}/api/v1/sync/tickets?limit=5"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    print(f"URL: {url}")

    try:
        response = requests.get(url, headers=headers)
        print_response(response)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                tickets = data.get('data', [])
                print(f"\n✅ SUCCESS: Retrieved {len(tickets)} tickets for sync")

                # Check if queue fields are present
                if tickets:
                    first_ticket = tickets[0]
                    has_queue_id = 'queue_id' in first_ticket
                    has_queue_name = 'queue_name' in first_ticket
                    has_category = 'category' in first_ticket
                    has_customer_name = 'customer_name' in first_ticket
                    has_assigned_name = 'assigned_to_name' in first_ticket

                    print(f"\nNew Fields Present (from recent update):")
                    print(f"  - queue_id: {'✅' if has_queue_id else '❌'}")
                    print(f"  - queue_name: {'✅' if has_queue_name else '❌'}")
                    print(f"  - category: {'✅' if has_category else '❌'}")
                    print(f"  - customer_name: {'✅' if has_customer_name else '❌'}")
                    print(f"  - assigned_to_name: {'✅' if has_assigned_name else '❌'}")

                return tickets
            else:
                print(f"\n❌ FAILED: {data.get('message', 'Unknown error')}")
        else:
            print(f"\n❌ FAILED: HTTP {response.status_code}")
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")

    return None

def main():
    """Main test function"""
    print_header("Queue API Testing Script")
    print("\nThis script will test all queue-related API endpoints")
    print(f"Base URL: {BASE_URL}")

    # Get API key
    api_key = input("\nEnter your API key: ").strip()

    if not api_key:
        print("\n❌ ERROR: API key is required")
        return

    # Test 1: Get queues list
    queues = test_queues_endpoint(api_key)

    # Test 2: Get all tickets (check queue fields)
    tickets = test_tickets_with_queue_filter(api_key)

    # Test 3: Filter by queue (if we have queues)
    if queues and len(queues) > 0:
        first_queue = queues[0]
        queue_id = first_queue.get('id')
        if queue_id:
            test_tickets_with_queue_filter(api_key, queue_id)

    # Test 4: Get single ticket (if we have tickets)
    if tickets and len(tickets) > 0:
        first_ticket = tickets[0]
        ticket_id = first_ticket.get('id')
        if ticket_id:
            test_single_ticket(api_key, ticket_id)

    # Test 5: Sync endpoint
    test_sync_tickets(api_key)

    print_header("Testing Complete")
    print("\nSummary:")
    print("- Tested /api/v1/queues endpoint")
    print("- Tested /api/v1/tickets endpoint (with queue fields)")
    print("- Tested /api/v1/tickets endpoint (with queue filter)")
    print("- Tested /api/v1/tickets/{id} endpoint")
    print("- Tested /api/v1/sync/tickets endpoint")
    print("\nCheck the output above for any ❌ failures")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
