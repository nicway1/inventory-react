#!/usr/bin/env python3

import logging
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.db_manager import DatabaseManager
from models.user import User
from sqlalchemy import or_

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_user_search():
    logger.info("=== TESTING USER SEARCH FOR @MENTION ===\n")
    
    # Initialize database manager
    db_manager = DatabaseManager()
    
    try:
        db_session = db_manager.get_session()
        
        # Test search functionality
        test_queries = ['admin', 'ronnie', 'truelog', 'a']
        
        for query in test_queries:
            logger.info(f"Searching for: '{query}'")
            
            # Search users by username or email (same logic as the API endpoint)
            users = db_session.query(User).filter(
                or_(
                    User.username.ilike(f'%{query}%'),
                    User.email.ilike(f'%{query}%')
                )
            ).limit(10).all()
            
            logger.info(f"  Found {len(users)} users:")
            for user in users:
                display_name = f"{user.username} ({user.email})" if user.email != user.username else user.username
                logger.info(f"    - {display_name}")
            
            logger.info("")
        
        logger.info("=== USER SEARCH TEST COMPLETED ===")
        
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db_session.close()

if __name__ == "__main__":
    test_user_search()