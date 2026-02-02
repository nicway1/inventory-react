#!/usr/bin/env python3
"""
Migration to create tracking_refresh_logs table.
Works for both SQLite and MySQL.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, Base
from models.tracking_refresh_log import TrackingRefreshLog
from sqlalchemy import inspect

def run_migration():
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    if 'tracking_refresh_logs' in existing_tables:
        print("Table 'tracking_refresh_logs' already exists. Skipping.")
        return

    print("Creating 'tracking_refresh_logs' table...")
    TrackingRefreshLog.__table__.create(engine)
    print("Table 'tracking_refresh_logs' created successfully!")

if __name__ == '__main__':
    run_migration()
