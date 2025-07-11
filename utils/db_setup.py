import os
import sys
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


# Add the project root directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.base import Base

from utils.db_manager import Base, DatabaseManager
from models.user import User
from models.ticket import Ticket
from models.asset import Asset
from models.company import Company
from models.customer_user import CustomerUser
from models.queue import Queue
from models.accessory import Accessory
from models.comment import Comment
from models.ticket_attachment import TicketAttachment
from models.intake_ticket import IntakeTicket, IntakeAttachment

def setup_database(db_url="sqlite:///inventory.db"):
    """Create all database tables."""
    engine = create_engine(db_url)
    
    # Import all models to ensure they are registered with Base
    from models.user import User
    from models.ticket import Ticket
    from models.asset import Asset
    from models.company import Company
    from models.customer_user import CustomerUser
    from models.queue import Queue
    from models.accessory import Accessory
    from models.comment import Comment
    from models.ticket_attachment import TicketAttachment
    from models.intake_ticket import IntakeTicket, IntakeAttachment
    
    # Create all tables
    Base.metadata.create_all(engine)
    logger.info("Database tables created successfully!")

if __name__ == "__main__":
    setup_database() 