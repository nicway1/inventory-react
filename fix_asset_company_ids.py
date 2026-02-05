#!/usr/bin/env python3
"""
Fix assets with customer name but NULL company_id
This script matches customer names to companies and updates company_id
"""

from database import SessionLocal
from models.asset import Asset
from models.company import Company
from sqlalchemy import and_

def fix_asset_company_ids():
    db_session = SessionLocal()
    try:
        # Find all assets with customer set but company_id NULL
        assets_without_company_id = db_session.query(Asset).filter(
            and_(
                Asset.customer.isnot(None),
                Asset.customer != '',
                Asset.company_id.is_(None)
            )
        ).all()

        print(f"Found {len(assets_without_company_id)} assets with customer but no company_id")

        # Get all companies for matching
        companies = db_session.query(Company).all()
        company_map = {company.name.lower(): company.id for company in companies}

        updated_count = 0
        not_found_count = 0
        not_found_customers = set()

        for asset in assets_without_company_id:
            customer_lower = asset.customer.lower() if asset.customer else None

            if customer_lower and customer_lower in company_map:
                # Match found - update company_id
                asset.company_id = company_map[customer_lower]
                print(f"✓ Asset {asset.id} ({asset.name}, Serial: {asset.serial_num}): Set company_id to {asset.company_id} ({asset.customer})")
                updated_count += 1
            else:
                # No match found
                not_found_customers.add(asset.customer)
                not_found_count += 1
                print(f"✗ Asset {asset.id} ({asset.name}, Serial: {asset.serial_num}): No company found for customer '{asset.customer}'")

        # Show summary
        print("\n" + "="*80)
        print(f"SUMMARY:")
        print(f"  Total assets processed: {len(assets_without_company_id)}")
        print(f"  Successfully updated: {updated_count}")
        print(f"  No matching company: {not_found_count}")

        if not_found_customers:
            print(f"\nCustomers without matching companies:")
            for customer in sorted(not_found_customers):
                print(f"  - {customer}")

        # Ask for confirmation
        if updated_count > 0:
            print("\n" + "="*80)
            import sys
            if len(sys.argv) > 1 and sys.argv[1] == '--confirm':
                response = 'yes'
                print(f"\nAuto-confirming (--confirm flag)")
            else:
                try:
                    response = input(f"\nCommit {updated_count} updates to database? (yes/no): ")
                except EOFError:
                    response = 'yes'
                    print(f"\nNon-interactive mode - auto-confirming")

            if response.lower() in ['yes', 'y']:
                db_session.commit()
                print(f"✓ Successfully committed {updated_count} updates!")
            else:
                db_session.rollback()
                print("✗ Changes rolled back. No updates made.")
        else:
            print("\nNo updates to commit.")

    except Exception as e:
        print(f"Error: {e}")
        db_session.rollback()
        raise
    finally:
        db_session.close()

if __name__ == "__main__":
    fix_asset_company_ids()
