#!/usr/bin/env python3
"""
Consolidate duplicate accessory images into shared product images.
"""

import hashlib
import os
import shutil
from collections import defaultdict
from database import SessionLocal
from models.accessory import Accessory

# Paths
UPLOAD_DIR = 'static/uploads/accessories'
SHARED_DIR = 'static/images/products/shared'

def get_file_hash(filepath):
    """Get MD5 hash of file"""
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def identify_product_type(accessory):
    """Identify the product type from accessory info"""
    name = (accessory.name or '').lower()
    category = (accessory.category or '').lower()
    manufacturer = (accessory.manufacturer or '').lower()

    if 'magic mouse' in name:
        return 'apple_magic_mouse'
    elif 'magic keyboard' in name:
        return 'apple_magic_keyboard'
    elif 'airpods' in name:
        return 'apple_airpods'
    elif 'earpods' in name:
        return 'apple_earpods'
    elif 'jabra' in name or 'jabra' in manufacturer:
        if 'evolve2 75' in name or 'evolve 275' in name:
            return 'jabra_evolve2_75'
        elif 'evolve2 65' in name:
            return 'jabra_evolve2_65'
        elif 'evolve2 50' in name:
            return 'jabra_evolve2_50'
        elif 'evolve2 40' in name or 'evolve 240' in name:
            return 'jabra_evolve2_40'
        else:
            return 'jabra_headset'
    elif '3m' in manufacturer or 'privacy' in name:
        return '3m_privacy_filter'
    elif 'asus' in manufacturer or 'asus' in name:
        return 'asus_accessory'
    elif 'logitech' in manufacturer:
        if 'mouse' in name or 'mouse' in category:
            return 'logitech_mouse'
        elif 'keyboard' in name or 'keyboard' in category:
            return 'logitech_keyboard'
        else:
            return 'logitech_accessory'
    elif 'keyboard' in category:
        return 'keyboard'
    elif 'mouse' in category:
        return 'mouse'
    elif 'headset' in category or 'headphone' in category:
        return 'headset'
    elif 'cable' in category:
        return 'cable'
    elif 'charger' in category or 'power' in category:
        return 'charger'
    else:
        return 'accessory'

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
    used_names = set()

    try:
        for h, files in hash_to_files.items():
            # Get sample accessory to identify product type
            sample = files[0]
            acc_id = int(sample.replace('accessory_', '').replace('.jpg', '').replace('.png', '').replace('.gif', ''))
            accessory = session.get(Accessory, acc_id)

            if accessory:
                product_type = identify_product_type(accessory)
            else:
                product_type = 'unknown'

            # Get extension
            ext = sample.split('.')[-1]
            shared_name = f"{product_type}.{ext}"

            # Handle duplicates by adding a number
            counter = 1
            base_name = product_type
            while shared_name in used_names:
                shared_name = f"{base_name}_{counter}.{ext}"
                counter += 1
            used_names.add(shared_name)

            shared_path = os.path.join(SHARED_DIR, shared_name)

            # Copy one file to shared location
            src = os.path.join(UPLOAD_DIR, files[0])
            shutil.copy2(src, shared_path)

            hash_to_shared[h] = f"/static/images/products/shared/{shared_name}"
            print(f"Created: {shared_name} ({len(files)} accessories)")

        # Step 3: Update database with shared image paths
        print("\nUpdating database...")
        updated = 0
        for h, files in hash_to_files.items():
            shared_url = hash_to_shared[h]
            for f in files:
                acc_id = int(f.replace('accessory_', '').replace('.jpg', '').replace('.png', '').replace('.gif', ''))
                accessory = session.get(Accessory, acc_id)
                if accessory and accessory.image_url != shared_url:
                    accessory.image_url = shared_url
                    updated += 1

        session.commit()
        print(f"Updated {updated} accessories to use shared images")

        # Step 4: Remove individual accessory images
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
        print(f"Created {len(hash_to_shared)} shared images")
        print(f"Updated {updated} accessories in database")
        print(f"Removed {removed} duplicate files")

    finally:
        session.close()

if __name__ == '__main__':
    main()
