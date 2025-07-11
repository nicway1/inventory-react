from database import Base, engine
from models.asset import Asset
from models.accessory import Accessory
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


def clear_database():
    logger.info("Clearing database...")
    # Drop all tables
    Base.metadata.drop_all(bind=engine)
    logger.info("All tables dropped.")
    
    # Recreate all tables
    Base.metadata.create_all(bind=engine)
    logger.info("Tables recreated successfully.")

if __name__ == "__main__":
    clear_database() 