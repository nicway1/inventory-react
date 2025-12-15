#!/usr/bin/env python3
"""
Create the user_queue_permissions table.
Run this script on PythonAnywhere after pulling the latest code.

Usage:
    python3 create_user_queue_permissions_table.py
"""

from database import engine
from models.user_queue_permission import UserQueuePermission

print("Creating user_queue_permissions table...")
UserQueuePermission.__table__.create(engine, checkfirst=True)
print("Done! Table created successfully.")
