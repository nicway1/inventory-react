#!/usr/bin/env python3

import logging
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.db_manager import DatabaseManager
from utils.comment_store import CommentStore
from utils.activity_store import ActivityStore
from models.user import User
from models.ticket import Ticket

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_comment_mentions():
    logger.info("=== TESTING COMMENT MENTIONS ===\n")
    
    # Initialize stores (using the same pattern as store_instances.py)
    from utils.user_store import UserStore
    from utils.ticket_store import TicketStore
    
    db_manager = DatabaseManager()
    user_store = UserStore()
    activity_store = ActivityStore()
    ticket_store = TicketStore()
    comment_store = CommentStore(user_store, activity_store, ticket_store)
    
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
        
        # Test creating a comment with mention
        logger.info("\n1. Creating comment with @mention...")
        comment_content = f"Hey @{mentioned_user.username}, can you help with this ticket? This looks like something you've handled before."
        
        comment = comment_store.add_comment(
            ticket_id=ticket.id,
            user_id=commenter.id,
            content=comment_content
        )
        
        if comment:
            logger.info("✓ Comment created successfully")
            logger.info(f"  Comment ID: {comment.id}")
            logger.info(f"  Content: {comment.content}")
            logger.info(f"  Mentions found: {comment.mentions}")
        else:
            logger.error("✗ Failed to create comment")
            return
        
        # Check if notification was created
        logger.info("\n2. Checking if notification was created...")
        from utils.notification_service import NotificationService
        notification_service = NotificationService(db_manager)
        
        notifications = notification_service.get_user_notifications(mentioned_user.id, limit=1)
        if notifications:
            latest = notifications[0]
            logger.info("✓ Notification created successfully")
            logger.info(f"  Title: {latest.title}")
            logger.info(f"  Message: {latest.message}")
        else:
            logger.warning("⚠ No notification found (this might be expected if email sending failed)")
        
        # Test HTML mention formatting
        logger.info("\n3. Testing HTML mention formatting...")
        html_comment_content = f'This is a test with <span class="mention">@{mentioned_user.username}</span> in HTML format.'
        
        html_comment = comment_store.add_comment(
            ticket_id=ticket.id,
            user_id=commenter.id,
            content=html_comment_content
        )
        
        if html_comment:
            logger.info("✓ HTML comment created successfully")
            logger.info(f"  Mentions found: {html_comment.mentions}")
        
        logger.info("\n=== COMMENT MENTIONS TEST COMPLETED ===")
        
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db_session.close()

if __name__ == "__main__":
    test_comment_mentions()