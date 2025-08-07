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
from models.comment import Comment

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_full_mention_workflow():
    logger.info("=== TESTING FULL MENTION WORKFLOW ===\n")
    
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
        
        # Test 1: Create a comment with mention (simulating what happens in the UI)
        logger.info("\n1. Creating comment with @mention...")
        comment_content = f"Hey @{mentioned_user.username}, can you help with this? This is urgent!"
        
        # Create comment directly in database (simulating comment_store.add_comment)
        comment = Comment(
            ticket_id=ticket.id,
            user_id=commenter.id,
            content=comment_content
        )
        
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)
        
        logger.info(f"✓ Comment created with ID: {comment.id}")
        logger.info(f"  Content: {comment.content}")
        logger.info(f"  Mentions extracted: {comment.mentions}")
        logger.info(f"  Formatted content: {comment.formatted_content}")
        
        # Test 2: Manually trigger notification (simulating what _notify_mentions does)
        logger.info("\n2. Creating notification for mention...")
        success = notification_service.create_mention_notification(
            mentioned_user_id=mentioned_user.id,
            commenter_user_id=commenter.id,
            ticket_id=ticket.id,
            comment_content=comment.content
        )
        
        if success:
            logger.info("✓ Notification created successfully")
        else:
            logger.error("✗ Failed to create notification")
            return
        
        # Test 3: Simulate API calls that the frontend would make
        logger.info("\n3. Testing notification API endpoints...")
        
        # Get unread count
        unread_count = notification_service.get_unread_count(mentioned_user.id)
        logger.info(f"✓ Unread count: {unread_count}")
        
        # Get notifications
        notifications = notification_service.get_user_notifications(mentioned_user.id, limit=5)
        logger.info(f"✓ Retrieved {len(notifications)} notifications")
        
        if notifications:
            latest = notifications[0]
            logger.info(f"  Latest notification:")
            logger.info(f"    Title: {latest.title}")
            logger.info(f"    Message: {latest.message}")
            logger.info(f"    Is Read: {latest.is_read}")
            logger.info(f"    Created: {latest.created_at}")
            
            # Test marking as read
            logger.info("\n4. Marking notification as read...")
            success = notification_service.mark_notification_as_read(latest.id, mentioned_user.id)
            if success:
                logger.info("✓ Notification marked as read")
                
                # Check new unread count
                new_count = notification_service.get_unread_count(mentioned_user.id)
                logger.info(f"✓ New unread count: {new_count}")
            else:
                logger.error("✗ Failed to mark notification as read")
        
        # Test 4: Test HTML mention formatting
        logger.info("\n5. Testing HTML mention formatting...")
        html_content = f'This is a test with <span class="mention">@{mentioned_user.username}</span> in HTML.'
        
        html_comment = Comment(
            ticket_id=ticket.id,
            user_id=commenter.id,
            content=html_content
        )
        
        logger.info(f"HTML comment mentions: {html_comment.mentions}")
        logger.info(f"HTML formatted content: {html_comment.formatted_content}")
        
        logger.info("\n=== FULL MENTION WORKFLOW TEST COMPLETED SUCCESSFULLY ===")
        
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db_session.close()

if __name__ == "__main__":
    test_full_mention_workflow()