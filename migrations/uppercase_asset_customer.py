#!/usr/bin/env python3
"""
Migration script to convert all Asset.customer values to uppercase.
Run: python migrations/uppercase_asset_customer.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db_manager import DatabaseManager
from models.asset import Asset

def run_migration():
    db = DatabaseManager()
    session = db.get_session()

    print("Starting Asset.customer uppercase migration...")

    # Get all assets with non-null customer values
    assets = session.query(Asset).filter(
        Asset.customer.isnot(None),
        Asset.customer != ''
    ).all()

    print(f"Found {len(assets)} assets with customer values")

    updated_count = 0
    for asset in assets:
        normalized = asset.customer.strip().upper()
        if asset.customer != normalized:
            asset.customer = normalized
            updated_count += 1

    print(f"Updated {updated_count} asset customer values to uppercase")

    session.commit()
    session.close()

    print("Migration complete!")

if __name__ == '__main__':
    run_migration()
