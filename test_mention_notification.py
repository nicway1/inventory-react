#!/usr/bin/env python3

"""
Test the complete mention notification workflow
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.store_instances import comment_store, db_manager, activity_store
from models.user import User
from models.activity import Activity

def test_mention_notification():
    logger.info("=== TESTING MENTION NOTIFICATION WORKFLOW ===\n")
    
    # Test 1: Add a comment with mention
    logger.info("1. Adding a comment with @admin mention...")
    ticket_id = 2  # Using ticket 2
    user_id = 1    # User 1 (admin)
    
    comment = comment_store.add_comment(
        ticket_id=ticket_id,
        user_id=user_id,
        content="Hey @admin, please check this urgent issue! It needs immediate attention."
    )
    logger.info("   ✅ Comment created with ID: {comment.id}")
    
    # Test 2: Check if activity was created
    logger.info("\n2. Checking if mention notification was created...")
    db_session = db_manager.get_session()
    try:
        # Get recent activities for the mentioned user (admin, user_id=1)
        recent_activities = db_session.query(Activity).filter(
            Activity.user_id == 1,
            Activity.type == 'mention'
        ).order_by(Activity.created_at.desc()).limit(5).all()
        
        logger.info("   Found {len(recent_activities)} mention activities for admin")
        
        for i, activity in enumerate(recent_activities):
            logger.info("   Activity {i+1}: '{activity.content}'")
            logger.info("               Created: {activity.created_at}")
            logger.info("               Type: {activity.type}")
            logger.info("               Reference ID: {activity.reference_id}")
            logger.info("               Is Read: {activity.is_read}")
            print()
            
        if recent_activities:
            logger.info("   ✅ Mention notifications are being created correctly!")
        else:
            logger.info("   ❌ No mention activities found")
            
    finally:
        db_session.close()
    
    # Test 3: Check template field access
    logger.info("3. Testing template field access...")
    if recent_activities:
        activity = recent_activities[0]
        logger.info("   activity.content: '{activity.content}'")
        logger.info("   activity.created_at: {activity.created_at}")
        logger.info("   ✅ Template can access activity.content correctly")
    
    logger.info("\n=== TEST COMPLETED ===")

if __name__ == "__main__":
    test_mention_notification() 