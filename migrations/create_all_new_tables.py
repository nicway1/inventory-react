#!/usr/bin/env python3
"""
Migration: Create all new tables for recent features

This creates:
- dev_blog_entries
- weekly_meetings
- action_items
- action_item_comments
- user_mention_permissions
- Adds can_export_tickets column to permissions

Run: python migrations/create_all_new_tables.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, SessionLocal
from sqlalchemy import inspect, text
from models.base import Base


def run_migration():
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    # Import all models to register them
    from models.dev_blog_entry import DevBlogEntry
    from models.weekly_meeting import WeeklyMeeting
    from models.action_item import ActionItem, ActionItemComment
    from models.user_mention_permission import UserMentionPermission

    tables_to_create = [
        ('dev_blog_entries', DevBlogEntry),
        ('weekly_meetings', WeeklyMeeting),
        ('action_items', ActionItem),
        ('action_item_comments', ActionItemComment),
        ('user_mention_permissions', UserMentionPermission),
    ]

    for table_name, model in tables_to_create:
        if table_name not in existing_tables:
            print(f"Creating table: {table_name}")
            model.__table__.create(engine)
            print(f"  ✓ Created {table_name}")
        else:
            print(f"  - Table {table_name} already exists, skipping")

    # Check and add can_export_tickets column to permissions
    perm_columns = [c['name'] for c in inspector.get_columns('permissions')]

    with engine.connect() as conn:
        if 'can_export_tickets' not in perm_columns:
            print("Adding can_export_tickets column to permissions...")
            conn.execute(text("ALTER TABLE permissions ADD COLUMN can_export_tickets BOOLEAN DEFAULT 0"))
            conn.commit()
            print("  ✓ Added can_export_tickets")
        else:
            print("  - can_export_tickets already exists")

        if 'mention_filter_enabled' not in [c['name'] for c in inspector.get_columns('users')]:
            print("Adding mention_filter_enabled column to users...")
            conn.execute(text("ALTER TABLE users ADD COLUMN mention_filter_enabled BOOLEAN DEFAULT 0"))
            conn.commit()
            print("  ✓ Added mention_filter_enabled")
        else:
            print("  - mention_filter_enabled already exists")

    print("\n✓ Migration complete!")


if __name__ == '__main__':
    run_migration()
