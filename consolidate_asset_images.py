#!/usr/bin/env python3
"""
Consolidate duplicate asset images into shared product images.
This reduces 2250 files to ~9 shared images.
"""

import hashlib
import os
import shutil
from collections import defaultdict
from database import SessionLocal
from models.asset import Asset

# Paths
UPLOAD_DIR = 'static/uploads/assets'
SHARED_DIR = 'static/images/products/shared'

# Mapping of hash -> shared image name (will be populated)
HASH_TO_PRODUCT = {}

def get_file_hash(filepath):
    """Get MD5 hash of file"""
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def identify_product_type(asset):
    """Identify the product type from asset info"""
    name = (asset.name or '').lower()
    model = (asset.model or '').lower()

    if 'macbook pro 14' in name or 'a2992' in model or 'a2442' in model:
        return 'macbook_pro_14'
    elif 'macbook pro 16' in name:
        return 'macbook_pro_16'
    elif 'macbook pro 13' in name or 'a2251' in model or 'a2338' in model:
        return 'macbook_pro_13'
    elif 'macbook pro' in name:
        return 'macbook_pro'
    elif 'macbook air 15' in name or 'a3114' in model:
        return 'macbook_air_15'
    elif 'macbook air 13' in name or 'a3240' in model or 'a2337' in model:
        return 'macbook_air_13'
    elif 'macbook air' in name:
        return 'macbook_air'
    elif 'mac mini' in name:
        return 'mac_mini'
    elif 'imac' in name:
        return 'imac'
    elif 'surface laptop' in name:
        return 'surface_laptop'
    elif 'surface pro' in name:
        return 'surface_pro'
    elif 'surface' in name:
        return 'surface'
    elif 'thinkpad' in name or 'thinkpad' in model:
        return 'thinkpad'
    elif 'latitude' in name or 'latitude' in model:
        return 'dell_latitude'
    elif 'xps' in name or 'xps' in model:
        return 'dell_xps'
    elif 'elitebook' in name or 'elitebook' in model:
        return 'hp_elitebook'
    elif 'probook' in name or 'probook' in model:
        return 'hp_probook'
    elif 'iphone' in name:
        return 'iphone'
    elif 'ipad' in name:
        return 'ipad'
    elif 'asus' in name.lower():
        return 'asus_keyboard'
    else:
        return 'generic_laptop'

def main():
    # Create shared directory
    os.makedirs(SHARED_DIR, exist_ok=True)

    # Step 1: Group files by hash
    hash_to_files = defaultdict(list)
    for f in os.listdir(UPLOAD_DIR):
        if f.endswith(('.jpg', '.png', '.gif')):
            path = os.path.join(UPLOAD_DIR, f)
            h = get_file_hash(path)
            hash_to_files[h].append(f)

    print(f"Found {len(hash_to_files)} unique images from {sum(len(v) for v in hash_to_files.values())} files")

    # Step 2: Identify product type for each hash and create shared images
    session = SessionLocal()
    hash_to_shared = {}

    try:
        for h, files in hash_to_files.items():
            # Get sample asset to identify product type
            sample = files[0]
            asset_id = int(sample.replace('asset_', '').replace('.jpg', '').replace('.png', '').replace('.gif', ''))
            asset = session.get(Asset, asset_id)

            if asset:
                product_type = identify_product_type(asset)
            else:
                product_type = 'unknown'

            # Get extension
            ext = sample.split('.')[-1]
            shared_name = f"{product_type}.{ext}"
            shared_path = os.path.join(SHARED_DIR, shared_name)

            # Handle duplicates by adding a number
            counter = 1
            while shared_name in [v.split('/')[-1] for v in hash_to_shared.values()]:
                shared_name = f"{product_type}_{counter}.{ext}"
                shared_path = os.path.join(SHARED_DIR, shared_name)
                counter += 1

            # Copy one file to shared location
            src = os.path.join(UPLOAD_DIR, files[0])
            shutil.copy2(src, shared_path)

            hash_to_shared[h] = f"/static/images/products/shared/{shared_name}"
            print(f"Created: {shared_name} ({len(files)} assets)")

        # Step 3: Update database with shared image paths
        print("\nUpdating database...")
        updated = 0
        for h, files in hash_to_files.items():
            shared_url = hash_to_shared[h]
            for f in files:
                asset_id = int(f.replace('asset_', '').replace('.jpg', '').replace('.png', '').replace('.gif', ''))
                asset = session.get(Asset, asset_id)
                if asset and asset.image_url != shared_url:
                    asset.image_url = shared_url
                    updated += 1

        session.commit()
        print(f"Updated {updated} assets to use shared images")

        # Step 4: Remove individual asset images
        print("\nRemoving duplicate files...")
        removed = 0
        for f in os.listdir(UPLOAD_DIR):
            if f.endswith(('.jpg', '.png', '.gif')):
                os.remove(os.path.join(UPLOAD_DIR, f))
                removed += 1

        print(f"Removed {removed} duplicate files")

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Created {len(hash_to_shared)} shared images in {SHARED_DIR}")
        print(f"Updated {updated} assets in database")
        print(f"Removed {removed} duplicate files")
        print(f"Disk space saved: ~{removed * 40 // 1024} MB (estimated)")

    finally:
        session.close()

if __name__ == '__main__':
    main()
