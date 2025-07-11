#!/usr/bin/env python3

"""
Test return tracking caching functionality
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.store_instances import ticket_store, db_manager
from utils.tracking_cache import TrackingCache
from models.ticket import Ticket
import json

def test_return_tracking_cache():
    logger.info("=== TESTING RETURN TRACKING CACHE ===\n")
    
    db_session = db_manager.get_session()
    try:
        # Find a ticket with return tracking
        tickets = db_session.query(Ticket).filter(Ticket.return_tracking.isnot(None)).limit(1).all()
        if not tickets:
            logger.info("❌ No tickets with return tracking found")
            return
            
        ticket = tickets[0]
        tracking_number = ticket.return_tracking
        ticket_id = ticket.id
        
        logger.info("📦 Testing with ticket {ticket_id}, tracking: {tracking_number}")
        
        # Test 1: Check if cached data exists
        logger.info("\n1. Checking for existing cached data...")
        cached_data = TrackingCache.get_cached_tracking(
            db_session, 
            tracking_number, 
            ticket_id=ticket_id, 
            tracking_type='return',
            max_age_hours=24
        )
        
        if cached_data:
            logger.info("✅ Found cached data!")
            logger.info("   - Cache date: {cached_data.get('cached_at', 'Unknown')}")
            logger.info("   - Events: {len(cached_data.get('tracking_info', []))}")
            logger.info("   - Status: {cached_data.get('shipping_status', 'Unknown')}")
        else:
            logger.info("❌ No cached data found")
            
        # Test 2: Test cache save functionality
        logger.info("\n2. Testing cache save functionality...")
        test_tracking_info = [
            {
                'date': '2024-01-01T12:00:00',
                'status': 'Test Status',
                'location': 'Test Location'
            }
        ]
        
        try:
            TrackingCache.save_tracking_data(
                db_session,
                tracking_number, 
                test_tracking_info, 
                'Test Status',
                ticket_id=ticket_id,
                tracking_type='return'
            )
            logger.info("✅ Cache save successful")
        except Exception as e:
            logger.info("❌ Cache save failed: {str(e)}")
            
        # Test 3: Verify cached data can be retrieved
        logger.info("\n3. Verifying cached data can be retrieved...")
        new_cached_data = TrackingCache.get_cached_tracking(
            db_session, 
            tracking_number, 
            ticket_id=ticket_id, 
            tracking_type='return',
            max_age_hours=24
        )
        
        if new_cached_data and new_cached_data.get('tracking_info'):
            logger.info("✅ Cache retrieval successful")
            logger.info("   - Events: {len(new_cached_data.get('tracking_info', []))}")
        else:
            logger.info("❌ Cache retrieval failed")
            
        logger.info("\n🎉 Return tracking cache test completed!")
        
    except Exception as e:
        logger.info("❌ Error during cache test: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db_session.close()

if __name__ == "__main__":
    test_return_tracking_cache() 