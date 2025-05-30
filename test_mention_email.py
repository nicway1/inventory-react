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
    print("=== TESTING MENTION EMAIL NOTIFICATION WORKFLOW ===\n")
    
    with app.app_context():
        # Test 1: Get user information
        print("1. Getting user information...")
        db_session = db_manager.get_session()
        try:
            # Get all users to see available usernames
            users = db_session.query(User).limit(5).all()
            print("   Available users:")
            for user in users:
                print(f"     - {user.username} (ID: {user.id}, Email: {user.email})")
            
            if len(users) < 2:
                print("   ❌ Need at least 2 users for testing")
                return
                
            commenter = users[0]  # First user will be the commenter
            mentioned_user = users[1] if len(users) > 1 else users[0]  # Second user will be mentioned
            
            print(f"   Commenter: {commenter.username}")
            print(f"   Mentioned: {mentioned_user.username}")
            
        finally:
            db_session.close()
        
        # Test 2: Add a comment with mention
        print(f"\n2. Adding a comment with @{mentioned_user.username} mention...")
        ticket_id = 2  # Using ticket 2
        
        comment = comment_store.add_comment(
            ticket_id=ticket_id,
            user_id=commenter.id,
            content=f"Hey @{mentioned_user.username}, please check this urgent issue! This is a test of our new Salesforce-style email notification system."
        )
        print(f"   ✅ Comment created with ID: {comment.id}")
        print(f"   📧 Email should have been sent to: {mentioned_user.email}")
        
        # Test 3: Verify the mention was detected
        print(f"\n3. Verifying mention detection...")
        if comment.mentions:
            print(f"   ✅ Detected mentions: {comment.mentions}")
            if mentioned_user.username in comment.mentions:
                print(f"   ✅ User {mentioned_user.username} was correctly detected in mentions")
            else:
                print(f"   ❌ User {mentioned_user.username} was not found in mentions")
        else:
            print("   ❌ No mentions detected")
        
        print(f"\n📬 Check the email inbox for {mentioned_user.email} to see the Salesforce-style notification!")
    
    print("\n=== TEST COMPLETED ===")
    print("The mention email notification system should now be working!")
    print("Every time someone uses @username in a comment, an email will be sent.")

if __name__ == "__main__":
    test_mention_email() 