#!/usr/bin/env python3

"""
Test script to verify member removal functionality
"""

from database import SessionLocal
from models.user import User
from models.group import Group
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_member_removal():
    """Test member removal functionality"""
    db_session = SessionLocal()
    
    try:
        # Find user 4 (molly.durham@firstbase.com)
        user = db_session.query(User).filter(User.id == 4).first()
        if not user:
            logger.error("User 4 not found")
            return False
            
        logger.info(f"Testing with user: {user.username} (ID: {user.id})")
        
        # Find the group this user is actually in
        user_groups = user.active_groups
        logger.info(f"User is in {len(user_groups)} groups: {[g.name for g in user_groups]}")
        
        if not user_groups:
            logger.info("User is not in any groups")
            return True
            
        # Test removal from the first group the user is in
        group = user_groups[0]
        logger.info(f"Testing removal from group: {group.name} (ID: {group.id})")
        
        # Check if user is actually a member before removal
        is_member_before = group.has_member(user.id)
        logger.info(f"User is member before removal: {is_member_before}")
        
        if not is_member_before:
            logger.warning("User is not a member of this group!")
            return False
            
        # Attempt removal
        success = group.remove_member(user.id)
        logger.info(f"Removal success: {success}")
        
        if success:
            db_session.commit()
            
            # Check if user is still a member after removal
            is_member_after = group.has_member(user.id)
            logger.info(f"User is member after removal: {is_member_after}")
            
            if is_member_after:
                logger.error("User is still a member after removal!")
                return False
            else:
                logger.info("✅ Member removal successful!")
                
                # Add the user back for future tests
                group.add_member(user.id, 1)  # Add back with admin as the adder
                db_session.commit()
                logger.info("User added back to group for future tests")
                
                return True
        else:
            logger.error("❌ Member removal failed!")
            return False
        
    except Exception as e:
        logger.error(f"Error testing member removal: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        db_session.close()

if __name__ == "__main__":
    success = test_member_removal()
    if success:
        logger.info("🎉 Test passed!")
    else:
        logger.error("❌ Test failed!")
    exit(0 if success else 1)