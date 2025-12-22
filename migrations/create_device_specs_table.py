"""
Migration: Create DeviceSpec table

Run this script to create the device_specs table for the MacBook Specs Collector feature.
Usage on PythonAnywhere: python3 migrations/create_device_specs_table.py
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_db, engine
from models.base import Base

# Import the model so it registers with Base.metadata
from models.device_spec import DeviceSpec


def create_tables():
    """Create the DeviceSpec table"""
    print("Creating Device Specs table...")

    # Create only the new table (won't affect existing tables)
    DeviceSpec.__table__.create(bind=engine, checkfirst=True)

    print("Done! Table created:")
    print("  - device_specs")
    print("")
    print("The MacBook Specs Collector is now ready to use.")
    print("Users can run: curl -sL https://inventory.truelog.com.sg/specs | bash")


if __name__ == '__main__':
    create_tables()
