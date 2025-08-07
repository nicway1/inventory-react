#!/usr/bin/env python3

import logging
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.db_manager import DatabaseManager
from utils.comment_store import CommentStore
from utils.activity_store import ActivityStore
from utils.user_store import UserStore
from utils.ticket_store import TicketStore
from models.user import User
from models.ticket import Ticket

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_real_mention_workflow():
    logger.info("=== TESTING REAL @MENTION WORKFLOW ===\n")
    
    # Initialize stores (same as store_instances.py)
    db_manager = DatabaseManager()
    user_store = UserStore()
    activity_store = ActivityStore()
    ticket_store = TicketStore()
    comment_store = CommentStore(user_store, activity_store, ticket_store)
    
    try:
        db_session = db_manager.get_session()
        
        # Get two different users
        users = db_session.query(User).limit(2).all()
        if len(users) < 2:
            logger.error("Need at least 2 users for testing")
            return
        
        commenter = users[0]  # User who writes the comment
        mentioned_user = users[1]  # User who gets mentioned
        
        # Get a test ticket
        ticket = db_session.query(Ticket).first()
        if not ticket:
            logger.error("Need at least 1 ticket for testing")
            return
        
        logger.info(f"Testing scenario:")
        logger.info(f"  👤 Commenter: {commenter.username} (ID: {commenter.id})")
        logger.info(f"  🎯 Mentioned User: {mentioned_user.username} (ID: {mentioned_user.id})")
        logger.info(f"  🎫 Ticket: #{ticket.display_id} (ID: {ticket.id})")
        
        # Test: Commenter mentions the other user
        logger.info(f"\n📝 {commenter.username} is writing a comment mentioning @{mentioned_user.username}...")
        
        comment_content = f"Hey @{mentioned_user.username}, can you help with this issue? It's urgent and needs your expertise!"
        
        # This simulates what happens when someone posts a comment with @mention
        comment = comment_store.add_comment(
            ticket_id=ticket.id,
            user_id=commenter.id,  # The person writing the comment
            content=comment_content
        )
        
        if comment:
            logger.info(f"✅ Comment created successfully")
            logger.info(f"   Comment ID: {comment.id}")
            logger.info(f"   Content: {comment.content}")
            logger.info(f"   Mentions detected: {comment.mentions}")
            
            # Check if notification was created for the mentioned user
            logger.info(f"\n🔔 Checking if {mentioned_user.username} received a notification...")
            
            from utils.notification_service import NotificationService
            notification_service = NotificationService(db_manager)
            
            # Get recent notifications for the mentioned user
            notifications = notification_service.get_user_notifications(mentioned_user.id, limit=3)
            
            # Look for the most recent notification
            if notifications:
                latest = notifications[0]
                logger.info(f"✅ Latest notification for {mentioned_user.username}:")
                logger.info(f"   Title: {latest.title}")
                logger.info(f"   Message: {latest.message}")
                logger.info(f"   Created: {latest.created_at}")
                logger.info(f"   Is Read: {latest.is_read}")
                
                # Check if it's about this mention
                if commenter.username in latest.message:
                    logger.info(f"🎉 SUCCESS! {mentioned_user.username} received notification about the mention!")
                else:
                    logger.warning(f"⚠️  Notification exists but doesn't seem to be about this mention")
            else:
                logger.error(f"❌ No notifications found for {mentioned_user.username}")
        else:
            logger.error("❌ Failed to create comment")
        
        logger.info("\n=== REAL @MENTION WORKFLOW TEST COMPLETED ===")
        
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db_session.close()

if __name__ == "__main__":
    test_real_mention_workflow()