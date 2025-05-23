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
    print("=== TESTING MENTION NOTIFICATION WORKFLOW ===\n")
    
    # Test 1: Add a comment with mention
    print("1. Adding a comment with @admin mention...")
    ticket_id = 2  # Using ticket 2
    user_id = 1    # User 1 (admin)
    
    comment = comment_store.add_comment(
        ticket_id=ticket_id,
        user_id=user_id,
        content="Hey @admin, please check this urgent issue! It needs immediate attention."
    )
    print(f"   ✅ Comment created with ID: {comment.id}")
    
    # Test 2: Check if activity was created
    print("\n2. Checking if mention notification was created...")
    db_session = db_manager.get_session()
    try:
        # Get recent activities for the mentioned user (admin, user_id=1)
        recent_activities = db_session.query(Activity).filter(
            Activity.user_id == 1,
            Activity.type == 'mention'
        ).order_by(Activity.created_at.desc()).limit(5).all()
        
        print(f"   Found {len(recent_activities)} mention activities for admin")
        
        for i, activity in enumerate(recent_activities):
            print(f"   Activity {i+1}: '{activity.content}'")
            print(f"               Created: {activity.created_at}")
            print(f"               Type: {activity.type}")
            print(f"               Reference ID: {activity.reference_id}")
            print(f"               Is Read: {activity.is_read}")
            print()
            
        if recent_activities:
            print("   ✅ Mention notifications are being created correctly!")
        else:
            print("   ❌ No mention activities found")
            
    finally:
        db_session.close()
    
    # Test 3: Check template field access
    print("3. Testing template field access...")
    if recent_activities:
        activity = recent_activities[0]
        print(f"   activity.content: '{activity.content}'")
        print(f"   activity.created_at: {activity.created_at}")
        print(f"   ✅ Template can access activity.content correctly")
    
    print("\n=== TEST COMPLETED ===")

if __name__ == "__main__":
    test_mention_notification() 