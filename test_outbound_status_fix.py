#!/usr/bin/env python3

"""
Test outbound tracking status update functionality
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.store_instances import ticket_store, db_manager
from models.ticket import Ticket
import json

def test_outbound_status_update():
    logger.info("=== TESTING OUTBOUND STATUS UPDATE ===\n")
    
    db_session = db_manager.get_session()
    try:
        # Find a ticket with outbound tracking
        tickets = db_session.query(Ticket).filter(Ticket.shipping_tracking.isnot(None)).limit(1).all()
        if not tickets:
            logger.info("❌ No tickets with outbound tracking found")
            return
            
        ticket = tickets[0]
        tracking_number = ticket.shipping_tracking
        ticket_id = ticket.id
        
        logger.info("📦 Testing with ticket {ticket_id}, tracking: {tracking_number}")
        logger.info("   Current status: {ticket.shipping_status}")
        
        # Simulate a status update (like what happens after API call)
        logger.info("\n🔄 Simulating status update to 'Delivered'...")
        ticket.shipping_status = "Delivered"
        ticket.updated_at = db_manager.datetime.datetime.now()
        db_session.commit()
        
        logger.info("✅ Status updated in database")
        
        # Verify the update
        fresh_ticket = db_session.query(Ticket).get(ticket_id)
        logger.info("   New status: {fresh_ticket.shipping_status}")
        
        # Reset to original status for testing
        logger.info("\n🔄 Resetting status to 'Pending' for testing...")
        fresh_ticket.shipping_status = "Pending"
        db_session.commit()
        
        logger.info("✅ Status reset for testing")
        logger.info("\n🎉 Outbound status update test completed!")
        
    except Exception as e:
        logger.info("❌ Error during status test: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db_session.close()

if __name__ == "__main__":
    test_outbound_status_update() 