#!/usr/bin/env python3

"""
Test script for group mention functionality
"""

from database import SessionLocal
from models.group import Group
from models.group_membership import GroupMembership
from models.user import User
from models.comment import Comment
from models.ticket import Ticket
from utils.comment_store import CommentStore
from utils.activity_store import ActivityStore
from utils.ticket_store import TicketStore
from utils.db_manager import DatabaseManager
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_group_functionality():
    """Test the complete group functionality"""
    db_session = SessionLocal()
    db_manager = DatabaseManager()
    
    try:
        logger.info("Starting group mention functionality test...")
        
        # 1. Create test users
        logger.info("Creating test users...")
        users = []
        for i in range(3):
            username = f"testuser{i+1}"
            user = db_session.query(User).filter(User.username == username).first()
            if not user:
                user = User(
                    username=username,
                    email=f"test{i+1}@example.com",
                    user_type='SUPERVISOR'
                )
                db_session.add(user)
            users.append(user)
        
        db_session.commit()
        logger.info(f"Created/found {len(users)} test users")
        
        # 2. Create a test group
        logger.info("Creating test group...")
        group_name = "developers"
        group = db_session.query(Group).filter(Group.name == group_name).first()
        if not group:
            group = Group(
                name=group_name,
                description="Test developers group",
                created_by_id=users[0].id
            )
            db_session.add(group)
            db_session.commit()
        
        # 3. Add members to the group
        logger.info("Adding members to group...")
        for user in users[1:]:  # Add users 2 and 3 to the group
            if not group.has_member(user.id):
                group.add_member(user.id, users[0].id)
        
        db_session.commit()
        logger.info(f"Group @{group_name} now has {group.member_count} members")
        
        # 4. Test group mention detection in comments
        logger.info("Testing group mention detection...")
        
        # Create a test comment with group mention
        test_content = f"Hello @{group_name}, please review this issue. Also @{users[0].username} needs to check it."
        
        # Create a mock comment to test mention detection
        class MockComment:
            def __init__(self, content):
                self.content = content
                self.ticket_id = 1
                self.user_id = users[0].id
        
        comment = MockComment(test_content)
        
        # Check if mentions are detected correctly
        from models.comment import Comment
        real_comment = Comment(content=test_content)
        
        all_mentions = real_comment.mentions
        user_mentions = real_comment.user_mentions
        group_mentions = real_comment.group_mentions
        
        logger.info(f"All mentions detected: {all_mentions}")
        logger.info(f"User mentions: {user_mentions}")
        logger.info(f"Group mentions: {group_mentions}")
        
        # Verify the detection works
        assert group_name in all_mentions, f"Group {group_name} not detected in mentions"
        assert group_name in group_mentions, f"Group {group_name} not detected in group mentions"
        assert users[0].username in user_mentions, f"User {users[0].username} not detected in user mentions"
        
        logger.info("✓ Group mention detection working correctly!")
        
        # 5. Test group properties
        logger.info("Testing group properties...")
        logger.info(f"Group members: {[member.username for member in group.members]}")
        logger.info(f"Users[1] groups: {users[1].get_group_names()}")
        logger.info(f"Users[1] is in {group_name}: {users[1].is_in_group(group_name)}")
        
        # 6. Clean up (optional)
        logger.info("Test completed successfully!")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        db_session.close()

if __name__ == "__main__":
    success = test_group_functionality()
    if success:
        logger.info("🎉 All tests passed!")
    else:
        logger.error("❌ Tests failed!")
    exit(0 if success else 1)