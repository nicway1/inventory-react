#!/usr/bin/env python3
"""
Update the local asset to IN_STOCK status for testing
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.store_instances import db_manager
from models.asset import Asset, AssetStatus

def fix_asset_status():
    db_session = db_manager.get_session()

    try:
        # Get the asset
        asset = db_session.query(Asset).filter(Asset.id == 6802).first()

        if asset:
            print(f"Current status: {asset.status.value if asset.status else 'None'}")
            print(f"Changing to: In Stock")

            asset.status = AssetStatus.IN_STOCK
            db_session.commit()

            print(f"✓ Updated asset {asset.id} to IN_STOCK")
            print(f"\nAsset details:")
            print(f"  ID: {asset.id}")
            print(f"  Serial: {asset.serial_num}")
            print(f"  Model: {asset.model}")
            print(f"  Status: {asset.status.value}")
            print(f"  Company ID: {asset.company_id}")
            print(f"  Customer ID: {asset.customer_id}")
        else:
            print("Asset not found!")

    except Exception as e:
        print(f"Error: {e}")
        db_session.rollback()
    finally:
        db_session.close()

if __name__ == "__main__":
    fix_asset_status()
