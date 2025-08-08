#!/usr/bin/env python3

"""
Migration script to add groups and group_memberships tables
"""

from database import SessionLocal, engine
from models.group import Group
from models.group_membership import GroupMembership
from models.base import Base
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_groups_tables():
    """Create groups and group_memberships tables"""
    try:
        logger.info("Creating groups and group_memberships tables...")
        
        # Create the tables
        Group.__table__.create(engine, checkfirst=True)
        GroupMembership.__table__.create(engine, checkfirst=True)
        
        logger.info("Successfully created groups tables")
        return True
        
    except Exception as e:
        logger.error(f"Error creating groups tables: {e}")
        return False

def verify_tables():
    """Verify that the tables were created successfully"""
    try:
        db_session = SessionLocal()
        
        # Try to query both tables
        groups_count = db_session.query(Group).count()
        memberships_count = db_session.query(GroupMembership).count()
        
        logger.info(f"Groups table: {groups_count} records")
        logger.info(f"Group memberships table: {memberships_count} records")
        
        db_session.close()
        return True
        
    except Exception as e:
        logger.error(f"Error verifying tables: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting groups tables migration...")
    
    # Create the tables
    if create_groups_tables():
        logger.info("Groups tables created successfully")
        
        # Verify the tables
        if verify_tables():
            logger.info("Tables verified successfully")
        else:
            logger.error("Table verification failed")
    else:
        logger.error("Failed to create groups tables")
    
    logger.info("Migration complete")