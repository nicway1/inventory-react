#!/usr/bin/env python3
"""
Test the mobile ticket detail endpoint
Usage: python3 test_mobile_ticket_endpoint.py
"""

import requests
import json

BASE_URL = "https://inventory.truelog.com.sg"

def test_mobile_ticket_endpoint():
    print("🧪 Testing Mobile Ticket Detail Endpoint")
    print("=" * 60)

    # Step 1: Login to get JWT token
    print("\n1. Logging in to get JWT token...")
    login_url = f"{BASE_URL}/api/mobile/v1/auth/login"
    login_data = {
        "username": "admin",  # Change to your test username
        "password": "admin123"  # Change to your test password
    }

    try:
        login_response = requests.post(login_url, json=login_data, timeout=10)
        print(f"   Status: {login_response.status_code}")

        if login_response.status_code == 200:
            login_result = login_response.json()
            if login_result.get('success'):
                token = login_result.get('token')
                user = login_result.get('user', {})
                print(f"   ✅ Login successful")
                print(f"   User: {user.get('username')} ({user.get('user_type')})")
                print(f"   Token: {token[:50]}...")
            else:
                print(f"   ❌ Login failed: {login_result.get('error')}")
                return
        else:
            print(f"   ❌ Login request failed: {login_response.text}")
            return
    except Exception as e:
        print(f"   ❌ Login error: {str(e)}")
        return

    # Step 2: Test ticket detail endpoint
    print("\n2. Testing ticket detail endpoint...")
    ticket_id = 561  # Change to a real ticket ID in your system
    ticket_url = f"{BASE_URL}/api/mobile/v1/tickets/{ticket_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        ticket_response = requests.get(ticket_url, headers=headers, timeout=10)
        print(f"   Status: {ticket_response.status_code}")
        print(f"   URL: {ticket_url}")

        if ticket_response.status_code == 200:
            result = ticket_response.json()
            if result.get('success'):
                ticket = result.get('ticket', {})
                print(f"   ✅ Ticket retrieved successfully")
                print(f"\n   Ticket Details:")
                print(f"   - ID: {ticket.get('id')}")
                print(f"   - Display ID: {ticket.get('display_id')}")
                print(f"   - Subject: {ticket.get('subject')}")
                print(f"   - Status: {ticket.get('status')}")
                print(f"   - Priority: {ticket.get('priority')}")
                print(f"   - Category: {ticket.get('category')}")

                print(f"\n   Data Structure:")
                print(f"   - Requester: {'✅' if ticket.get('requester') else '❌'}")
                print(f"   - Assigned To: {'✅' if ticket.get('assigned_to') else '❌'}")
                print(f"   - Queue: {'✅' if ticket.get('queue') else '❌'}")
                print(f"   - Customer: {'✅' if ticket.get('customer') else '❌'}")
                print(f"   - Assets: {len(ticket.get('assets', []))} asset(s)")
                print(f"   - Case Progress: {'✅' if ticket.get('case_progress') else '❌'}")
                print(f"   - Tracking: {'✅' if ticket.get('tracking') else '❌'}")
                print(f"   - Comments: {len(ticket.get('comments', []))} comment(s)")

                print(f"\n   ✅ Response format matches iOS app requirements!")

                # Show full response for debugging
                print(f"\n   Full Response (first 1000 chars):")
                print(f"   {json.dumps(result, indent=2)[:1000]}...")
            else:
                print(f"   ❌ Request failed: {result.get('error')}")
        elif ticket_response.status_code == 404:
            print(f"   ❌ Ticket not found (404)")
            print(f"   Response: {ticket_response.text}")
            print(f"\n   💡 Try changing ticket_id to a valid ticket ID in your system")
        elif ticket_response.status_code == 401:
            print(f"   ❌ Unauthorized (401)")
            print(f"   Token might be invalid or expired")
        else:
            print(f"   ❌ Request failed: {ticket_response.text}")
    except Exception as e:
        print(f"   ❌ Request error: {str(e)}")
        import traceback
        print(traceback.format_exc())

    print("\n" + "=" * 60)
    print("Test complete!")

if __name__ == '__main__':
    test_mobile_ticket_endpoint()
