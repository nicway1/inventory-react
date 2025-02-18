"""
This module initializes all models in the correct order to avoid circular imports.
"""

# Empty file to make the directory a Python package 

# Import all models to ensure proper SQLAlchemy model registration
from models.base import Base
from models.user import User, UserType, Country
from models.company import Company
from models.asset import Asset, AssetStatus
from models.accessory import Accessory
from models.customer_user import CustomerUser
from models.activity import Activity
from models.ticket import Ticket
from models.location import Location
from models.permission import Permission
from models.asset_history import AssetHistory
from models.accessory_history import AccessoryHistory

# This ensures all models are registered with SQLAlchemy
__all__ = [
    'Base',
    'User',
    'UserType',
    'Country',
    'Company',
    'Asset',
    'AssetStatus',
    'Accessory',
    'CustomerUser',
    'Activity',
    'Ticket',
    'Location',
    'Permission',
    'AssetHistory',
    'AccessoryHistory'
] 