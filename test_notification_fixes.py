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

def test_notification_fixes():
    logger.info("=== TESTING NOTIFICATION FIXES ===\n")
    
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
        
        # Test 1: Create a test notification
        logger.info("\n1. Creating test notification...")
        success = notification_service.create_mention_notification(
            mentioned_user_id=user.id,
            commenter_user_id=user.id,  # This should be different in real scenario
            ticket_id=ticket.id,
            comment_content="Test notification for fixing click and mark all read functionality"
        )
        
        if success:
            logger.info("✓ Test notification created")
        else:
            logger.error("✗ Failed to create test notification")
            return
        
        # Test 2: Get notifications (simulating the API call)
        logger.info("\n2. Getting user notifications...")
        notifications = notification_service.get_user_notifications(user.id, limit=5)
        logger.info(f"✓ Found {len(notifications)} notifications")
        
        for notification in notifications:
            logger.info(f"  - {notification.title}")
            logger.info(f"    Message: {notification.message}")
            logger.info(f"    Reference: {notification.reference_type}#{notification.reference_id}")
            logger.info(f"    Read: {notification.is_read}")
        
        # Test 3: Mark all as read (simulating the API call)
        logger.info("\n3. Testing mark all as read...")
        success = notification_service.mark_all_as_read(user.id)
        
        if success:
            logger.info("✓ Mark all as read succeeded")
            
            # Verify they're marked as read
            updated_notifications = notification_service.get_user_notifications(user.id, limit=5)
            unread_count = sum(1 for n in updated_notifications if not n.is_read)
            logger.info(f"✓ Unread count after mark all: {unread_count}")
        else:
            logger.error("✗ Mark all as read failed")
        
        # Test 4: Test individual mark as read
        if notifications:
            logger.info("\n4. Testing individual mark as read...")
            # Create a new notification to test individual marking
            notification_service.create_mention_notification(
                mentioned_user_id=user.id,
                commenter_user_id=user.id,
                ticket_id=ticket.id,
                comment_content="Another test notification for individual marking"
            )
            
            fresh_notifications = notification_service.get_user_notifications(user.id, limit=1)
            if fresh_notifications:
                test_notification = fresh_notifications[0]
                success = notification_service.mark_notification_as_read(test_notification.id, user.id)
                if success:
                    logger.info("✓ Individual mark as read succeeded")
                else:
                    logger.error("✗ Individual mark as read failed")
        
        logger.info("\n=== NOTIFICATION FIXES TEST COMPLETED ===")
        
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db_session.close()

if __name__ == "__main__":
    test_notification_fixes()