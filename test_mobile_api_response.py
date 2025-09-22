#!/usr/bin/env python3
"""
Test script to check actual mobile API responses and identify data type issues
"""

import json
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from routes.mobile_api import get_ticket_detail
from models.ticket import Ticket
from models.user import User
from utils.db_manager import DatabaseManager
from flask import Flask, request
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_mobile_api_response():
    """Test the mobile API response structure for different tickets"""

    # Create a minimal Flask app for testing
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-key'

    db_manager = DatabaseManager()

    with app.app_context():
        db_session = db_manager.get_session()
        try:
            # Get a few different tickets to test
            tickets = db_session.query(Ticket).limit(3).all()

            if not tickets:
                print("No tickets found in database for testing")
                return

            print("Testing Mobile API Response Structure")
            print("=" * 50)

            for i, ticket in enumerate(tickets, 1):
                print(f"\n--- TICKET {i} (ID: {ticket.id}) ---")
                print(f"Subject: {ticket.subject}")
                print(f"Category: {ticket.category}")
                print(f"Has Customer: {ticket.customer is not None}")
                print(f"Has Assets: {ticket.assets and len(ticket.assets) > 0}")
                print(f"Has Requester: {ticket.requester is not None}")
                print(f"Has Assigned To: {ticket.assigned_to is not None}")

                # Test the actual data structure
                ticket_data = {
                    'id': ticket.id,
                    'display_id': ticket.display_id,
                    'subject': ticket.subject,
                    'description': ticket.description,
                    'status': ticket.status.value if ticket.status else None,
                    'priority': ticket.priority.value if ticket.priority else None,
                    'category': ticket.category.value if ticket.category else None,
                    'created_at': ticket.created_at.isoformat() if ticket.created_at else None,
                    'updated_at': ticket.updated_at.isoformat() if ticket.updated_at else None,
                    'notes': ticket.notes,
                }

                # Test requester field
                print(f"\nRequester Analysis:")
                if ticket.requester:
                    print(f"  - Requester object exists: {type(ticket.requester)}")
                    print(f"  - Has first_name: {hasattr(ticket.requester, 'first_name')}")
                    print(f"  - Has last_name: {hasattr(ticket.requester, 'last_name')}")
                    print(f"  - first_name value: {getattr(ticket.requester, 'first_name', 'None')}")
                    print(f"  - last_name value: {getattr(ticket.requester, 'last_name', 'None')}")

                    # Safe name construction
                    first_name = getattr(ticket.requester, 'first_name', '') or ''
                    last_name = getattr(ticket.requester, 'last_name', '') or ''
                    full_name = f"{first_name} {last_name}".strip() or ticket.requester.username

                    ticket_data['requester'] = {
                        'id': ticket.requester.id,
                        'name': full_name,
                        'email': ticket.requester.email,
                        'username': ticket.requester.username
                    }
                    print(f"  - Generated name: '{full_name}'")
                else:
                    ticket_data['requester'] = None
                    print("  - No requester found")

                # Test assigned_to field
                print(f"\nAssigned To Analysis:")
                if ticket.assigned_to:
                    print(f"  - Assigned to object exists: {type(ticket.assigned_to)}")
                    first_name = getattr(ticket.assigned_to, 'first_name', '') or ''
                    last_name = getattr(ticket.assigned_to, 'last_name', '') or ''
                    full_name = f"{first_name} {last_name}".strip() or ticket.assigned_to.username

                    ticket_data['assigned_to'] = {
                        'id': ticket.assigned_to.id,
                        'name': full_name,
                        'email': ticket.assigned_to.email,
                        'username': ticket.assigned_to.username
                    }
                    print(f"  - Generated name: '{full_name}'")
                else:
                    ticket_data['assigned_to'] = None
                    print("  - No assigned user found")

                # Test queue field
                print(f"\nQueue Analysis:")
                if ticket.queue:
                    print(f"  - Queue object exists: {type(ticket.queue)}")
                    ticket_data['queue'] = {
                        'id': ticket.queue.id,
                        'name': ticket.queue.name
                    }
                    print(f"  - Queue name: '{ticket.queue.name}'")
                else:
                    ticket_data['queue'] = None
                    print("  - No queue found")

                # Test customer field
                print(f"\nCustomer Analysis:")
                if ticket.customer:
                    print(f"  - Customer object exists: {type(ticket.customer)}")
                    print(f"  - Customer name: {ticket.customer.name}")
                    print(f"  - Has company: {ticket.customer.company is not None}")

                    customer_data = {
                        'id': ticket.customer.id,
                        'name': ticket.customer.name,
                        'email': ticket.customer.email,
                        'phone': ticket.customer.phone,
                        'address': ticket.customer.address,
                    }

                    if ticket.customer.company:
                        customer_data['company'] = {
                            'id': ticket.customer.company.id,
                            'name': ticket.customer.company.name
                        }
                    else:
                        customer_data['company'] = None

                    ticket_data['customer'] = customer_data
                    print(f"  - Company: {customer_data['company']}")
                else:
                    ticket_data['customer'] = None
                    print("  - No customer found")

                # Test assets
                print(f"\nAssets Analysis:")
                if ticket.assets:
                    print(f"  - Assets count: {len(ticket.assets)}")
                    assets_data = []
                    for asset in ticket.assets:
                        assets_data.append({
                            'id': asset.id,
                            'serial_number': asset.serial_num,
                            'asset_tag': asset.asset_tag,
                            'model': asset.model,
                            'manufacturer': asset.manufacturer,
                            'status': asset.status.value if asset.status else None
                        })
                    ticket_data['assets'] = assets_data
                else:
                    ticket_data['assets'] = []
                    print("  - No assets found")

                # Test case progress
                ticket_data['case_progress'] = {
                    'case_created': bool(ticket.created_at),
                    'assets_assigned': bool(ticket.assets and len(ticket.assets) > 0),
                    'tracking_added': bool(ticket.shipping_tracking),
                    'delivered': bool(ticket.shipping_status and 'delivered' in ticket.shipping_status.lower())
                }

                # Test tracking
                ticket_data['tracking'] = {
                    'shipping_tracking': ticket.shipping_tracking,
                    'shipping_carrier': ticket.shipping_carrier,
                    'shipping_status': ticket.shipping_status,
                    'shipping_address': ticket.shipping_address,
                    'return_tracking': ticket.return_tracking,
                    'return_status': ticket.return_status
                }

                # Test comments
                if hasattr(ticket, 'comments') and ticket.comments:
                    comments_data = []
                    for comment in ticket.comments:
                        comment_data = {
                            'id': comment.id,
                            'content': comment.content,
                            'created_at': comment.created_at.isoformat() if comment.created_at else None,
                        }

                        if comment.user:
                            first_name = getattr(comment.user, 'first_name', '') or ''
                            last_name = getattr(comment.user, 'last_name', '') or ''
                            full_name = f"{first_name} {last_name}".strip() or comment.user.username

                            comment_data['user'] = {
                                'id': comment.user.id,
                                'name': full_name,
                                'username': comment.user.username
                            }
                        else:
                            comment_data['user'] = None

                        comments_data.append(comment_data)
                    ticket_data['comments'] = comments_data
                else:
                    ticket_data['comments'] = []

                # Output the JSON structure
                print(f"\n--- JSON RESPONSE STRUCTURE ---")
                print(json.dumps(ticket_data, indent=2, default=str))

                # Data type analysis
                print(f"\n--- DATA TYPES ANALYSIS ---")
                for key, value in ticket_data.items():
                    print(f"{key}: {type(value)} = {value if value is not None else 'NULL'}")

                print("\n" + "="*80)

        finally:
            db_session.close()

if __name__ == "__main__":
    test_mobile_api_response()