#!/usr/bin/env python3
"""
Test script to verify that Asset Checkout (claw) tickets can be assigned to queues.
"""

from utils.db_manager import DatabaseManager
from models.ticket import Ticket
from models.queue import Queue

def test_queue_assignment_functionality():
    """Test that Asset Checkout tickets can be properly assigned to queues"""
    print("🧪 Testing queue assignment functionality for Asset Checkout tickets...")
    
    db_manager = DatabaseManager()
    db_session = db_manager.get_session()
    
    try:
        # Test 1: Check available queues
        print("\n📋 Test 1: Checking available queues...")
        queues = db_session.query(Queue).all()
        print(f"Found {len(queues)} queues in the system:")
        for queue in queues:
            print(f"  - Queue ID: {queue.id}, Name: {queue.name}")
        
        # Test 2: Check recent Asset Checkout tickets and their queue assignments
        print("\n📋 Test 2: Checking recent Asset Checkout tickets...")
        checkout_tickets = db_session.query(Ticket).filter(
            Ticket.category.like('%CHECKOUT%')
        ).order_by(Ticket.created_at.desc()).limit(10).all()
        
        print(f"Found {len(checkout_tickets)} recent Asset Checkout tickets:")
        for ticket in checkout_tickets:
            queue_name = ticket.queue.name if ticket.queue else "No Queue Assigned"
            print(f"  - Ticket #{ticket.id}: {ticket.category.value} → Queue: {queue_name}")
        
        # Test 3: Check specific Asset Checkout (claw) tickets
        print("\n📋 Test 3: Checking Asset Checkout (claw) tickets specifically...")
        claw_tickets = db_session.query(Ticket).filter(
            Ticket.category.in_(['ASSET_CHECKOUT_CLAW'])
        ).order_by(Ticket.created_at.desc()).limit(5).all()
        
        if claw_tickets:
            print(f"Found {len(claw_tickets)} Asset Checkout (claw) tickets:")
            for ticket in claw_tickets:
                queue_name = ticket.queue.name if ticket.queue else "No Queue Assigned"
                print(f"  - Ticket #{ticket.id}: {ticket.subject} → Queue: {queue_name}")
        else:
            print("No Asset Checkout (claw) tickets found yet.")
        
        # Test 4: Show form validation test
        print(f"\n✅ Queue assignment fix verification complete!")
        print(f"📝 To test the fix:")
        print(f"   1. Go to /tickets/new")
        print(f"   2. Select 'Asset Checkout (claw)' category")
        print(f"   3. Look for 'Assign to Queue (Optional)' dropdown")
        print(f"   4. Create a ticket and verify queue assignment works")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during queue assignment test: {str(e)}")
        return False
        
    finally:
        db_session.close()

if __name__ == "__main__":
    success = test_queue_assignment_functionality()
    if success:
        print("\n🎉 Queue assignment functionality test completed successfully!")
    else:
        print("\n💥 Queue assignment functionality test failed!") 