#!/usr/bin/env python3
"""
Script to add Internal Transfer category to CategoryDisplayConfig
"""

from database import SessionLocal
from models.ticket_category_config import CategoryDisplayConfig
from models.ticket import TicketCategory

def add_internal_transfer_category():
    """Add Internal Transfer to the category display configs"""
    db = SessionLocal()
    try:
        # Check if INTERNAL_TRANSFER already exists
        existing = db.query(CategoryDisplayConfig).filter_by(category_key='INTERNAL_TRANSFER').first()

        if existing:
            print(f"Internal Transfer category already exists: {existing}")
            print(f"  - Display Name: {existing.display_name}")
            print(f"  - Enabled: {existing.is_enabled}")
            print(f"  - Sort Order: {existing.sort_order}")
            return

        # Get the current highest sort order
        max_sort_order = db.query(CategoryDisplayConfig).order_by(CategoryDisplayConfig.sort_order.desc()).first()
        next_sort_order = (max_sort_order.sort_order + 1) if max_sort_order else 0

        # Create new config for Internal Transfer
        config = CategoryDisplayConfig(
            category_key='INTERNAL_TRANSFER',
            display_name='Internal Transfer',
            is_enabled=True,
            is_predefined=True,
            sort_order=next_sort_order
        )

        db.add(config)
        db.commit()

        print("✓ Successfully added Internal Transfer category to display configs!")
        print(f"  - Category Key: INTERNAL_TRANSFER")
        print(f"  - Display Name: Internal Transfer")
        print(f"  - Sort Order: {next_sort_order}")

    except Exception as e:
        db.rollback()
        print(f"✗ Error adding Internal Transfer category: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == '__main__':
    add_internal_transfer_category()
