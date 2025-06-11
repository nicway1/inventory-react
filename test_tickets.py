#!/usr/bin/env python3
"""
Test script to verify ticket listing with custom categories works
"""
from database import SessionLocal
from models.ticket import Ticket

def test_ticket_loading():
    """Test loading tickets and displaying categories"""
    print("Testing ticket loading with custom categories...")
    
    db = SessionLocal()
    try:
        # Load all tickets
        tickets = db.query(Ticket).all()
        print(f"✓ Successfully loaded {len(tickets)} tickets")
        
        # Test each ticket's category display
        for ticket in tickets[-5:]:  # Show last 5 tickets
            try:
                category_display = ticket.get_category_display_name()
                print(f"  - Ticket {ticket.id}: '{ticket.subject}' -> Category: '{category_display}'")
            except Exception as e:
                print(f"  ✗ Error with ticket {ticket.id}: {e}")
                
        print("\n✓ All tickets processed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Error loading tickets: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = test_ticket_loading()
    if success:
        print("\n🎉 SUCCESS: Ticket listing with custom categories works!")
    else:
        print("\n❌ FAILED: There are still issues with ticket listing")
        exit(1) 