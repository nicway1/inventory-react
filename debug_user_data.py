#!/usr/bin/env python3

"""
Debug script to check user data and group membership
"""

from database import SessionLocal
from models.user import User
from models.group import Group
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_user_data():
    """Debug user data to find the issue"""
    db_session = SessionLocal()
    
    try:
        logger.info("Checking user data...")
        
        # Get all users
        users = db_session.query(User).all()
        logger.info(f"Found {len(users)} users in database:")
        
        for user in users[:10]:  # Show first 10 users
            logger.info(f"User ID: {user.id}, Username: {user.username}, Email: {user.email}")
        
        # Check for users where username looks like an email
        email_users = db_session.query(User).filter(User.username.like('%@%')).all()
        if email_users:
            logger.warning(f"Found {len(email_users)} users with email addresses as usernames:")
            for user in email_users[:5]:
                logger.warning(f"  User ID: {user.id}, Username: {user.username}, Email: {user.email}")
        
        # Check groups and their members
        groups = db_session.query(Group).all()
        logger.info(f"Found {len(groups)} groups:")
        
        for group in groups:
            logger.info(f"Group: {group.name} (ID: {group.id})")
            logger.info(f"  Members ({group.member_count}):")
            for member in group.members:
                logger.info(f"    - ID: {member.id}, Username: {member.username}, Email: {member.email}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error debugging user data: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        db_session.close()

if __name__ == "__main__":
    debug_user_data()