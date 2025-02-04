"""
This module initializes all models in the correct order to avoid circular imports.
"""

# Empty file to make the directory a Python package 

# Import all models to ensure proper SQLAlchemy model registration
from models.base import Base
from models.location import Location
from models.company import Company
from models.user import User
from models.asset import Asset
from models.accessory import Accessory
from models.ticket import Ticket
from models.activity import Activity
from models.comment import Comment
from models.queue import Queue
from models.shipment import Shipment

# This ensures all models are registered with SQLAlchemy
__all__ = [
    'Base',
    'Location',
    'Company',
    'User',
    'Asset',
    'Accessory',
    'Ticket',
    'Activity',
    'Comment',
    'Queue',
    'Shipment'
] 