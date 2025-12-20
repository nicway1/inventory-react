#!/usr/bin/env python3
"""
Script to scrape and download product images for accessories
"""

import os
import re
import requests
import time
import hashlib
from urllib.parse import quote_plus
from database import SessionLocal
from models.accessory import Accessory

# Create uploads directory
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'accessories')
os.makedirs(UPLOAD_DIR, exist_ok=True)

def clean_name(name):
    """Clean accessory name for search"""
    # Remove company names in parentheses
    name = re.sub(r'\([^)]*\)', '', name)
    # Remove extra whitespace
    name = ' '.join(name.split())
    return name.strip()

def get_search_query(accessory):
    """Build search query from accessory info"""
    parts = []

    # Add manufacturer if known
    mfg = accessory.manufacturer or ''
    if mfg and mfg.lower() not in ['no brand', 'none', '']:
        parts.append(mfg)

    # Add model if known
    model = accessory.model_no or ''
    if model and model.lower() not in ['none', '']:
        parts.append(model)

    # Add cleaned name
    name = clean_name(accessory.name)
    parts.append(name)

    query = ' '.join(parts)
    return query

def search_image_duckduckgo(query):
    """Search for image using DuckDuckGo"""
    try:
        search_url = f"https://duckduckgo.com/?q={quote_plus(query + ' product image png')}&iax=images&ia=images"
        # DuckDuckGo doesn't have a simple API, so we'll try a different approach
        return None
    except Exception as e:
        print(f"  Error searching: {e}")
        return None

def search_image_google(query):
    """Try to get image from Google Images (simplified)"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    try:
        # This is a simplified approach - in production you'd use proper API
        search_url = f"https://www.google.com/search?q={quote_plus(query)}&tbm=isch"
        response = requests.get(search_url, headers=headers, timeout=10)
        # Extract first image URL from response (simplified)
        # This won't work reliably - need proper scraping
        return None
    except:
        return None

def get_product_image_url(accessory):
    """Get a product image URL based on manufacturer and product"""
    mfg = (accessory.manufacturer or '').lower()
    name = (accessory.name or '').lower()
    model = (accessory.model_no or '').lower()
    category = (accessory.category or '').lower()

    # Known product image URLs (curated list)
    image_urls = {
        # Logitech products
        'logitech pebble': 'https://resource.logitech.com/content/dam/logitech/en/products/keyboards/pebble-keys-2-k380s/gallery/pebble-keys-2-k380s-gallery-graphite-1.png',
        'logitech lift': 'https://resource.logitech.com/content/dam/logitech/en/products/mice/lift-vertical-ergonomic-mouse/gallery/lift-702x400.png',
        'm720': 'https://resource.logitech.com/content/dam/logitech/en/products/mice/m720-triathlon/gallery/m720-702x400.png',
        'm650': 'https://resource.logitech.com/content/dam/logitech/en/products/mice/signature-m650/gallery/signature-m650-702x400.png',
        'mk120': 'https://resource.logitech.com/content/dam/logitech/en/products/combos/mk120/gallery/mk120-702x400.png',
        'c920': 'https://resource.logitech.com/content/dam/logitech/en/products/webcams/c920e/gallery/c920e-702x400.png',
        'brio 300': 'https://resource.logitech.com/content/dam/logitech/en/products/webcams/brio-300/gallery/brio-300-702x400-graphite.png',
        'zone 300': 'https://resource.logitech.com/content/dam/logitech/en/products/headsets/zone-300/gallery/zone-300-702x400.png',

        # Apple products
        'apple magic mouse': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/MK2C3?wid=400&hei=400',
        'magic mouse': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/MK2C3?wid=400&hei=400',
        'apple magic keyboard': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/MK293?wid=400&hei=400',
        'magic keyboard': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/MK293?wid=400&hei=400',
        'apple earpods': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/MTJY3?wid=400&hei=400',
        'usb-c digital av': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/MUF82?wid=400&hei=400',
        'multiport adapter': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/MUF82?wid=400&hei=400',

        # Anker products
        'anker 736': 'https://m.media-amazon.com/images/I/51agsNn054L._AC_SL1500_.jpg',
        'anker 30w': 'https://m.media-amazon.com/images/I/51Uj9K5hH0L._AC_SL1500_.jpg',
        'anker charger': 'https://m.media-amazon.com/images/I/51agsNn054L._AC_SL1500_.jpg',

        # Dell products
        'dell p2425h': 'https://i.dell.com/is/image/DellContent/content/dam/ss2/product-images/dell-client-products/peripherals/monitors/p-series/p2425h/media-gallery/monitor-p2425h-black-gallery-1.psd?fmt=png-alpha&wid=400',
        'dell wd19': 'https://i.dell.com/is/image/DellContent/content/dam/ss2/product-images/dell-client-products/peripherals/docking-stations/wd19/media-gallery/peripherals-docking-station-wd19-gallery-1.psd?fmt=png-alpha&wid=400',
        'dell wh1022': 'https://i.dell.com/is/image/DellContent/content/dam/ss2/product-images/dell-client-products/peripherals/headsets/wh1022/media-gallery/peripherals-headset-wh1022-gallery-1.psd?fmt=png-alpha&wid=400',
        'dell ms116': 'https://i.dell.com/is/image/DellContent/content/dam/ss2/product-images/dell-client-products/peripherals/mice/ms116/media-gallery/peripherals-mouse-ms116-gallery-1.psd?fmt=png-alpha&wid=400',
        'dell mobile wireless': 'https://i.dell.com/is/image/DellContent/content/dam/ss2/product-images/dell-client-products/peripherals/mice/ms3320w/media-gallery/peripherals-mouse-ms3320w-gallery-1.psd?fmt=png-alpha&wid=400',

        # Jabra products
        'jabra evolve2 40': 'https://www.jabra.com/-/media/Images/Products/Jabra-Evolve2-40/Product-images/evolve2-40-front.png?w=400',
        'jabra evolve2 50': 'https://www.jabra.com/-/media/Images/Products/Jabra-Evolve2-50/Product-images/evolve2-50-front.png?w=400',
        'jabra evolve2 65': 'https://www.jabra.com/-/media/Images/Products/Jabra-Evolve2-65-Flex/Product-images/evolve2-65-flex-front.png?w=400',
        'jabra evolve2 75': 'https://www.jabra.com/-/media/Images/Products/Jabra-Evolve2-75/Product-images/evolve2-75-front.png?w=400',
        'evolve 2 40': 'https://www.jabra.com/-/media/Images/Products/Jabra-Evolve2-40/Product-images/evolve2-40-front.png?w=400',
        'evolve 2 50': 'https://www.jabra.com/-/media/Images/Products/Jabra-Evolve2-50/Product-images/evolve2-50-front.png?w=400',
        'evolve 2 75': 'https://www.jabra.com/-/media/Images/Products/Jabra-Evolve2-75/Product-images/evolve2-75-front.png?w=400',
        'evolve 240': 'https://www.jabra.com/-/media/Images/Products/Jabra-Evolve-40/Product-images/evolve-40-front.png?w=400',
        'evolve 275': 'https://www.jabra.com/-/media/Images/Products/Jabra-Evolve-75/Product-images/evolve-75-front.png?w=400',

        # YubiKey products
        'yubikey 5c nano': 'https://www.yubico.com/wp-content/uploads/2022/12/YubiKey-5C-Nano-Front.png',
        'yubikey 5c nfc': 'https://www.yubico.com/wp-content/uploads/2022/12/YubiKey-5C-NFC-Front.png',
        'yubi 5c': 'https://www.yubico.com/wp-content/uploads/2022/12/YubiKey-5C-NFC-Front.png',

        # Lenovo products
        'lenovo thunderbolt': 'https://p1-ofp.static.pub/fes/cms/2022/04/14/qwb9rvt6n9xhxzq4jcvx94yxafqz6k238519.png',
        'thinkpad thunderbolt': 'https://p1-ofp.static.pub/fes/cms/2022/04/14/qwb9rvt6n9xhxzq4jcvx94yxafqz6k238519.png',
        'lenovo preferred pro': 'https://p1-ofp.static.pub/fes/cms/2022/02/14/m5w1mlmv5v5yt0xmixf8z2u7yqhz6v815481.png',
        'lenovo essential usb': 'https://p1-ofp.static.pub/fes/cms/2022/02/14/m5w1mlmv5v5yt0xmixf8z2u7yqhz6v815481.png',

        # ASUS products
        'asus tuf gaming k1': 'https://dlcdnwebimgs.asus.com/gain/85f9ca89-2da6-4d0e-9c9b-ab19b60d7d4f/w400',
        'asus tuf gaming m3': 'https://dlcdnwebimgs.asus.com/gain/6f5d6f9a-d5a4-4f4e-9ebb-7c5d5a0f5f5f/w400',

        # Belkin products
        'belkin usb-c': 'https://www.belkin.com/dw/image/v2/BGBF_PRD/on/demandware.static/-/Sites-master-product-catalog-blk/default/dw3e3f3c3e/images/hi-res/cab015bt2mbk/cab015bt2mbk-hero.png?sw=400',
        'belkin boostcharge': 'https://www.belkin.com/dw/image/v2/BGBF_PRD/on/demandware.static/-/Sites-master-product-catalog-blk/default/dw3e3f3c3e/images/hi-res/cab015bt2mbk/cab015bt2mbk-hero.png?sw=400',

        # 3M Privacy screens
        '3m privacy': 'https://multimedia.3m.com/mws/media/1936641P/3m-bright-screen-privacy-filter.png?width=400',
        'privacy screen': 'https://multimedia.3m.com/mws/media/1936641P/3m-bright-screen-privacy-filter.png?width=400',

        # Plantronics
        'plantronics': 'https://www.poly.com/content/dam/www/products/headsets/blackwire-5200/images/blackwire-5200-series.png',
        'black wire': 'https://www.poly.com/content/dam/www/products/headsets/blackwire-5200/images/blackwire-5200-series.png',

        # Generic categories
        'usb-c cable': 'https://m.media-amazon.com/images/I/61ni3t1ryQL._AC_SL1500_.jpg',
        'usb c cable': 'https://m.media-amazon.com/images/I/61ni3t1ryQL._AC_SL1500_.jpg',
        'travel adapter': 'https://m.media-amazon.com/images/I/61TQrF9vKKL._AC_SL1500_.jpg',
        'power cord': 'https://m.media-amazon.com/images/I/51hnXrO8B7L._AC_SL1000_.jpg',
        'laptop stand': 'https://m.media-amazon.com/images/I/61KDBs+tNtL._AC_SL1500_.jpg',
        'webcam': 'https://resource.logitech.com/content/dam/logitech/en/products/webcams/c920e/gallery/c920e-702x400.png',
        'earpads': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/MTJY3?wid=400&hei=400',
        'earphone': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/MTJY3?wid=400&hei=400',
    }

    # Search through our curated list
    search_text = f"{mfg} {name} {model}".lower()

    for key, url in image_urls.items():
        if key in search_text:
            return url

    # Fallback based on category
    category_images = {
        'keyboard': 'https://resource.logitech.com/content/dam/logitech/en/products/keyboards/pebble-keys-2-k380s/gallery/pebble-keys-2-k380s-gallery-graphite-1.png',
        'mouse': 'https://resource.logitech.com/content/dam/logitech/en/products/mice/m720-triathlon/gallery/m720-702x400.png',
        'monitor': 'https://i.dell.com/is/image/DellContent/content/dam/ss2/product-images/dell-client-products/peripherals/monitors/p-series/p2425h/media-gallery/monitor-p2425h-black-gallery-1.psd?fmt=png-alpha&wid=400',
        'docking': 'https://p1-ofp.static.pub/fes/cms/2022/04/14/qwb9rvt6n9xhxzq4jcvx94yxafqz6k238519.png',
        'headset': 'https://www.jabra.com/-/media/Images/Products/Jabra-Evolve2-50/Product-images/evolve2-50-front.png?w=400',
        'headphone': 'https://www.jabra.com/-/media/Images/Products/Jabra-Evolve2-50/Product-images/evolve2-50-front.png?w=400',
        'cable': 'https://m.media-amazon.com/images/I/61ni3t1ryQL._AC_SL1500_.jpg',
        'charger': 'https://m.media-amazon.com/images/I/51agsNn054L._AC_SL1500_.jpg',
        'adapter': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/MUF82?wid=400&hei=400',
        'power': 'https://m.media-amazon.com/images/I/51agsNn054L._AC_SL1500_.jpg',
        'screen protector': 'https://multimedia.3m.com/mws/media/1936641P/3m-bright-screen-privacy-filter.png?width=400',
    }

    for cat_key, url in category_images.items():
        if cat_key in category:
            return url

    return None

def download_image(url, accessory_id):
    """Download image and save locally"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            # Determine file extension
            content_type = response.headers.get('content-type', '')
            if 'png' in content_type or url.endswith('.png'):
                ext = 'png'
            elif 'gif' in content_type or url.endswith('.gif'):
                ext = 'gif'
            else:
                ext = 'jpg'

            filename = f"accessory_{accessory_id}.{ext}"
            filepath = os.path.join(UPLOAD_DIR, filename)

            with open(filepath, 'wb') as f:
                f.write(response.content)

            return f"/static/uploads/accessories/{filename}"
    except Exception as e:
        print(f"  Error downloading: {e}")
    return None

def main():
    session = SessionLocal()

    try:
        accessories = session.query(Accessory).all()
        print(f"Found {len(accessories)} accessories")

        updated = 0
        for acc in accessories:
            print(f"\n[{acc.id}] {acc.name}")

            # Skip if already has custom image
            if acc.image_url and '/uploads/' in acc.image_url:
                print(f"  Already has custom image: {acc.image_url}")
                continue

            # Get product image URL
            image_url = get_product_image_url(acc)

            if image_url:
                print(f"  Found image: {image_url[:60]}...")

                # Download and save locally
                local_path = download_image(image_url, acc.id)

                if local_path:
                    acc.image_url = local_path
                    updated += 1
                    print(f"  Saved to: {local_path}")
                else:
                    print(f"  Failed to download")
            else:
                print(f"  No image found")

            # Rate limiting
            time.sleep(0.5)

        session.commit()
        print(f"\n\nUpdated {updated} accessories with images")

    finally:
        session.close()

if __name__ == '__main__':
    main()
