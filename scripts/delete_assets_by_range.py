#!/usr/bin/env python3
"""
Script to delete assets by asset tag range
Run this on PythonAnywhere console:
    cd /home/ainventory/inventory && python scripts/delete_assets_by_range.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.asset import Asset

def delete_assets_by_tag_range(start_tag, end_tag, dry_run=True):
    """
    Delete assets within a tag range (e.g., SG-1180 to SG-1206)

    Args:
        start_tag: Starting asset tag number (e.g., 1180)
        end_tag: Ending asset tag number (e.g., 1206)
        dry_run: If True, only show what would be deleted without actually deleting
    """
    db = SessionLocal()

    try:
        # Find all assets in the range
        assets_to_delete = []
        for num in range(start_tag, end_tag + 1):
            tag = f"SG-{num}"
            asset = db.query(Asset).filter(Asset.asset_tag == tag).first()
            if asset:
                assets_to_delete.append(asset)

        print(f"\n{'[DRY RUN] ' if dry_run else ''}Found {len(assets_to_delete)} assets to delete:")
        print("-" * 80)

        for asset in assets_to_delete:
            print(f"  {asset.asset_tag}: {asset.name} | Serial: {asset.serial_num} | Model: {asset.model or '-'}")

        print("-" * 80)

        if dry_run:
            print(f"\n[DRY RUN] Would delete {len(assets_to_delete)} assets.")
            print("To actually delete, run with dry_run=False")
            return

        # Confirm deletion
        confirm = input(f"\nAre you sure you want to DELETE {len(assets_to_delete)} assets? (type 'YES' to confirm): ")
        if confirm != 'YES':
            print("Aborted.")
            return

        # Delete assets - first remove ticket associations via raw SQL
        from sqlalchemy import text

        asset_ids = [a.id for a in assets_to_delete]
        print(f"\nRemoving ticket associations for {len(asset_ids)} assets...")

        # Delete from ticket_assets association table first
        if asset_ids:
            placeholders = ','.join([str(id) for id in asset_ids])
            db.execute(text(f"DELETE FROM ticket_assets WHERE asset_id IN ({placeholders})"))

            # Also delete asset history if exists
            try:
                db.execute(text(f"DELETE FROM asset_history WHERE asset_id IN ({placeholders})"))
            except:
                pass  # Table might not exist

            # Delete from ticket_asset_checkins if exists
            try:
                db.execute(text(f"DELETE FROM ticket_asset_checkins WHERE asset_id IN ({placeholders})"))
            except:
                pass  # Table might not exist

        db.commit()
        print("  Associations removed.")

        # Now delete the assets
        deleted_count = 0
        for asset in assets_to_delete:
            db.delete(asset)
            deleted_count += 1
            print(f"  Deleted: {asset.asset_tag}")

        db.commit()
        print(f"\nSuccessfully deleted {deleted_count} assets.")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def delete_assets_by_ticket(ticket_id, dry_run=True):
    """
    Delete all assets linked to a specific ticket

    Args:
        ticket_id: The ticket ID (integer)
        dry_run: If True, only show what would be deleted
    """
    from models.ticket import Ticket

    db = SessionLocal()

    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            print(f"Ticket {ticket_id} not found")
            return

        assets = list(ticket.assets)
        print(f"\n{'[DRY RUN] ' if dry_run else ''}Ticket {ticket.display_id} has {len(assets)} assets:")
        print("-" * 80)

        for asset in assets:
            print(f"  {asset.asset_tag}: {asset.name} | Serial: {asset.serial_num} | Model: {asset.model or '-'}")

        print("-" * 80)

        if dry_run:
            print(f"\n[DRY RUN] Would delete {len(assets)} assets.")
            print("To actually delete, call with dry_run=False")
            return

        # Confirm deletion
        confirm = input(f"\nAre you sure you want to DELETE {len(assets)} assets from ticket {ticket.display_id}? (type 'YES' to confirm): ")
        if confirm != 'YES':
            print("Aborted.")
            return

        # Delete assets
        deleted_count = 0
        for asset in assets:
            ticket.assets.remove(asset)
            db.delete(asset)
            deleted_count += 1
            print(f"  Deleted: {asset.asset_tag}")

        db.commit()
        print(f"\nSuccessfully deleted {deleted_count} assets from ticket {ticket.display_id}.")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    print("Asset Deletion Script")
    print("=" * 80)
    print("\nOptions:")
    print("  1. Delete by asset tag range (e.g., SG-1180 to SG-1206)")
    print("  2. Delete by ticket ID")

    choice = input("\nEnter choice (1 or 2): ").strip()

    if choice == "1":
        start = int(input("Enter start tag number (e.g., 1180): "))
        end = int(input("Enter end tag number (e.g., 1206): "))

        # First do dry run
        delete_assets_by_tag_range(start, end, dry_run=True)

        proceed = input("\nProceed with actual deletion? (y/n): ").strip().lower()
        if proceed == 'y':
            delete_assets_by_tag_range(start, end, dry_run=False)

    elif choice == "2":
        ticket_id = int(input("Enter ticket ID: "))

        # First do dry run
        delete_assets_by_ticket(ticket_id, dry_run=True)

        proceed = input("\nProceed with actual deletion? (y/n): ").strip().lower()
        if proceed == 'y':
            delete_assets_by_ticket(ticket_id, dry_run=False)

    else:
        print("Invalid choice")
