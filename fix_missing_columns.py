from sqlalchemy import create_engine
from database import engine
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


def add_missing_columns():
    with engine.connect() as connection:
        # Add Asset Intake specific fields
        try:
            connection.execute('ALTER TABLE tickets ADD COLUMN packing_list_path VARCHAR(500)')
            logger.info("Added packing_list_path column")
        except Exception as e:
            logger.info("packing_list_path column might already exist: {e}")
        
        try:
            connection.execute('ALTER TABLE tickets ADD COLUMN asset_csv_path VARCHAR(500)')
            logger.info("Added asset_csv_path column")
        except Exception as e:
            logger.info("asset_csv_path column might already exist: {e}")
        
        try:
            connection.execute('ALTER TABLE tickets ADD COLUMN notes VARCHAR(2000)')
            logger.info("Added notes column")
        except Exception as e:
            logger.info("notes column might already exist: {e}")

if __name__ == '__main__':
    logger.info("Adding missing columns to database...")
    add_missing_columns()
    logger.info("Column addition completed") 