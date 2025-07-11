#!/usr/bin/env python
# Diagnostic script for comments functionality

from utils.store_instances import comment_store, db_manager
from models.ticket import Ticket
from models.comment import Comment
import json
import os
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


def diagnose_comments():
    logger.info("\n=== COMMENTS DIAGNOSTIC ===\n")
    
    # Check if comments file exists
    comments_file = 'data/comments.json'
    logger.info("1. Checking if comments file exists: {os.path.exists(comments_file)}")
    
    # Check content of comments file
    if os.path.exists(comments_file):
        try:
            with open(comments_file, 'r') as f:
                comments_data = json.load(f)
                logger.info("2. Comments file contains {len(comments_data)} comments")
                if comments_data:
                    logger.info("   First comment: {comments_data[0]}")
        except Exception as e:
            logger.info("2. Error reading comments file: {e}")
    else:
        logger.info("2. Comments file does not exist")
    
    # Check comment_store
    logger.info("\n3. CommentStore contains {len(comment_store.comments)} comments")
    if comment_store.comments:
        logger.info("   First comment key: {list(comment_store.comments.keys())[0]}")
    
    # Check tickets in database
    db_session = db_manager.get_session()
    try:
        tickets = db_session.query(Ticket).all()
        logger.info("\n4. Database has {len(tickets)} tickets")
        
        if tickets:
            # Check first ticket
            ticket = tickets[0]
            logger.info("   First ticket ID: {ticket.id}")
            
            # Check comments in DB for first ticket
            db_comments = db_session.query(Comment).filter(Comment.ticket_id == ticket.id).all()
            logger.info("   Ticket {ticket.id} has {len(db_comments)} comments in the database")
            
            # Check relationship
            if hasattr(ticket, 'comments'):
                rel_comments = ticket.comments
                logger.info("   Ticket {ticket.id} has {len(rel_comments) if rel_comments else 0} comments via relationship")
            else:
                logger.info("   Ticket {ticket.id} does not have a 'comments' relationship attribute")
            
            # Check comments from store
            store_comments = comment_store.get_ticket_comments(ticket.id)
            logger.info("   Ticket {ticket.id} has {len(store_comments)} comments via comment_store")
    except Exception as e:
        logger.info("\nError checking database: {e}")
    finally:
        db_session.close()
    
    logger.info("\n=== END DIAGNOSTIC ===\n")

if __name__ == "__main__":
    diagnose_comments() 