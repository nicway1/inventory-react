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

def test_notification_system():
    logger.info("=== TESTING NOTIFICATION SYSTEM ===\n")
    
    # Initialize database manager
    db_manager = DatabaseManager()
    notification_service = NotificationService(db_manager)
    
    try:
        db_session = db_manager.get_session()
        
        # Get test users
        users = db_session.query(User).limit(2).all()
        if len(users) < 2:
            logger.error("Need at least 2 users in database for testing")
            return
        
        commenter = users[0]
        mentioned_user = users[1]
        
        # Get a test ticket
        ticket = db_session.query(Ticket).first()
        if not ticket:
            logger.error("Need at least 1 ticket in database for testing")
            return
        
        logger.info(f"Testing with:")
        logger.info(f"  Commenter: {commenter.username} (ID: {commenter.id})")
        logger.info(f"  Mentioned User: {mentioned_user.username} (ID: {mentioned_user.id})")
        logger.info(f"  Ticket: #{ticket.display_id} (ID: {ticket.id})")
        
        # Test creating a mention notification
        logger.info("\n1. Creating mention notification...")
        success = notification_service.create_mention_notification(
            mentioned_user_id=mentioned_user.id,
            commenter_user_id=commenter.id,
            ticket_id=ticket.id,
            comment_content=f"Hey @{mentioned_user.username}, can you take a look at this issue?"
        )
        
        if success:
            logger.info("✓ Mention notification created successfully")
        else:
            logger.error("✗ Failed to create mention notification")
            return
        
        # Test getting notifications
        logger.info("\n2. Getting user notifications...")
        notifications = notification_service.get_user_notifications(mentioned_user.id)
        logger.info(f"✓ Found {len(notifications)} notifications for {mentioned_user.username}")
        
        if notifications:
            latest = notifications[0]
            logger.info(f"  Latest: {latest.title}")
            logger.info(f"  Message: {latest.message}")
            logger.info(f"  Read: {latest.is_read}")
        
        # Test getting unread count
        logger.info("\n3. Getting unread count...")
        unread_count = notification_service.get_unread_count(mentioned_user.id)
        logger.info(f"✓ Unread count: {unread_count}")
        
        # Test marking as read
        if notifications:
            logger.info("\n4. Marking notification as read...")
            success = notification_service.mark_notification_as_read(
                notifications[0].id, 
                mentioned_user.id
            )
            if success:
                logger.info("✓ Notification marked as read")
                
                # Check unread count again
                new_count = notification_service.get_unread_count(mentioned_user.id)
                logger.info(f"✓ New unread count: {new_count}")
            else:
                logger.error("✗ Failed to mark notification as read")
        
        logger.info("\n=== NOTIFICATION SYSTEM TEST COMPLETED ===")
        
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db_session.close()

if __name__ == "__main__":
    test_notification_system()