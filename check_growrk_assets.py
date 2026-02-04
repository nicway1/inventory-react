#!/usr/bin/env python3
"""
Check GROWRK assets by customer field
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.store_instances import db_manager
from models.asset import Asset, AssetStatus

def check_growrk():
    db_session = db_manager.get_session()

    try:
        # Find assets with "GROWRK" in customer field
        growrk_assets = db_session.query(Asset).filter(
            Asset.customer.like('%GROWRK%')
        ).all()

        print(f"Total assets with 'GROWRK' in customer field: {len(growrk_assets)}")

        # Count by status
        statuses = {}
        for asset in growrk_assets:
            status = asset.status.value if asset.status else 'NULL'
            statuses[status] = statuses.get(status, 0) + 1

        print("\nBy status:")
        for status, count in sorted(statuses.items()):
            print(f"  {status}: {count}")

        # IN_STOCK only
        in_stock_growrk = db_session.query(Asset).filter(
            Asset.customer.like('%GROWRK%'),
            Asset.status == AssetStatus.IN_STOCK
        ).all()

        print(f"\nIN_STOCK GROWRK assets: {len(in_stock_growrk)}")
        print("\nFirst 10:")
        for asset in in_stock_growrk[:10]:
            print(f"  {asset.serial_num} - {asset.model} - {asset.customer}")

    finally:
        db_session.close()

if __name__ == "__main__":
    check_growrk()
