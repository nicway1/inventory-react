#!/usr/bin/env python3
"""
Script to update DEVELOPER permissions for Development Console access.
Run this script after deploying to update existing database records.

Usage: python update_developer_permissions.py
"""

import sqlite3
import os

# Determine database path
if os.path.exists('/home/nicway/inventory/inventory.db'):
    DB_PATH = '/home/nicway/inventory/inventory.db'
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory.db')

def update_permissions():
    print(f"Updating DEVELOPER permissions in: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Update DEVELOPER permissions for Development Console
    cursor.execute("""
        UPDATE permissions SET
            can_access_development = 1,
            can_view_features = 1,
            can_create_features = 1,
            can_edit_features = 1,
            can_approve_features = 1,
            can_view_bugs = 1,
            can_create_bugs = 1,
            can_edit_bugs = 1,
            can_view_releases = 1,
            can_create_releases = 1,
            can_edit_releases = 1
        WHERE user_type = 'DEVELOPER'
    """)

    rows_updated = cursor.rowcount
    conn.commit()

    # Verify the update
    cursor.execute("""
        SELECT user_type, can_access_development, can_view_features,
               can_create_features, can_edit_features
        FROM permissions
        WHERE user_type = 'DEVELOPER'
    """)
    result = cursor.fetchone()

    conn.close()

    print(f"Updated {rows_updated} row(s)")
    if result:
        print(f"DEVELOPER permissions: access_dev={result[1]}, view_features={result[2]}, create_features={result[3]}, edit_features={result[4]}")
    print("Done!")

if __name__ == '__main__':
    update_permissions()
