"""
Migration: Create SLA and Holiday tables (SQLite)

Run this script to create the sla_configs and queue_holidays tables.
Usage: python3 migrations/sla_tables_sqlite.py
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_db, engine
from models.base import Base

# Import the models so they register with Base.metadata
from models.sla_config import SLAConfig
from models.queue_holiday import QueueHoliday


def create_tables():
    """Create the SLA-related tables"""
    print("Creating SLA tables...")

    # Create only the new tables (won't affect existing tables)
    SLAConfig.__table__.create(bind=engine, checkfirst=True)
    QueueHoliday.__table__.create(bind=engine, checkfirst=True)

    print("Done! Tables created:")
    print("  - sla_configs")
    print("  - queue_holidays")
    print("")
    print("Next steps:")
    print("1. Restart the Flask application")
    print("2. Add the Case Manager SLA widget to your dashboard")
    print("3. Configure SLA rules at /sla/manage")


if __name__ == '__main__':
    create_tables()
