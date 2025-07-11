from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Text
from database import Base, engine
from models.ticket import Ticket
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


def update_schema():
    # Add new columns to the tickets table
    with engine.connect() as connection:
        try:
            # Add shipping_address column
            connection.execute('ALTER TABLE tickets ADD COLUMN shipping_address TEXT')
            logger.info("Added shipping_address column")
        except Exception as e:
            logger.info("shipping_address column might already exist: {e}")

        try:
            # Add shipping_tracking column
            connection.execute('ALTER TABLE tickets ADD COLUMN shipping_tracking TEXT')
            logger.info("Added shipping_tracking column")
        except Exception as e:
            logger.info("shipping_tracking column might already exist: {e}")

        try:
            # Add customer_id column
            connection.execute('ALTER TABLE tickets ADD COLUMN customer_id INTEGER REFERENCES customer_users(id)')
            logger.info("Added customer_id column")
        except Exception as e:
            logger.info("customer_id column might already exist: {e}")

        try:
            # Add shipping_status column
            connection.execute('ALTER TABLE tickets ADD COLUMN shipping_status VARCHAR(20)')
            logger.info("Added shipping_status column")
        except Exception as e:
            logger.info("shipping_status column might already exist: {e}")

        try:
            # Add return_status column
            connection.execute('ALTER TABLE tickets ADD COLUMN return_status VARCHAR(20)')
            logger.info("Added return_status column")
        except Exception as e:
            logger.info("return_status column might already exist: {e}")

        try:
            # Add replacement_status column
            connection.execute('ALTER TABLE tickets ADD COLUMN replacement_status VARCHAR(20)')
            logger.info("Added replacement_status column")
        except Exception as e:
            logger.info("replacement_status column might already exist: {e}")

        try:
            # Add shipping_carrier column
            connection.execute('ALTER TABLE tickets ADD COLUMN shipping_carrier VARCHAR(50) DEFAULT \'singpost\'')
            logger.info("Added shipping_carrier column")
        except Exception as e:
            logger.info("shipping_carrier column might already exist: {e}")

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
    logger.info("Updating database schema...")
    update_schema()
    logger.info("Schema update completed") 