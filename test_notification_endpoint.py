#!/usr/bin/env python3

import logging
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.db_manager import DatabaseManager
from utils.notification_service import NotificationService
from models.user import User
from models.ticket import Ticket

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_notification_endpoint_logic():
    logger.info("=== TESTING NOTIFICATION ENDPOINT LOGIC ===\n")
    
    # Initialize database manager
    db_manager = DatabaseManager()
    notification_service = NotificationService(db_manager)
    
    try:
        db_session = db_manager.get_session()
        
        # Get a test user
        user = db_session.query(User).first()
        if not user:
            logger.error("No users found in database")
            return
        
        # Get a test ticket
        ticket = db_session.query(Ticket).first()
        if not ticket:
            logger.error("No tickets found in database")
            return
        
        logger.info(f"Testing with user: {user.username} (ID: {user.id})")
        logger.info(f"Testing with ticket: #{ticket.display_id} (ID: {ticket.id})")
        
        # Test the same logic as the endpoint
        success = notification_service.create_mention_notification(
            mentioned_user_id=user.id,
            commenter_user_id=user.id,
            ticket_id=ticket.id,
            comment_content="This is a test @mention notification to see the toast popup!"
        )
        
        if success:
            logger.info("✓ Test notification created successfully")
            
            # Check if it was actually created
            notifications = notification_service.get_user_notifications(user.id, limit=1)
            if notifications:
                latest = notifications[0]
                logger.info(f"✓ Latest notification: {latest.title}")
                logger.info(f"  Message: {latest.message}")
                logger.info(f"  Created: {latest.created_at}")
            else:
                logger.warning("⚠ No notifications found after creation")
        else:
            logger.error("✗ Failed to create test notification")
        
        logger.info("\n=== TEST COMPLETED ===")
        
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db_session.close()

if __name__ == "__main__":
    test_notification_endpoint_logic()