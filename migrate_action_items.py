#!/usr/bin/env python3
"""
Migration script to create the action_items table.
Run this script to add the Weekly Meeting Action Items feature.

Usage:
    cd ~/inventory
    source venv/bin/activate
    python migrate_action_items.py
"""

from database import engine
from sqlalchemy import text, inspect

def check_table_exists(table_name):
    """Check if a table exists in the database"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()

def check_column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def add_column_if_missing(table_name, column_name, column_type):
    """Add a column to a table if it doesn't exist"""
    if check_column_exists(table_name, column_name):
        print(f"  ✓ Column '{column_name}' already exists.")
        return False

    print(f"  Adding '{column_name}' column...")
    with engine.connect() as conn:
        conn.execute(text(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}'))
        conn.commit()
    print(f"  ✓ Added '{column_name}' column!")
    return True

def create_action_items_table():
    """Create the action_items table if it doesn't exist"""
    if check_table_exists('action_items'):
        print("✓ Table 'action_items' already exists.")
        return False

    print("Creating 'action_items' table...")

    create_table_sql = """
    CREATE TABLE action_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title VARCHAR(500) NOT NULL,
        description TEXT,
        status VARCHAR(20) DEFAULT 'NOT_STARTED',
        priority VARCHAR(20) DEFAULT 'MEDIUM',
        meeting_date DATE,
        meeting_notes TEXT,
        created_by_id INTEGER NOT NULL,
        assigned_to_id INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME,
        due_date DATE,
        completed_at DATETIME,
        position INTEGER DEFAULT 0,
        FOREIGN KEY (created_by_id) REFERENCES users (id),
        FOREIGN KEY (assigned_to_id) REFERENCES users (id)
    )
    """

    # For PostgreSQL, adjust the SQL
    database_url = str(engine.url)
    if 'postgresql' in database_url:
        create_table_sql = """
        CREATE TABLE action_items (
            id SERIAL PRIMARY KEY,
            title VARCHAR(500) NOT NULL,
            description TEXT,
            status VARCHAR(20) DEFAULT 'NOT_STARTED',
            priority VARCHAR(20) DEFAULT 'MEDIUM',
            meeting_date DATE,
            meeting_notes TEXT,
            created_by_id INTEGER NOT NULL REFERENCES users(id),
            assigned_to_id INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            due_date DATE,
            completed_at TIMESTAMP,
            position INTEGER DEFAULT 0
        )
        """

    with engine.connect() as conn:
        conn.execute(text(create_table_sql))
        conn.commit()

    print("✓ Successfully created 'action_items' table!")
    return True

def add_tester_columns():
    """Add tester_id and item_number columns if they don't exist"""
    if not check_table_exists('action_items'):
        return 0

    changes = 0
    print("Checking for new columns...")

    if add_column_if_missing('action_items', 'tester_id', 'INTEGER REFERENCES users(id)'):
        changes += 1

    if add_column_if_missing('action_items', 'item_number', 'INTEGER'):
        changes += 1

    return changes


def create_weekly_meetings_table():
    """Create the weekly_meetings table if it doesn't exist"""
    if check_table_exists('weekly_meetings'):
        print("✓ Table 'weekly_meetings' already exists.")
        return False

    print("Creating 'weekly_meetings' table...")

    create_table_sql = """
    CREATE TABLE weekly_meetings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(200) NOT NULL,
        meeting_date DATE NOT NULL,
        notes TEXT,
        is_active BOOLEAN DEFAULT 1,
        created_by_id INTEGER NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME,
        FOREIGN KEY (created_by_id) REFERENCES users (id)
    )
    """

    # For PostgreSQL, adjust the SQL
    database_url = str(engine.url)
    if 'postgresql' in database_url:
        create_table_sql = """
        CREATE TABLE weekly_meetings (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            meeting_date DATE NOT NULL,
            notes TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_by_id INTEGER NOT NULL REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
        """

    with engine.connect() as conn:
        conn.execute(text(create_table_sql))
        conn.commit()

    print("✓ Successfully created 'weekly_meetings' table!")
    return True


def add_meeting_id_column():
    """Add meeting_id column to action_items if it doesn't exist"""
    if not check_table_exists('action_items'):
        return 0

    changes = 0
    if add_column_if_missing('action_items', 'meeting_id', 'INTEGER REFERENCES weekly_meetings(id)'):
        changes += 1

    return changes


def create_comments_table():
    """Create the action_item_comments table if it doesn't exist"""
    if check_table_exists('action_item_comments'):
        print("✓ Table 'action_item_comments' already exists.")
        return False

    print("Creating 'action_item_comments' table...")

    create_table_sql = """
    CREATE TABLE action_item_comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action_item_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME,
        FOREIGN KEY (action_item_id) REFERENCES action_items (id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """

    # For PostgreSQL, adjust the SQL
    database_url = str(engine.url)
    if 'postgresql' in database_url:
        create_table_sql = """
        CREATE TABLE action_item_comments (
            id SERIAL PRIMARY KEY,
            action_item_id INTEGER NOT NULL REFERENCES action_items(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id),
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
        """

    with engine.connect() as conn:
        conn.execute(text(create_table_sql))
        conn.commit()

    print("✓ Successfully created 'action_item_comments' table!")
    return True

def migrate():
    """Run all migrations"""
    print("Running Action Items migration...")
    print("-" * 40)

    changes_made = 0

    # Create weekly_meetings table first (since action_items references it)
    if create_weekly_meetings_table():
        changes_made += 1

    if create_action_items_table():
        changes_made += 1

    # Add new columns to existing table
    changes_made += add_tester_columns()

    # Add meeting_id column to action_items
    changes_made += add_meeting_id_column()

    # Create comments table
    if create_comments_table():
        changes_made += 1

    print("-" * 40)
    if changes_made == 0:
        print("No migrations needed. Database is up to date!")
    else:
        print(f"✓ Migration complete! {changes_made} change(s) made.")

if __name__ == '__main__':
    migrate()
