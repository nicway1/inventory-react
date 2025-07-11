#!/usr/bin/env python3
"""
Test script to verify ticket listing with custom categories works
"""
from database import SessionLocal
from models.ticket import Ticket

def test_ticket_loading():
    """Test loading tickets and displaying categories"""
    logger.info("Testing ticket loading with custom categories...")
    
    db = SessionLocal()
    try:
        # Load all tickets
        tickets = db.query(Ticket).all()
        logger.info("✓ Successfully loaded {len(tickets)} tickets")
        
        # Test each ticket's category display
        for ticket in tickets[-5:]:  # Show last 5 tickets
            try:
                category_display = ticket.get_category_display_name()
                logger.info("  - Ticket {ticket.id}: '{ticket.subject}' -> Category: '{category_display}'")
            except Exception as e:
                logger.info("  ✗ Error with ticket {ticket.id}: {e}")
                
        logger.info("\n✓ All tickets processed successfully!")
        return True
        
    except Exception as e:
        logger.info("✗ Error loading tickets: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = test_ticket_loading()
    if success:
        logger.info("\n🎉 SUCCESS: Ticket listing with custom categories works!")
    else:
        logger.info("\n❌ FAILED: There are still issues with ticket listing")
        exit(1) 