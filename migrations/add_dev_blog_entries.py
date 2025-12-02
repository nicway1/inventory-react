#!/usr/bin/env python3
"""
Migration: Add dev_blog_entries table for git commit tracking

Run this migration to create the dev_blog_entries table:
    python migrations/add_dev_blog_entries.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, SessionLocal
from models.dev_blog_entry import DevBlogEntry
from models.base import Base
from sqlalchemy import inspect


def run_migration():
    """Create the dev_blog_entries table if it doesn't exist"""
    inspector = inspect(engine)

    if 'dev_blog_entries' not in inspector.get_table_names():
        print("Creating dev_blog_entries table...")
        DevBlogEntry.__table__.create(engine)
        print("Table created successfully!")
    else:
        print("Table dev_blog_entries already exists, skipping...")


if __name__ == '__main__':
    run_migration()
