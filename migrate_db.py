from sqlalchemy import create_engine, inspect
from models import Base, AccessoryTransaction
from utils.db_manager import DatabaseManager
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


def migrate_database():
    try:
        # Get database URL from DatabaseManager
        db_manager = DatabaseManager()
        engine = db_manager.engine
        
        # Create an inspector
        inspector = inspect(engine)
        
        # Check if the table already exists
        if 'accessory_transactions' not in inspector.get_table_names():
            # Create the new table only if it doesn't exist
            AccessoryTransaction.__table__.create(engine)
            logger.info("Successfully created accessory_transactions table")
        else:
            logger.info("Table accessory_transactions already exists, skipping creation")
        
        # Add any other migration steps here if needed
        
        return True
    except Exception as e:
        logger.info("Error during migration: {str(e)}")
        return False

if __name__ == "__main__":
    migrate_database() 