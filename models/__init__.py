# Empty file to make the directory a Python package 

# Import all models to ensure proper SQLAlchemy model registration
from models.base import Base
from models.user import User
from models.ticket import Ticket
from models.accessory import Accessory
from models.asset import Asset
from models.company import Company
from models.location import Location
from models.queue import Queue

# This ensures all models are registered with SQLAlchemy
__all__ = ['Base', 'User', 'Ticket', 'Accessory', 'Asset', 'Company', 'Location', 'Queue'] 