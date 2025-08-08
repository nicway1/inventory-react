#!/usr/bin/env python3

import logging
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.db_manager import DatabaseManager
from models.comment import Comment
from models.user import User
from models.ticket import Ticket

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_comment_creation():
    logger.info("=== TESTING COMMENT CREATION FIX ===\n")
    
    # Initialize database manager
    db_manager = DatabaseManager()
    
    try:
        db_session = db_manager.get_session()
        
        # Get a test user and ticket
        user = db_session.query(User).first()
        ticket = db_session.query(Ticket).first()
        
        if not user or not ticket:
            logger.error("Need at least 1 user and 1 ticket for testing")
            return
        
        logger.info(f"Testing with user: {user.username} (ID: {user.id})")
        logger.info(f"Testing with ticket: #{ticket.display_id} (ID: {ticket.id})")
        
        # Test creating a comment using the fixed constructor
        logger.info("\n1. Testing Comment creation with proper constructor...")
        
        comment = Comment(
            ticket_id=ticket.id,
            user_id=user.id,
            content="Test comment for queue change functionality"
        )
        
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)
        
        logger.info(f"✅ Comment created successfully!")
        logger.info(f"   Comment ID: {comment.id}")
        logger.info(f"   Content: {comment.content}")
        logger.info(f"   Created at: {comment.created_at}")
        
        # Test that the comment is properly linked
        logger.info(f"   Linked to ticket: #{comment.ticket.display_id}")
        logger.info(f"   Created by user: {comment.user.username}")
        
        logger.info("\n✅ Comment creation test passed! Queue change should now work.")
        
    except Exception as e:
        logger.error(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db_session.close()

if __name__ == "__main__":
    test_comment_creation()