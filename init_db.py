from database import engine, Base
from models.intake_ticket import IntakeTicket, IntakeAttachment
from models.asset import Asset
from models.user import User
from models.company import Company
from models.accessory import Accessory
from models.accessory_transaction import AccessoryTransaction
from models.accessory_history import AccessoryHistory
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


def init_database():
    logger.info("Creating database tables...")
    Base.metadata.create_all(engine)
    logger.info("Database tables created successfully!")

if __name__ == "__main__":
    init_database() 