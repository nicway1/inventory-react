#!/usr/bin/env python3

"""
Test script to verify comments functionality after the fix
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.store_instances import comment_store, db_manager
from models.ticket import Ticket
from models.comment import Comment
from sqlalchemy.orm import joinedload

def test_comments():
    logger.info("=== TESTING COMMENTS FUNCTIONALITY ===\n")
    
    # Get a database session
    db_session = db_manager.get_session()
    try:
        # Get first ticket
        tickets = db_session.query(Ticket).limit(1).all()
        if not tickets:
            logger.info("❌ No tickets found in database")
            return
            
        ticket = tickets[0]
        ticket_id = ticket.id
        logger.info("Testing with ticket ID: {ticket_id}")
        
        # 1. Check comments from comment_store (JSON file)
        comments_from_store = comment_store.get_ticket_comments(ticket_id)
        logger.info("\n1. Comments from comment_store: {len(comments_from_store)}")
        for i, comment in enumerate(comments_from_store):
            logger.info("   Comment {i+1}: ID={comment.id}, Content='{comment.content[:50]}...'")
        
        # 2. Check comments from database relationship  
        ticket_with_comments = db_session.query(Ticket).options(
            joinedload(Ticket.comments).joinedload(Comment.user)
        ).get(ticket_id)
        
        db_comments = ticket_with_comments.comments if ticket_with_comments.comments else []
        logger.info("\n2. Comments from database: {len(db_comments)}")
        for i, comment in enumerate(db_comments):
            logger.info("   Comment {i+1}: ID={comment.id}, Content='{comment.content[:50]}...'")
        
        # 3. Test adding a comment
        logger.info("\n3. Adding a test comment...")
        test_comment = comment_store.add_comment(
            ticket_id=ticket_id,
            user_id=1,  # Assuming user ID 1 exists
            content="Test comment for functionality check @admin"
        )
        logger.info("   Added comment ID: {test_comment.id}")
        
        # 4. Check comments again
        comments_after = comment_store.get_ticket_comments(ticket_id)
        logger.info("\n4. Comments after adding: {len(comments_after)}")
        for i, comment in enumerate(comments_after):
            logger.info("   Comment {i+1}: ID={comment.id}, Content='{comment.content[:50]}...'")
            
        logger.info("\n✅ Comments functionality test completed!")
        logger.info("   - Comment store has {len(comments_after)} comments for ticket {ticket_id}")
        logger.info("   - Database has {len(db_comments)} comments for ticket {ticket_id}")
        
    except Exception as e:
        logger.info("❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db_session.close()

if __name__ == "__main__":
    test_comments() 