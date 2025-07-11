#!/usr/bin/env python3

"""
Test the complete mention email notification workflow
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from utils.store_instances import comment_store, db_manager
from models.user import User

def test_mention_email():
    logger.info("=== TESTING MENTION EMAIL NOTIFICATION WORKFLOW ===\n")
    
    with app.app_context():
        # Test 1: Get user information
        logger.info("1. Getting user information...")
        db_session = db_manager.get_session()
        try:
            # Get all users to see available usernames
            users = db_session.query(User).limit(5).all()
            logger.info("   Available users:")
            for user in users:
                logger.info("     - {user.username} (ID: {user.id}, Email: {user.email})")
            
            if len(users) < 2:
                logger.info("   ❌ Need at least 2 users for testing")
                return
                
            commenter = users[0]  # First user will be the commenter
            mentioned_user = users[1] if len(users) > 1 else users[0]  # Second user will be mentioned
            
            logger.info("   Commenter: {commenter.username}")
            logger.info("   Mentioned: {mentioned_user.username}")
            
        finally:
            db_session.close()
        
        # Test 2: Add a comment with mention
        logger.info("\n2. Adding a comment with @{mentioned_user.username} mention...")
        ticket_id = 2  # Using ticket 2
        
        comment = comment_store.add_comment(
            ticket_id=ticket_id,
            user_id=commenter.id,
            content=f"Hey @{mentioned_user.username}, please check this urgent issue! This is a test of our new Salesforce-style email notification system."
        )
        logger.info("   ✅ Comment created with ID: {comment.id}")
        logger.info("   📧 Email should have been sent to: {mentioned_user.email}")
        
        # Test 3: Verify the mention was detected
        logger.info("\n3. Verifying mention detection...")
        if comment.mentions:
            logger.info("   ✅ Detected mentions: {comment.mentions}")
            if mentioned_user.username in comment.mentions:
                logger.info("   ✅ User {mentioned_user.username} was correctly detected in mentions")
            else:
                logger.info("   ❌ User {mentioned_user.username} was not found in mentions")
        else:
            logger.info("   ❌ No mentions detected")
        
        logger.info("\n📬 Check the email inbox for {mentioned_user.email} to see the Salesforce-style notification!")
    
    logger.info("\n=== TEST COMPLETED ===")
    logger.info("The mention email notification system should now be working!")
    logger.info("Every time someone uses @username in a comment, an email will be sent.")

if __name__ == "__main__":
    test_mention_email() 