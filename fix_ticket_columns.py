#!/usr/bin/env python3
"""
Fix for SQLAlchemy cache issue with ticket columns.
This script ensures the columns exist and forces SQLAlchemy to recognize them.
"""

import sqlite3
import sys
import os

def fix_ticket_columns():
    """Ensure ticket columns exist and are properly recognized"""

    print("🔧 Fixing ticket column recognition...")

    try:
        # Connect to the database
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()

        # Define the columns that should exist
        required_columns = [
            ('item_packed', 'BOOLEAN', 'FALSE'),
            ('item_packed_at', 'DATETIME', 'NULL'),
            ('shipping_tracking_created_at', 'DATETIME', 'NULL')
        ]

        # Check current schema
        cursor.execute('PRAGMA table_info(tickets)')
        existing_columns = {col[1]: col for col in cursor.fetchall()}

        changes_made = False

        for col_name, col_type, default_val in required_columns:
            if col_name not in existing_columns:
                print(f"Adding missing column: {col_name}")
                sql = f"ALTER TABLE tickets ADD COLUMN {col_name} {col_type} DEFAULT {default_val};"
                cursor.execute(sql)
                changes_made = True
                print(f"✅ Added {col_name}")
            else:
                print(f"✅ Column {col_name} already exists")

        if changes_made:
            conn.commit()
            print("💾 Database changes committed")
        else:
            print("✅ All columns already exist")

        # Force SQLAlchemy to refresh its metadata by clearing any cached model files
        cache_dirs = ['__pycache__', 'models/__pycache__']
        for cache_dir in cache_dirs:
            if os.path.exists(cache_dir):
                import shutil
                shutil.rmtree(cache_dir)
                print(f"🗑️  Cleared cache: {cache_dir}")

        # Clear .pyc files
        for root, dirs, files in os.walk('.'):
            for file in files:
                if file.endswith('.pyc'):
                    os.remove(os.path.join(root, file))

        conn.close()

        print("\n🔄 Please restart your Flask application now.")
        print("The SQLAlchemy metadata cache has been cleared.")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting ticket column fix...")
    success = fix_ticket_columns()

    if success:
        print("✅ Fix completed successfully!")
        print("\n🎯 Next steps:")
        print("1. Stop your Flask application if it's running")
        print("2. Run: python3 app.py")
        print("3. The SQLAlchemy error should be resolved")
    else:
        print("❌ Fix failed!")
        sys.exit(1)