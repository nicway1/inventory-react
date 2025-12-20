#!/usr/bin/env python3
"""
Script to update accessory image_url in database based on existing image files.
Run this on PythonAnywhere after pulling the code with images.
"""

import os
import re
from database import SessionLocal
from models.accessory import Accessory

# Path to accessory images
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'accessories')

def main():
    session = SessionLocal()

    try:
        # Get all existing image files
        if not os.path.exists(UPLOAD_DIR):
            print(f"Directory not found: {UPLOAD_DIR}")
            return

        image_files = os.listdir(UPLOAD_DIR)
        print(f"Found {len(image_files)} image files in {UPLOAD_DIR}")

        # Build a map of accessory_id -> image path
        image_map = {}
        for filename in image_files:
            # Extract ID from filename like "accessory_123.jpg"
            match = re.match(r'accessory_(\d+)\.(jpg|png|gif)', filename)
            if match:
                acc_id = int(match.group(1))
                image_map[acc_id] = f"/static/uploads/accessories/{filename}"

        print(f"Mapped {len(image_map)} accessory images")

        # Update database
        updated = 0
        for acc_id, image_url in image_map.items():
            accessory = session.query(Accessory).filter_by(id=acc_id).first()
            if accessory:
                if accessory.image_url != image_url:
                    print(f"[{acc_id}] {accessory.name[:40]}: {image_url}")
                    accessory.image_url = image_url
                    updated += 1
            else:
                print(f"[{acc_id}] Accessory not found in database")

        session.commit()
        print(f"\nUpdated {updated} accessories with image URLs")

    finally:
        session.close()

if __name__ == '__main__':
    main()
