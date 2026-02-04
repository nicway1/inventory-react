#!/usr/bin/env python3
"""
Count all assets in local database
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.store_instances import db_manager
from models.asset import Asset, AssetStatus
from sqlalchemy import func

def count_assets():
    db_session = db_manager.get_session()

    try:
        total = db_session.query(Asset).count()
        print(f"Total assets in database: {total}")

        # Count by status
        status_counts = db_session.query(
            Asset.status,
            func.count(Asset.id)
        ).group_by(Asset.status).all()

        print("\nBy status:")
        for status, count in status_counts:
            print(f"  {status.value if status else 'NULL'}: {count}")

        # Count by company
        company_counts = db_session.query(
            Asset.company_id,
            func.count(Asset.id)
        ).group_by(Asset.company_id).all()

        print("\nBy company_id:")
        for company_id, count in company_counts:
            print(f"  Company {company_id if company_id else 'NULL'}: {count}")

        # Check IN_STOCK with customer
        in_stock_with_customer = db_session.query(Asset).filter(
            Asset.status == AssetStatus.IN_STOCK,
            Asset.customer != None
        ).count()

        print(f"\nIN_STOCK assets with customer field: {in_stock_with_customer}")

        # Sample IN_STOCK assets
        print("\nFirst 10 IN_STOCK assets:")
        in_stock = db_session.query(Asset).filter(
            Asset.status == AssetStatus.IN_STOCK
        ).limit(10).all()

        for asset in in_stock:
            print(f"  ID: {asset.id}, Serial: {asset.serial_num}, Customer: {asset.customer}, Company ID: {asset.company_id}, Customer ID: {asset.customer_id}")

    finally:
        db_session.close()

if __name__ == "__main__":
    count_assets()
