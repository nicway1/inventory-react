#!/usr/bin/env python3
"""
Combined script to update asset and accessory image_url in database
based on existing shared images.
Run this on PythonAnywhere after pulling the code with images.
"""

import os
import re
import hashlib
from database import SessionLocal
from models.asset import Asset
from models.accessory import Accessory

# Path to shared images
SHARED_DIR = os.path.join(os.path.dirname(__file__), 'static', 'images', 'products', 'shared')

# Mapping of product types to image files
ASSET_IMAGE_MAP = {
    'macbook_pro_14': ['a2992', 'a2442', 'macbook pro 14'],
    'macbook_pro_13': ['a2251', 'a2338', 'macbook pro 13'],
    'macbook_pro_16': ['macbook pro 16'],
    'macbook_pro': ['macbook pro'],
    'macbook_air_15': ['a3114', 'macbook air 15'],
    'macbook_air_13': ['a3240', 'a2337', 'macbook air 13'],
    'macbook_air': ['macbook air'],
    'mac_mini': ['mac mini'],
    'surface_laptop': ['surface laptop'],
    'asus_keyboard': ['asus tuf', 'asus keyboard'],
}

ACCESSORY_IMAGE_MAP = {
    '3m_privacy_filter': ['3m privacy', 'privacy filter', 'privacy screen'],
    'apple_magic_keyboard': ['magic keyboard'],
    'apple_magic_mouse': ['magic mouse'],
    'apple_earpods': ['earpods', 'ear pods'],
    'jabra_evolve2_40': ['evolve2 40', 'evolve 240'],
    'jabra_evolve2_50': ['evolve2 50', 'evolve 250'],
    'jabra_evolve2_65': ['evolve2 65', 'evolve 265'],
    'jabra_evolve2_75': ['evolve2 75', 'evolve 275'],
    'jabra_headset': ['jabra'],
    'asus_accessory': ['asus'],
}


def find_shared_image(search_text, image_map, default=None):
    """Find matching shared image based on search text"""
    search_lower = search_text.lower()

    for image_name, keywords in image_map.items():
        for keyword in keywords:
            if keyword in search_lower:
                # Find the actual file (jpg or png)
                for ext in ['.jpg', '.png']:
                    path = os.path.join(SHARED_DIR, image_name + ext)
                    if os.path.exists(path):
                        return f"/static/images/products/shared/{image_name}{ext}"
    return default


def main():
    session = SessionLocal()

    try:
        # Get list of available shared images
        shared_images = []
        if os.path.exists(SHARED_DIR):
            shared_images = [f for f in os.listdir(SHARED_DIR) if f.endswith(('.jpg', '.png'))]
        print(f"Found {len(shared_images)} shared images in {SHARED_DIR}")

        # Update assets
        print("\n=== Updating Assets ===")
        assets = session.query(Asset).all()
        asset_updated = 0

        for asset in assets:
            search_text = f"{asset.name or ''} {asset.model or ''}"
            new_image = find_shared_image(search_text, ASSET_IMAGE_MAP)

            if new_image and asset.image_url != new_image:
                asset.image_url = new_image
                asset_updated += 1

        print(f"Updated {asset_updated} assets")

        # Update accessories
        print("\n=== Updating Accessories ===")
        accessories = session.query(Accessory).all()
        acc_updated = 0

        for acc in accessories:
            search_text = f"{acc.name or ''} {acc.manufacturer or ''} {acc.category or ''}"
            new_image = find_shared_image(search_text, ACCESSORY_IMAGE_MAP)

            if new_image and acc.image_url != new_image:
                acc.image_url = new_image
                acc_updated += 1

        print(f"Updated {acc_updated} accessories")

        session.commit()

        print("\n=== Summary ===")
        print(f"Assets updated: {asset_updated}")
        print(f"Accessories updated: {acc_updated}")

    finally:
        session.close()


if __name__ == '__main__':
    main()
