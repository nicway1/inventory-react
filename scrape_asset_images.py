#!/usr/bin/env python3
"""
Script to scrape and download product images for tech assets (MacBooks, laptops, etc.)
"""

import os
import re
import requests
import time
from database import SessionLocal
from models.asset import Asset

# Create uploads directory
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'assets')
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_product_image_url(asset):
    """Get a product image URL based on manufacturer and model"""
    mfg = (asset.manufacturer or '').lower()
    model = (asset.model or '').lower()
    name = (asset.name or '').lower()
    category = (asset.category or '').lower()

    # Combine for searching
    search_text = f"{mfg} {model} {name}".lower()

    # Known product image URLs (curated list)
    image_urls = {
        # Apple MacBooks
        'macbook pro 14': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/mbp14-spacegray-select-202310?wid=400&hei=400&fmt=jpeg',
        'macbook pro 16': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/mbp16-spacegray-select-202310?wid=400&hei=400&fmt=jpeg',
        'macbook pro 13': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/mbp-spacegray-select-202206?wid=400&hei=400&fmt=jpeg',
        'macbook air 15': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/mba15-midnight-select-202306?wid=400&hei=400&fmt=jpeg',
        'macbook air 13': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/mba13-midnight-select-202402?wid=400&hei=400&fmt=jpeg',
        'macbook air m3': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/mba13-midnight-select-202402?wid=400&hei=400&fmt=jpeg',
        'macbook air m2': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/mba13-midnight-select-202306?wid=400&hei=400&fmt=jpeg',
        'macbook air m1': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/macbook-air-space-gray-select-201810?wid=400&hei=400&fmt=jpeg',
        'macbook pro m3': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/mbp14-spacegray-select-202310?wid=400&hei=400&fmt=jpeg',
        'macbook pro m2': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/mbp-spacegray-select-202206?wid=400&hei=400&fmt=jpeg',
        'macbook pro m1': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/mbp-spacegray-select-202011?wid=400&hei=400&fmt=jpeg',

        # Generic MacBook fallbacks
        'macbook pro': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/mbp14-spacegray-select-202310?wid=400&hei=400&fmt=jpeg',
        'macbook air': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/mba13-midnight-select-202402?wid=400&hei=400&fmt=jpeg',
        'macbook': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/mbp14-spacegray-select-202310?wid=400&hei=400&fmt=jpeg',

        # iMac
        'imac 24': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/imac-24-blue-selection-hero-202310?wid=400&hei=400&fmt=jpeg',
        'imac': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/imac-24-blue-selection-hero-202310?wid=400&hei=400&fmt=jpeg',

        # Mac Studio / Mac Mini / Mac Pro
        'mac studio': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/mac-studio-select-202306?wid=400&hei=400&fmt=jpeg',
        'mac mini': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/mac-mini-hero-202301?wid=400&hei=400&fmt=jpeg',
        'mac pro': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/mac-pro-tower-select-202306?wid=400&hei=400&fmt=jpeg',

        # iPhone models
        'iphone 15 pro max': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/iphone-15-pro-max-black-titanium-select?wid=400&hei=400&fmt=jpeg',
        'iphone 15 pro': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/iphone-15-pro-black-titanium-select?wid=400&hei=400&fmt=jpeg',
        'iphone 15 plus': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/iphone-15-plus-black-select?wid=400&hei=400&fmt=jpeg',
        'iphone 15': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/iphone-15-black-select?wid=400&hei=400&fmt=jpeg',
        'iphone 14 pro max': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/iphone-14-pro-max-deep-purple-select?wid=400&hei=400&fmt=jpeg',
        'iphone 14 pro': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/iphone-14-pro-deep-purple-select?wid=400&hei=400&fmt=jpeg',
        'iphone 14': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/iphone-14-midnight-select?wid=400&hei=400&fmt=jpeg',
        'iphone 13': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/iphone-13-midnight-select?wid=400&hei=400&fmt=jpeg',
        'iphone 12': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/iphone-12-black-select?wid=400&hei=400&fmt=jpeg',
        'iphone 11': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/iphone-11-black-select?wid=400&hei=400&fmt=jpeg',
        'iphone se': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/iphone-se-midnight-select?wid=400&hei=400&fmt=jpeg',
        'iphone': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/iphone-15-black-select?wid=400&hei=400&fmt=jpeg',

        # iPad models
        'ipad pro 12.9': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/ipad-pro-13-select-wifi-spacegray-202405?wid=400&hei=400&fmt=jpeg',
        'ipad pro 11': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/ipad-pro-11-select-wifi-spacegray-202405?wid=400&hei=400&fmt=jpeg',
        'ipad pro': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/ipad-pro-13-select-wifi-spacegray-202405?wid=400&hei=400&fmt=jpeg',
        'ipad air': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/ipad-air-select-wifi-spacegray-202405?wid=400&hei=400&fmt=jpeg',
        'ipad mini': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/ipad-mini-select-wifi-spacegray-202109?wid=400&hei=400&fmt=jpeg',
        'ipad': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/ipad-10th-gen-wifi-blue-select?wid=400&hei=400&fmt=jpeg',

        # Apple Watch
        'apple watch ultra': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/watch-ultra-2-702x400?wid=400&hei=400&fmt=jpeg',
        'apple watch series 9': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/watch-s9-702x400?wid=400&hei=400&fmt=jpeg',
        'apple watch': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/watch-s9-702x400?wid=400&hei=400&fmt=jpeg',

        # Lenovo ThinkPad models
        'thinkpad x1 carbon': 'https://p1-ofp.static.pub/fes/cms/2023/08/08/jyf3q5ljxs1mvkxf2xqd2vy0tqz05r604157.png',
        'thinkpad x1 yoga': 'https://p1-ofp.static.pub/fes/cms/2023/08/08/4i8z5kq9b1q4j1p6pqk0ljl4xk7z8s108924.png',
        'thinkpad t14': 'https://p1-ofp.static.pub/fes/cms/2023/01/19/5g1u1h7j5zv1z1f6xq5x5x5x5x5x5x803125.png',
        'thinkpad t15': 'https://p1-ofp.static.pub/fes/cms/2022/09/29/fwj3c8qgb3sn6y7o1i4a5i7xfxtjdg389620.png',
        'thinkpad t480': 'https://p1-ofp.static.pub/fes/cms/2021/05/20/thinkpad-t14-702x400.png',
        'thinkpad t490': 'https://p1-ofp.static.pub/fes/cms/2021/05/20/thinkpad-t14-702x400.png',
        'thinkpad e14': 'https://p1-ofp.static.pub/fes/cms/2023/01/19/thinkpad-e14-702x400.png',
        'thinkpad e15': 'https://p1-ofp.static.pub/fes/cms/2023/01/19/thinkpad-e15-702x400.png',
        'thinkpad l14': 'https://p1-ofp.static.pub/fes/cms/2022/09/06/thinkpad-l14-702x400.png',
        'thinkpad p14s': 'https://p1-ofp.static.pub/fes/cms/2023/01/19/thinkpad-p14s-702x400.png',
        'thinkpad p16': 'https://p1-ofp.static.pub/fes/cms/2023/01/19/thinkpad-p16-702x400.png',
        'thinkpad': 'https://p1-ofp.static.pub/fes/cms/2023/08/08/jyf3q5ljxs1mvkxf2xqd2vy0tqz05r604157.png',

        # Lenovo IdeaPad
        'ideapad': 'https://p1-ofp.static.pub/fes/cms/2023/05/02/ideapad-slim-5-702x400.png',
        'lenovo yoga': 'https://p1-ofp.static.pub/fes/cms/2023/08/08/4i8z5kq9b1q4j1p6pqk0ljl4xk7z8s108924.png',
        'lenovo legion': 'https://p1-ofp.static.pub/fes/cms/2023/01/19/legion-pro-702x400.png',

        # Dell models
        'latitude 7420': 'https://i.dell.com/is/image/DellContent/content/dam/ss2/product-images/dell-client-products/notebooks/latitude-notebooks/latitude-14-7420/media-gallery/laptop-latitude-14-7420-702x400.psd?fmt=png-alpha&wid=400',
        'latitude 7430': 'https://i.dell.com/is/image/DellContent/content/dam/ss2/product-images/dell-client-products/notebooks/latitude-notebooks/latitude-14-7430/media-gallery/laptop-latitude-14-7430-702x400.psd?fmt=png-alpha&wid=400',
        'latitude 7440': 'https://i.dell.com/is/image/DellContent/content/dam/ss2/product-images/dell-client-products/notebooks/latitude-notebooks/latitude-14-7440/media-gallery/laptop-latitude-14-7440-702x400.psd?fmt=png-alpha&wid=400',
        'latitude 5420': 'https://i.dell.com/is/image/DellContent/content/dam/ss2/product-images/dell-client-products/notebooks/latitude-notebooks/latitude-14-5420/media-gallery/laptop-latitude-14-5420-702x400.psd?fmt=png-alpha&wid=400',
        'latitude 5520': 'https://i.dell.com/is/image/DellContent/content/dam/ss2/product-images/dell-client-products/notebooks/latitude-notebooks/latitude-15-5520/media-gallery/laptop-latitude-15-5520-702x400.psd?fmt=png-alpha&wid=400',
        'latitude 5540': 'https://i.dell.com/is/image/DellContent/content/dam/ss2/product-images/dell-client-products/notebooks/latitude-notebooks/latitude-15-5540/media-gallery/laptop-latitude-15-5540-702x400.psd?fmt=png-alpha&wid=400',
        'latitude': 'https://i.dell.com/is/image/DellContent/content/dam/ss2/product-images/dell-client-products/notebooks/latitude-notebooks/latitude-14-7440/media-gallery/laptop-latitude-14-7440-702x400.psd?fmt=png-alpha&wid=400',

        'xps 13': 'https://i.dell.com/is/image/DellContent/content/dam/ss2/product-images/dell-client-products/notebooks/xps-notebooks/xps-13-9340/media-gallery/touch/notebook-xps-13-9340-702x400.psd?fmt=png-alpha&wid=400',
        'xps 15': 'https://i.dell.com/is/image/DellContent/content/dam/ss2/product-images/dell-client-products/notebooks/xps-notebooks/xps-15-9530/media-gallery/notebook-xps-15-9530-702x400.psd?fmt=png-alpha&wid=400',
        'xps 17': 'https://i.dell.com/is/image/DellContent/content/dam/ss2/product-images/dell-client-products/notebooks/xps-notebooks/xps-17-9730/media-gallery/notebook-xps-17-9730-702x400.psd?fmt=png-alpha&wid=400',
        'xps': 'https://i.dell.com/is/image/DellContent/content/dam/ss2/product-images/dell-client-products/notebooks/xps-notebooks/xps-13-9340/media-gallery/touch/notebook-xps-13-9340-702x400.psd?fmt=png-alpha&wid=400',

        'precision 5570': 'https://i.dell.com/is/image/DellContent/content/dam/ss2/product-images/dell-client-products/notebooks/precision-mobile-workstations/precision-15-5570/media-gallery/notebook-precision-5570-702x400.psd?fmt=png-alpha&wid=400',
        'precision': 'https://i.dell.com/is/image/DellContent/content/dam/ss2/product-images/dell-client-products/notebooks/precision-mobile-workstations/precision-15-5570/media-gallery/notebook-precision-5570-702x400.psd?fmt=png-alpha&wid=400',

        'optiplex': 'https://i.dell.com/is/image/DellContent/content/dam/ss2/product-images/dell-client-products/desktops/optiplex-desktops/optiplex-7010-702x400.psd?fmt=png-alpha&wid=400',

        # HP models
        'elitebook 840': 'https://www.hp.com/content/dam/sites/worldwide/personal-computers/notebooks/elitebook-840-g10/elitebook-840-702x400.png',
        'elitebook 850': 'https://www.hp.com/content/dam/sites/worldwide/personal-computers/notebooks/elitebook-850-g10/elitebook-850-702x400.png',
        'elitebook 860': 'https://www.hp.com/content/dam/sites/worldwide/personal-computers/notebooks/elitebook-860-g10/elitebook-860-702x400.png',
        'elitebook x360': 'https://www.hp.com/content/dam/sites/worldwide/personal-computers/notebooks/elitebook-x360-1040-g10/elitebook-x360-1040-702x400.png',
        'elitebook': 'https://www.hp.com/content/dam/sites/worldwide/personal-computers/notebooks/elitebook-840-g10/elitebook-840-702x400.png',

        'probook 450': 'https://www.hp.com/content/dam/sites/worldwide/personal-computers/notebooks/probook-450-g10/probook-450-702x400.png',
        'probook 640': 'https://www.hp.com/content/dam/sites/worldwide/personal-computers/notebooks/probook-640-g9/probook-640-702x400.png',
        'probook': 'https://www.hp.com/content/dam/sites/worldwide/personal-computers/notebooks/probook-450-g10/probook-450-702x400.png',

        'zbook studio': 'https://www.hp.com/content/dam/sites/worldwide/personal-computers/notebooks/zbook-studio-g10/zbook-studio-702x400.png',
        'zbook fury': 'https://www.hp.com/content/dam/sites/worldwide/personal-computers/notebooks/zbook-fury-16-g10/zbook-fury-16-702x400.png',
        'zbook': 'https://www.hp.com/content/dam/sites/worldwide/personal-computers/notebooks/zbook-studio-g10/zbook-studio-702x400.png',

        'hp spectre': 'https://www.hp.com/content/dam/sites/worldwide/personal-computers/notebooks/spectre-x360-16/spectre-x360-16-702x400.png',
        'hp envy': 'https://www.hp.com/content/dam/sites/worldwide/personal-computers/notebooks/envy-x360-15/envy-x360-15-702x400.png',
        'hp pavilion': 'https://www.hp.com/content/dam/sites/worldwide/personal-computers/notebooks/pavilion-15/pavilion-15-702x400.png',

        # Microsoft Surface
        'surface pro 9': 'https://img-prod-cms-rt-microsoft-com.akamaized.net/cms/api/am/imageFileData/RWYmrq?ver=cf6e&q=90&m=6&h=400&w=400',
        'surface pro 8': 'https://img-prod-cms-rt-microsoft-com.akamaized.net/cms/api/am/imageFileData/RWYmrq?ver=cf6e&q=90&m=6&h=400&w=400',
        'surface pro 7': 'https://img-prod-cms-rt-microsoft-com.akamaized.net/cms/api/am/imageFileData/RWYmrq?ver=cf6e&q=90&m=6&h=400&w=400',
        'surface pro': 'https://img-prod-cms-rt-microsoft-com.akamaized.net/cms/api/am/imageFileData/RWYmrq?ver=cf6e&q=90&m=6&h=400&w=400',
        'surface laptop 5': 'https://img-prod-cms-rt-microsoft-com.akamaized.net/cms/api/am/imageFileData/RWZ6O9?ver=ade5&q=90&m=6&h=400&w=400',
        'surface laptop 4': 'https://img-prod-cms-rt-microsoft-com.akamaized.net/cms/api/am/imageFileData/RWZ6O9?ver=ade5&q=90&m=6&h=400&w=400',
        'surface laptop': 'https://img-prod-cms-rt-microsoft-com.akamaized.net/cms/api/am/imageFileData/RWZ6O9?ver=ade5&q=90&m=6&h=400&w=400',
        'surface book': 'https://img-prod-cms-rt-microsoft-com.akamaized.net/cms/api/am/imageFileData/RW15bdR?ver=ed5b&q=90&m=6&h=400&w=400',
        'surface go': 'https://img-prod-cms-rt-microsoft-com.akamaized.net/cms/api/am/imageFileData/RWBByY?ver=c6c4&q=90&m=6&h=400&w=400',
        'surface studio': 'https://img-prod-cms-rt-microsoft-com.akamaized.net/cms/api/am/imageFileData/RWF0Pt?ver=a40c&q=90&m=6&h=400&w=400',
        'surface': 'https://img-prod-cms-rt-microsoft-com.akamaized.net/cms/api/am/imageFileData/RWYmrq?ver=cf6e&q=90&m=6&h=400&w=400',

        # ASUS laptops
        'asus zenbook': 'https://dlcdnwebimgs.asus.com/gain/e92c4a3d-3f5e-4f8a-9a6a-8d3e3e3e3e3e/w400',
        'asus vivobook': 'https://dlcdnwebimgs.asus.com/gain/f0f0f0f0-3f5e-4f8a-9a6a-8d3e3e3e3e3e/w400',
        'asus rog': 'https://dlcdnwebimgs.asus.com/gain/d1d1d1d1-3f5e-4f8a-9a6a-8d3e3e3e3e3e/w400',
        'asus tuf': 'https://dlcdnwebimgs.asus.com/gain/c2c2c2c2-3f5e-4f8a-9a6a-8d3e3e3e3e3e/w400',
        'asus': 'https://dlcdnwebimgs.asus.com/gain/e92c4a3d-3f5e-4f8a-9a6a-8d3e3e3e3e3e/w400',

        # Acer laptops
        'acer aspire': 'https://static.acer.com/up/Resource/Acer/Laptops/Aspire_5/Images/20230602/Aspire-5-702x400.png',
        'acer swift': 'https://static.acer.com/up/Resource/Acer/Laptops/Swift_5/Images/20230602/Swift-5-702x400.png',
        'acer predator': 'https://static.acer.com/up/Resource/Acer/Laptops/Predator_Helios/Images/20230602/Predator-Helios-702x400.png',
        'acer': 'https://static.acer.com/up/Resource/Acer/Laptops/Aspire_5/Images/20230602/Aspire-5-702x400.png',

        # Monitors
        'dell monitor': 'https://i.dell.com/is/image/DellContent/content/dam/ss2/product-images/dell-client-products/peripherals/monitors/p-series/p2425h/media-gallery/monitor-p2425h-black-gallery-1.psd?fmt=png-alpha&wid=400',
        'lg monitor': 'https://www.lg.com/content/dam/channel/wcms/sg/images/monitors/27uk850-w/gallery/lg-monitor-27uk850-702x400.png',
        'samsung monitor': 'https://images.samsung.com/is/image/samsung/p6pim/sg/ls27a600uuexxs/gallery/sg-odyssey-g5-s27ag500-ls27a600uuexxs-front-black-thumb-492274913?$730_584_PNG$',
    }

    # Search through our curated list (more specific first)
    for key, url in image_urls.items():
        if key in search_text:
            return url

    # Fallback based on manufacturer
    mfg_fallbacks = {
        'apple': 'https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/mbp14-spacegray-select-202310?wid=400&hei=400&fmt=jpeg',
        'lenovo': 'https://p1-ofp.static.pub/fes/cms/2023/08/08/jyf3q5ljxs1mvkxf2xqd2vy0tqz05r604157.png',
        'dell': 'https://i.dell.com/is/image/DellContent/content/dam/ss2/product-images/dell-client-products/notebooks/latitude-notebooks/latitude-14-7440/media-gallery/laptop-latitude-14-7440-702x400.psd?fmt=png-alpha&wid=400',
        'hp': 'https://www.hp.com/content/dam/sites/worldwide/personal-computers/notebooks/elitebook-840-g10/elitebook-840-702x400.png',
        'microsoft': 'https://img-prod-cms-rt-microsoft-com.akamaized.net/cms/api/am/imageFileData/RWYmrq?ver=cf6e&q=90&m=6&h=400&w=400',
        'asus': 'https://dlcdnwebimgs.asus.com/gain/e92c4a3d-3f5e-4f8a-9a6a-8d3e3e3e3e3e/w400',
        'acer': 'https://static.acer.com/up/Resource/Acer/Laptops/Aspire_5/Images/20230602/Aspire-5-702x400.png',
    }

    for mfg_key, url in mfg_fallbacks.items():
        if mfg_key in mfg:
            return url

    return None


def download_image(url, asset_id):
    """Download image and save locally"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
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

            filename = f"asset_{asset_id}.{ext}"
            filepath = os.path.join(UPLOAD_DIR, filename)

            with open(filepath, 'wb') as f:
                f.write(response.content)

            return f"/static/uploads/assets/{filename}"
    except Exception as e:
        print(f"  Error downloading: {e}")
    return None


def main():
    session = SessionLocal()

    try:
        assets = session.query(Asset).all()
        print(f"Found {len(assets)} assets")

        updated = 0
        skipped = 0
        failed = 0

        for asset in assets:
            print(f"\n[{asset.id}] {asset.name or 'Unknown'} - {asset.model or 'No model'}")

            # Skip if already has custom image
            if asset.image_url and '/uploads/' in asset.image_url:
                print(f"  Already has custom image: {asset.image_url}")
                skipped += 1
                continue

            # Get product image URL
            image_url = get_product_image_url(asset)

            if image_url:
                print(f"  Found image: {image_url[:60]}...")

                # Download and save locally
                local_path = download_image(image_url, asset.id)

                if local_path:
                    asset.image_url = local_path
                    updated += 1
                    print(f"  Saved to: {local_path}")
                else:
                    print(f"  Failed to download")
                    failed += 1
            else:
                print(f"  No image found for this asset")
                failed += 1

            # Rate limiting
            time.sleep(0.3)

        session.commit()
        print(f"\n\n=== Summary ===")
        print(f"Updated: {updated} assets with images")
        print(f"Skipped: {skipped} (already had images)")
        print(f"Failed:  {failed} (no image found or download failed)")

    finally:
        session.close()


if __name__ == '__main__':
    main()
