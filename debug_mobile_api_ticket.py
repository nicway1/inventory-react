#!/usr/bin/env python3
"""
Debug script to test mobile API ticket detail endpoint and identify 500 errors
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db_manager import DatabaseManager
from models.ticket import Ticket
from models.user import User
from sqlalchemy.orm import joinedload
import traceback
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_ticket_detail_logic(ticket_id):
    """Test the mobile API ticket detail logic with specific ticket"""

    db_manager = DatabaseManager()
    db_session = db_manager.get_session()

    try:
        print(f"Testing ticket ID: {ticket_id}")
        print("=" * 50)

        # Get ticket with all necessary relationships loaded
        ticket = db_session.query(Ticket).options(
            joinedload(Ticket.requester),
            joinedload(Ticket.assigned_to),
            joinedload(Ticket.queue),
            joinedload(Ticket.customer),
            joinedload(Ticket.assets),
            joinedload(Ticket.comments)
        ).filter(Ticket.id == ticket_id).first()

        if not ticket:
            print(f"❌ Ticket {ticket_id} not found")
            return False

        print(f"✅ Ticket found: {ticket.subject}")
        print(f"Status: {ticket.status}")
        print(f"Category: {ticket.category}")

        # Test each component that could cause errors
        errors = []

        # Test basic fields
        try:
            basic_data = {
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
            print("✅ Basic fields: OK")
        except Exception as e:
            errors.append(f"Basic fields error: {e}")
            print(f"❌ Basic fields error: {e}")

        # Test requester
        try:
            requester_data = {
                'id': ticket.requester.id,
                'name': ticket.requester.username,
                'email': ticket.requester.email,
                'username': ticket.requester.username
            } if ticket.requester else None
            print(f"✅ Requester: {requester_data}")
        except Exception as e:
            errors.append(f"Requester error: {e}")
            print(f"❌ Requester error: {e}")

        # Test assigned_to
        try:
            assigned_to_data = {
                'id': ticket.assigned_to.id,
                'name': ticket.assigned_to.username,
                'email': ticket.assigned_to.email,
                'username': ticket.assigned_to.username
            } if ticket.assigned_to else None
            print(f"✅ Assigned to: {assigned_to_data}")
        except Exception as e:
            errors.append(f"Assigned to error: {e}")
            print(f"❌ Assigned to error: {e}")

        # Test queue
        try:
            queue_data = {
                'id': ticket.queue.id,
                'name': ticket.queue.name
            } if ticket.queue else None
            print(f"✅ Queue: {queue_data}")
        except Exception as e:
            errors.append(f"Queue error: {e}")
            print(f"❌ Queue error: {e}")

        # Test customer (potential issue here)
        try:
            if ticket.customer:
                print(f"Customer exists: {ticket.customer.name}")
                print(f"Customer has company: {ticket.customer.company is not None}")

                # Test the problematic company logic
                company_data = None
                if ticket.customer.company:  # Fixed logic
                    company_data = {
                        'id': ticket.customer.company.id,
                        'name': ticket.customer.company.name
                    }

                customer_data = {
                    'id': ticket.customer.id,
                    'name': ticket.customer.name,
                    'email': ticket.customer.email,
                    'phone': ticket.customer.phone,
                    'address': ticket.customer.address,
                    'company': company_data
                }
                print(f"✅ Customer: {customer_data}")
            else:
                customer_data = None
                print("✅ Customer: None")
        except Exception as e:
            errors.append(f"Customer error: {e}")
            print(f"❌ Customer error: {e}")
            traceback.print_exc()

        # Test assets
        try:
            assets_data = []
            if ticket.assets:
                print(f"Assets count: {len(ticket.assets)}")
                for asset in ticket.assets:
                    asset_data = {
                        'id': asset.id,
                        'serial_number': asset.serial_num,
                        'asset_tag': asset.asset_tag,
                        'model': asset.model,
                        'manufacturer': asset.manufacturer,
                        'status': asset.status.value if asset.status else None
                    }
                    assets_data.append(asset_data)
            print(f"✅ Assets: {len(assets_data)} items")
        except Exception as e:
            errors.append(f"Assets error: {e}")
            print(f"❌ Assets error: {e}")
            traceback.print_exc()

        # Test case progress
        try:
            case_progress = {
                'case_created': bool(ticket.created_at),
                'assets_assigned': bool(ticket.assets and len(ticket.assets) > 0),
                'tracking_added': bool(ticket.shipping_tracking),
                'delivered': bool(ticket.shipping_status and 'delivered' in str(ticket.shipping_status).lower()) if ticket.shipping_status else False
            }
            print(f"✅ Case progress: {case_progress}")
        except Exception as e:
            errors.append(f"Case progress error: {e}")
            print(f"❌ Case progress error: {e}")
            traceback.print_exc()

        # Test tracking
        try:
            tracking_data = {
                'shipping_tracking': ticket.shipping_tracking,
                'shipping_carrier': ticket.shipping_carrier,
                'shipping_status': ticket.shipping_status,
                'shipping_address': ticket.shipping_address,
                'return_tracking': ticket.return_tracking,
                'return_status': ticket.return_status
            }
            print(f"✅ Tracking: {tracking_data}")
        except Exception as e:
            errors.append(f"Tracking error: {e}")
            print(f"❌ Tracking error: {e}")

        # Test comments
        try:
            comments_data = []
            if hasattr(ticket, 'comments') and ticket.comments:
                print(f"Comments count: {len(ticket.comments)}")
                for comment in ticket.comments:
                    comment_data = {
                        'id': comment.id,
                        'content': comment.content,
                        'created_at': comment.created_at.isoformat() if comment.created_at else None,
                        'user': {
                            'id': comment.user.id,
                            'name': comment.user.username,
                            'username': comment.user.username
                        } if comment.user else None
                    }
                    comments_data.append(comment_data)
            print(f"✅ Comments: {len(comments_data)} items")
        except Exception as e:
            errors.append(f"Comments error: {e}")
            print(f"❌ Comments error: {e}")
            traceback.print_exc()

        # Summary
        print("\n" + "=" * 50)
        if errors:
            print(f"❌ FOUND {len(errors)} ERRORS:")
            for i, error in enumerate(errors, 1):
                print(f"{i}. {error}")
            return False
        else:
            print("✅ ALL TESTS PASSED - No errors found")
            return True

    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        traceback.print_exc()
        return False
    finally:
        db_session.close()

def find_test_tickets():
    """Find tickets to test with different characteristics"""

    db_manager = DatabaseManager()
    db_session = db_manager.get_session()

    try:
        # Get tickets with different characteristics
        tickets = db_session.query(Ticket).limit(10).all()

        print("Available tickets for testing:")
        print("=" * 50)

        for ticket in tickets:
            print(f"ID: {ticket.id}")
            print(f"  Subject: {ticket.subject}")
            print(f"  Has Customer: {ticket.customer is not None}")
            print(f"  Has Assets: {ticket.assets and len(ticket.assets) > 0}")
            print(f"  Has Requester: {ticket.requester is not None}")
            print(f"  Has Assigned: {ticket.assigned_to is not None}")
            print()

        return [t.id for t in tickets]

    finally:
        db_session.close()

if __name__ == "__main__":
    print("Mobile API Ticket Detail Debug Tool")
    print("=" * 50)

    # Find available tickets
    ticket_ids = find_test_tickets()

    if not ticket_ids:
        print("No tickets found in database")
        sys.exit(1)

    # Test specific ticket if provided
    if len(sys.argv) > 1:
        test_ticket_id = int(sys.argv[1])
        print(f"\nTesting specific ticket: {test_ticket_id}")
        test_ticket_detail_logic(test_ticket_id)
    else:
        # Test first few tickets
        print(f"\nTesting first 3 tickets...")
        for ticket_id in ticket_ids[:3]:
            print(f"\n{'='*20} TESTING TICKET {ticket_id} {'='*20}")
            success = test_ticket_detail_logic(ticket_id)
            if not success:
                print(f"❌ Ticket {ticket_id} has issues!")
                break
            print(f"✅ Ticket {ticket_id} passed all tests")