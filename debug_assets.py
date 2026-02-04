#!/usr/bin/env python3
"""
Debug script to check why user 53 can't see assets at /tickets/new
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.store_instances import db_manager
from models.user import User
from models.asset import Asset, AssetStatus
from models.customer_user import CustomerUser
from models.user_company_permission import UserCompanyPermission
from models.company import Company
from sqlalchemy import or_

def debug_user_assets():
    db_session = db_manager.get_session()

    try:
        # Get user 53
        user = db_session.query(User).get(53)
        if not user:
            print("User 53 not found!")
            return

        print("=" * 80)
        print(f"USER INFORMATION")
        print("=" * 80)
        print(f"Username: {user.username}")
        print(f"User Type: {user.user_type.value}")
        print(f"Company ID: {user.company_id}")
        print(f"Company: {user.company.name if user.company else 'None'}")

        # Get user's company permissions
        print("\n" + "=" * 80)
        print("COMPANY PERMISSIONS")
        print("=" * 80)

        company_perms = db_session.query(UserCompanyPermission).filter(
            UserCompanyPermission.user_id == user.id
        ).all()

        if company_perms:
            permitted_company_ids = [perm.company_id for perm in company_perms]
            print(f"Direct company permissions: {permitted_company_ids}")

            # Get company names
            for comp_id in permitted_company_ids:
                company = db_session.query(Company).get(comp_id)
                if company:
                    print(f"  - {company.name} (ID: {comp_id})")

            # Get child companies
            print("\nIncluding child companies:")
            permitted_companies = db_session.query(Company).filter(Company.id.in_(permitted_company_ids)).all()
            all_permitted_ids = list(permitted_company_ids)

            for company in permitted_companies:
                if company.is_parent_company or company.child_companies.count() > 0:
                    child_ids = [c.id for c in company.child_companies.all()]
                    all_permitted_ids.extend(child_ids)
                    for child in company.child_companies.all():
                        print(f"  - {child.name} (ID: {child.id}) [child of {company.name}]")

            permitted_company_ids = list(set(all_permitted_ids))
            print(f"\nTotal permitted company IDs: {permitted_company_ids}")
        else:
            print("NO COMPANY PERMISSIONS FOUND!")
            permitted_company_ids = []

        if not permitted_company_ids:
            print("\n⚠️  User has no company permissions - will see 0 assets")
            return

        # Get customer_user IDs from permitted companies
        print("\n" + "=" * 80)
        print("CUSTOMER USER IDs FROM PERMITTED COMPANIES")
        print("=" * 80)

        permitted_customer_user_ids = [
            row[0] for row in db_session.query(CustomerUser.id).filter(
                CustomerUser.company_id.in_(permitted_company_ids)
            ).all()
        ]
        print(f"Found {len(permitted_customer_user_ids)} customer_user IDs")
        if permitted_customer_user_ids[:10]:
            print(f"First 10: {permitted_customer_user_ids[:10]}")

        # Now query assets using the same logic as tickets.py
        print("\n" + "=" * 80)
        print("QUERYING ASSETS")
        print("=" * 80)

        # Start with base query - only IN_STOCK assets
        assets_query = db_session.query(Asset).filter(
            Asset.status == AssetStatus.IN_STOCK
        )

        print("Filtering by company permissions...")

        # Get company names for matching by customer field
        all_company_names = [c.name.strip() for c in permitted_companies]
        print(f"Company names for matching: {all_company_names}")

        # Match by company_id, customer_id, or customer name string
        from sqlalchemy import func
        name_conditions = [func.lower(Asset.customer).like(f"%{name.lower()}%") for name in all_company_names]

        assets_query = assets_query.filter(
            or_(
                Asset.company_id.in_(permitted_company_ids),
                Asset.customer_id.in_(permitted_customer_user_ids),
                *name_conditions  # Also match by customer name string
            )
        )
        print(f"Filtering by {len(permitted_company_ids)} company IDs, {len(permitted_customer_user_ids)} customer_user IDs, and {len(all_company_names)} company names")

        assets = assets_query.all()
        print(f"\n✓ Query returned {len(assets)} assets")

        # Now try to build assets_data like in the code
        print("\n" + "=" * 80)
        print("BUILDING ASSETS DATA")
        print("=" * 80)

        assets_data = []
        errors = []

        for i, asset in enumerate(assets):
            try:
                # Try to build the dict
                asset_dict = {
                    'id': asset.id,
                    'serial_number': asset.serial_num,
                    'model': asset.model,
                    'customer': asset.customer_user.company.name if asset.customer_user and asset.customer_user.company else asset.customer,
                    'asset_tag': asset.asset_tag
                }
                assets_data.append(asset_dict)

                if i < 3:
                    print(f"✓ Asset {i+1}: {asset_dict}")
            except Exception as e:
                error_msg = f"Asset ID {asset.id}: {str(e)}"
                errors.append(error_msg)
                print(f"✗ Error processing asset {asset.id}: {e}")
                print(f"   - serial_num: {getattr(asset, 'serial_num', 'N/A')}")
                print(f"   - customer_user: {getattr(asset, 'customer_user', 'N/A')}")
                print(f"   - customer: {getattr(asset, 'customer', 'N/A')}")

        print(f"\n" + "=" * 80)
        print(f"RESULTS")
        print("=" * 80)
        print(f"Total assets from query: {len(assets)}")
        print(f"Successfully processed: {len(assets_data)}")
        print(f"Errors: {len(errors)}")

        if errors:
            print(f"\n⚠️  ERRORS FOUND:")
            for error in errors[:10]:  # Show first 10 errors
                print(f"  - {error}")

        if len(assets_data) == 0 and len(assets) > 0:
            print(f"\n🔴 PROBLEM FOUND: Query returned {len(assets)} assets but ALL failed to process!")
            print("This is why the dropdown is empty!")
        elif len(assets_data) < len(assets):
            print(f"\n⚠️  WARNING: {len(assets) - len(assets_data)} assets failed to process")
        else:
            print(f"\n✓ All assets processed successfully!")
            if assets_data:
                print(f"\nFirst 3 assets for dropdown:")
                for asset in assets_data[:3]:
                    print(f"  {asset['serial_number']} - {asset['model']} ({asset['asset_tag']})")

    finally:
        db_session.close()

if __name__ == "__main__":
    debug_user_assets()
