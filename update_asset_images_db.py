#!/usr/bin/env python3
"""
Script to update asset image_url in database based on existing image files.
Run this on PythonAnywhere after pulling the code with images.
"""

import os
import re
from database import SessionLocal
from models.asset import Asset

# Path to asset images
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'assets')

def main():
    session = SessionLocal()

    try:
        # Get all existing image files
        if not os.path.exists(UPLOAD_DIR):
            print(f"Directory not found: {UPLOAD_DIR}")
            return

        image_files = os.listdir(UPLOAD_DIR)
        print(f"Found {len(image_files)} image files in {UPLOAD_DIR}")

        # Build a map of asset_id -> image path
        image_map = {}
        for filename in image_files:
            # Extract ID from filename like "asset_123.jpg"
            match = re.match(r'asset_(\d+)\.(jpg|png|gif)', filename)
            if match:
                asset_id = int(match.group(1))
                image_map[asset_id] = f"/static/uploads/assets/{filename}"

        print(f"Mapped {len(image_map)} asset images")

        # Update database
        updated = 0
        for asset_id, image_url in image_map.items():
            asset = session.query(Asset).filter_by(id=asset_id).first()
            if asset:
                if asset.image_url != image_url:
                    print(f"[{asset_id}] {(asset.name or 'Unknown')[:40]}: {image_url}")
                    asset.image_url = image_url
                    updated += 1
            else:
                print(f"[{asset_id}] Asset not found in database")

        session.commit()
        print(f"\nUpdated {updated} assets with image URLs")

    finally:
        session.close()

if __name__ == '__main__':
    main()
