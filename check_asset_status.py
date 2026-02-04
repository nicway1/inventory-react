#!/usr/bin/env python3
"""
Check what status GROWRK assets have
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.store_instances import db_manager
from models.asset import Asset, AssetStatus
from models.customer_user import CustomerUser
from models.company import Company
from sqlalchemy import func

def check_asset_statuses():
    db_session = db_manager.get_session()

    try:
        # Get GROWRK and all its children
        growrk = db_session.query(Company).filter(Company.name == 'GROWRK').first()
        if not growrk:
            print("GROWRK company not found!")
            return

        company_ids = [growrk.id]
        if growrk.is_parent_company or growrk.child_companies.count() > 0:
            child_ids = [c.id for c in growrk.child_companies.all()]
            company_ids.extend(child_ids)

        print(f"Checking assets for GROWRK (ID: {growrk.id}) and {len(child_ids)} children")
        print(f"Company IDs: {company_ids}")

        # Get customer_user IDs
        customer_user_ids = [
            row[0] for row in db_session.query(CustomerUser.id).filter(
                CustomerUser.company_id.in_(company_ids)
            ).all()
        ]
        print(f"\nFound {len(customer_user_ids)} customer_user IDs")

        # Check total assets for these companies
        print("\n" + "=" * 80)
        print("ASSET COUNTS BY STATUS")
        print("=" * 80)

        from sqlalchemy import or_
        total_query = db_session.query(Asset).filter(
            or_(
                Asset.company_id.in_(company_ids),
                Asset.customer_id.in_(customer_user_ids)
            )
        )

        total_count = total_query.count()
        print(f"\nTotal assets (all statuses): {total_count}")

        # Count by status
        status_counts = db_session.query(
            Asset.status,
            func.count(Asset.id)
        ).filter(
            or_(
                Asset.company_id.in_(company_ids),
                Asset.customer_id.in_(customer_user_ids)
            )
        ).group_by(Asset.status).all()

        print("\nBreakdown by status:")
        for status, count in status_counts:
            print(f"  {status.value if status else 'NULL'}: {count} assets")

        # Show sample assets
        print("\n" + "=" * 80)
        print("SAMPLE ASSETS (first 10)")
        print("=" * 80)

        sample_assets = total_query.limit(10).all()
        for asset in sample_assets:
            print(f"  ID: {asset.id}, Serial: {asset.serial_num}, Status: {asset.status.value if asset.status else 'NULL'}, Model: {asset.model}")

        # Check IN_STOCK specifically
        print("\n" + "=" * 80)
        print("IN_STOCK ASSETS")
        print("=" * 80)

        in_stock = total_query.filter(Asset.status == AssetStatus.IN_STOCK).all()
        print(f"Found {len(in_stock)} IN_STOCK assets")

        if len(in_stock) > 0:
            print("\nIN_STOCK sample:")
            for asset in in_stock[:5]:
                print(f"  ID: {asset.id}, Serial: {asset.serial_num}, Model: {asset.model}")

    finally:
        db_session.close()

if __name__ == "__main__":
    check_asset_statuses()
