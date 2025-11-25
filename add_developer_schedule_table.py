#!/usr/bin/env python3

"""
Migration script to add developer_schedules table
"""

from database import SessionLocal, engine
from models.developer_schedule import DeveloperSchedule
from models.base import Base
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_developer_schedule_table():
    """Create developer_schedules table"""
    try:
        logger.info("Creating developer_schedules table...")

        # Create the table
        DeveloperSchedule.__table__.create(engine, checkfirst=True)

        logger.info("Successfully created developer_schedules table")
        return True

    except Exception as e:
        logger.error(f"Error creating developer_schedules table: {e}")
        return False

def verify_table():
    """Verify that the table was created successfully"""
    try:
        db_session = SessionLocal()

        # Try to query the table
        schedules_count = db_session.query(DeveloperSchedule).count()

        logger.info(f"Developer schedules table: {schedules_count} records")

        db_session.close()
        return True

    except Exception as e:
        logger.error(f"Error verifying table: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting developer_schedules table migration...")

    # Create the table
    if create_developer_schedule_table():
        logger.info("Developer schedules table created successfully")

        # Verify the table
        if verify_table():
            logger.info("Table verified successfully")
        else:
            logger.error("Table verification failed")
    else:
        logger.error("Failed to create developer_schedules table")

    logger.info("Migration complete")
