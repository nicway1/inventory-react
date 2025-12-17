"""
Migration: Create ImportSession and UserImportPermission tables

Run this script to create the new tables for the Import Manager feature.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_db, engine
from models.base import Base

# Import the models so they register with Base.metadata
from models.import_session import ImportSession
from models.user_import_permission import UserImportPermission


def create_tables():
    """Create the ImportSession and UserImportPermission tables"""
    print("Creating Import Manager tables...")

    # Create only the new tables (won't affect existing tables)
    ImportSession.__table__.create(bind=engine, checkfirst=True)
    UserImportPermission.__table__.create(bind=engine, checkfirst=True)

    print("Done! Tables created:")
    print("  - import_sessions")
    print("  - user_import_permissions")


if __name__ == '__main__':
    create_tables()
