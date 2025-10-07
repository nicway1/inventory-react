#!/usr/bin/env python3
"""
Script to assign DEVELOPER role to the admin user
"""

from database import engine
from sqlalchemy.orm import Session
from models.user import User
from models.enums import UserType
from models.permission import Permission
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def assign_developer_role():
    """Assign DEVELOPER role to admin user"""
    session = Session(engine)

    try:
        # Find the admin user
        admin_user = session.query(User).filter_by(username='admin').first()

        if not admin_user:
            logger.error("Admin user not found!")
            return False

        logger.info(f"Found admin user (ID: {admin_user.id})")
        logger.info(f"Current user_type: {admin_user.user_type}")

        # Update user_type to DEVELOPER
        admin_user.user_type = UserType.DEVELOPER

        # Check if DEVELOPER permission record exists, create if not
        dev_permission = session.query(Permission).filter_by(user_type=UserType.DEVELOPER).first()

        if not dev_permission:
            logger.info("Creating DEVELOPER permission record...")
            default_perms = Permission.get_default_permissions(UserType.DEVELOPER)
            dev_permission = Permission(user_type=UserType.DEVELOPER, **default_perms)
            session.add(dev_permission)
        else:
            logger.info("DEVELOPER permission record already exists")

        session.commit()
        logger.info(f"Successfully updated admin user to DEVELOPER role")
        logger.info(f"New user_type: {admin_user.user_type}")

        return True

    except Exception as e:
        session.rollback()
        logger.error(f"Error assigning developer role: {str(e)}")
        return False
    finally:
        session.close()

if __name__ == '__main__':
    logger.info("Starting DEVELOPER role assignment...")
    success = assign_developer_role()
    if success:
        logger.info("DEVELOPER role assignment completed successfully!")
    else:
        logger.error("DEVELOPER role assignment failed!")
