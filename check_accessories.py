import sys
import os
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models.accessory import Accessory

def check_accessories():
    session = SessionLocal()
    try:
        # Query all accessories
        accessories = session.query(Accessory).all()
        
        if not accessories:
            logger.info("No accessories found in the database!")
            return
        
        logger.info("\nAccessories in the database:")
        logger.info("-" * 80)
        for accessory in accessories:
            logger.info("Name: {accessory.name}")
            logger.info("Category: {accessory.category}")
            logger.info("Manufacturer: {accessory.manufacturer}")
            logger.info("Model: {accessory.model_no}")
            logger.info("Total Quantity: {accessory.total_quantity}")
            logger.info("Available Quantity: {accessory.available_quantity}")
            logger.info("Status: {accessory.status}")
            logger.info("Notes: {accessory.notes}")
            logger.info("-" * 80)
            
    except Exception as e:
        logger.info("Error checking accessories: {str(e)}")
    finally:
        session.close()

if __name__ == '__main__':
    check_accessories() 