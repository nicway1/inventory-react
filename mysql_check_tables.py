#!/usr/bin/env python3
"""
Quick MySQL table check - run on PythonAnywhere
"""

import os
import sys

os.environ['DATABASE_URL'] = 'mysql+pymysql://nicway2:truelog123%40@nicway2.mysql.pythonanywhere-services.com/nicway2$inventory'

try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    print("PyMySQL not installed")
    sys.exit(1)

from sqlalchemy import create_engine, text

engine = create_engine(os.environ['DATABASE_URL'], pool_pre_ping=True)

with engine.connect() as conn:
    # Check for activities table
    result = conn.execute(text("SHOW TABLES LIKE 'activities'"))
    has_activities = result.fetchone() is not None
    print(f"activities table: {'EXISTS' if has_activities else 'MISSING'}")

    # Check for ticket_category_configs table
    result = conn.execute(text("SHOW TABLES LIKE 'ticket_category_configs'"))
    has_tcc = result.fetchone() is not None
    print(f"ticket_category_configs table: {'EXISTS' if has_tcc else 'MISSING'}")

    if has_activities:
        result = conn.execute(text("SELECT COUNT(*) FROM activities"))
        print(f"  activities rows: {result.fetchone()[0]}")

    if has_tcc:
        result = conn.execute(text("SELECT COUNT(*) FROM ticket_category_configs"))
        print(f"  ticket_category_configs rows: {result.fetchone()[0]}")

    # List all tables
    print("\nAll tables in MySQL:")
    result = conn.execute(text("SHOW TABLES"))
    tables = [row[0] for row in result.fetchall()]
    for t in sorted(tables):
        print(f"  {t}")
