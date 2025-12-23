"""
PDF Asset Extractor
Extracts asset information from packing list PDFs for automatic asset creation
"""
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def extract_assets_from_pdf(pdf_path):
    """
    Extract asset information from a packing list PDF

    Returns:
        dict with:
            - po_number: PO number from the document
            - reference: Reference number
            - ship_date: Shipping date
            - supplier: Supplier name
            - receiver: Receiver name
            - total_quantity: Total items expected
            - assets: List of extracted assets with serial numbers and details
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.error("PyMuPDF (fitz) not installed")
        return None

    try:
        doc = fitz.open(pdf_path)
        all_text = ""

        # Extract text from all pages
        for page in doc:
            all_text += page.get_text() + "\n"

        doc.close()

        # Parse the extracted text
        return parse_packing_list_text(all_text)

    except Exception as e:
        logger.error(f"Error extracting PDF: {e}")
        return None


def parse_packing_list_text(text):
    """
    Parse packing list text and extract asset information
    """
    result = {
        'po_number': None,
        'reference': None,
        'ship_date': None,
        'supplier': None,
        'receiver': None,
        'total_quantity': 0,
        'assets': [],
        'raw_text': text[:2000]  # First 2000 chars for debugging
    }

    lines = text.split('\n')

    # Extract PO number (look for patterns like "PO nr" or "100010948 WISE")
    po_patterns = [
        r'PO\s*n[ro]?[:\s]*(\d+\s*\w*)',
        r'PO\s*Number[:\s]*(\d+\s*\w*)',
        r'(\d{9,}\s*WISE)',  # Pattern like "100010948 WISE"
    ]
    for pattern in po_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['po_number'] = match.group(1).strip()
            break

    # Extract Reference number
    ref_patterns = [
        r'Reference[:\s#]*(\d+)',
        r'REFERENCE[:\s#]*(\d+)',
        r'Collection\s*ref[:\s]*(\d+)',
    ]
    for pattern in ref_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['reference'] = match.group(1).strip()
            break

    # Extract ship date
    date_patterns = [
        r'Ship\s*date[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        r'DATE[:\s]*(\d{1,2}[-/]\w+[-/]\d{2,4})',
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['ship_date'] = match.group(1).strip()
            break

    # Extract total quantity
    qty_patterns = [
        r'Deconsolidated\s*quantity[:\s]*(\d+)',
        r'Total\s*quantity[:\s]*(\d+)',
        r'(\d+)\s*PCS',
    ]
    for pattern in qty_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['total_quantity'] = int(match.group(1))
            break

    # Extract assets - look for serial numbers and product descriptions
    assets = extract_assets_from_text(text)
    result['assets'] = assets

    if not result['total_quantity'] and assets:
        result['total_quantity'] = len(assets)

    return result


def extract_assets_from_text(text):
    """
    Extract individual assets with serial numbers from text
    """
    assets = []

    # Common Apple serial number patterns (alphanumeric, 10-12 chars)
    # Looking for patterns like: SF54Y0MR211, SK12L1QP79D, etc.
    serial_pattern = r'\b([A-Z0-9]{10,14})\b'

    # Find product description patterns
    # Pattern: MWW03ZP/A-SG0001 or similar Apple part numbers
    part_number_pattern = r'\b([A-Z]{2,4}\d{2,3}[A-Z]{2}/[A-Z]-[A-Z]{2}\d{4})\b'

    # Look for product descriptions
    product_patterns = [
        r'APPLE\s+\d+["\']?\s*MACBOOK\s+AIR[^,\n]*',
        r'APPLE\s+\d+["\']?\s*MACBOOK\s+PRO[^,\n]*',
        r'MACBOOK\s+AIR[^,\n]*M\d+[^,\n]*',
        r'MACBOOK\s+PRO[^,\n]*M\d+[^,\n]*',
    ]

    # Extract product info
    product_name = None
    part_number = None

    # Find part number
    part_match = re.search(part_number_pattern, text)
    if part_match:
        part_number = part_match.group(1)

    # Find product description
    for pattern in product_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            product_name = match.group(0).strip()
            break

    # Parse product details from description
    product_details = parse_product_description(product_name or "")

    # Find all serial numbers
    # Filter out common non-serial patterns
    exclude_patterns = [
        r'^\d+$',  # Pure numbers
        r'^100\d{7}',  # PO numbers
        r'^847\d{5}',  # Commodity codes
        r'^656\d{8}',  # Tracking numbers
    ]

    # Get all potential serials
    potential_serials = re.findall(serial_pattern, text)

    # Filter serials
    serial_numbers = []
    seen = set()
    for serial in potential_serials:
        # Skip if matches exclude patterns
        skip = False
        for exc_pattern in exclude_patterns:
            if re.match(exc_pattern, serial):
                skip = True
                break

        if skip:
            continue

        # Skip duplicates
        if serial in seen:
            continue
        seen.add(serial)

        # Skip if too short or all numbers
        if len(serial) < 10 or serial.isdigit():
            continue

        # Must have mix of letters and numbers for Apple serials
        has_letters = any(c.isalpha() for c in serial)
        has_numbers = any(c.isdigit() for c in serial)
        if has_letters and has_numbers:
            serial_numbers.append(serial)

    # Create asset entries for each serial
    for serial in serial_numbers:
        asset = {
            'serial_num': serial,
            'name': product_details.get('name', 'MacBook'),
            'model': part_number or product_details.get('model', ''),
            'manufacturer': 'Apple',
            'category': 'Laptop',
            'cpu_type': product_details.get('cpu_type', ''),
            'cpu_cores': product_details.get('cpu_cores', ''),
            'gpu_cores': product_details.get('gpu_cores', ''),
            'memory': product_details.get('memory', ''),
            'harddrive': product_details.get('storage', ''),
            'hardware_type': 'Laptop',
            'condition': 'New',
        }
        assets.append(asset)

    return assets


def parse_product_description(description):
    """
    Parse product description to extract specs
    e.g., "APPLE 13" MACBOOK AIR M4 10C CPU 8C GPU 16GB 256GB - SILVER"
    """
    details = {
        'name': '',
        'model': '',
        'cpu_type': '',
        'cpu_cores': '',
        'gpu_cores': '',
        'memory': '',
        'storage': '',
        'color': '',
    }

    if not description:
        return details

    desc_upper = description.upper()

    # Extract product name
    if 'MACBOOK AIR' in desc_upper:
        details['name'] = 'MacBook Air'
        details['model'] = 'MacBook Air'
    elif 'MACBOOK PRO' in desc_upper:
        details['name'] = 'MacBook Pro'
        details['model'] = 'MacBook Pro'
    elif 'MACBOOK' in desc_upper:
        details['name'] = 'MacBook'
        details['model'] = 'MacBook'

    # Extract screen size
    size_match = re.search(r'(\d+)["\']', description)
    if size_match:
        details['name'] = f'{size_match.group(1)}" {details["name"]}'

    # Extract CPU type (M1, M2, M3, M4, etc.)
    cpu_match = re.search(r'\b(M\d+)\b', desc_upper)
    if cpu_match:
        details['cpu_type'] = cpu_match.group(1)

    # Extract CPU cores
    cpu_cores_match = re.search(r'(\d+)C?\s*CPU', desc_upper)
    if cpu_cores_match:
        details['cpu_cores'] = cpu_cores_match.group(1)

    # Extract GPU cores
    gpu_cores_match = re.search(r'(\d+)C?\s*GPU', desc_upper)
    if gpu_cores_match:
        details['gpu_cores'] = gpu_cores_match.group(1)

    # Extract memory (RAM)
    mem_match = re.search(r'(\d+)\s*GB(?!\s*-|\s*SSD|\s*STORAGE)', desc_upper)
    if mem_match:
        details['memory'] = f"{mem_match.group(1)}GB"

    # Extract storage
    storage_match = re.search(r'(\d+)\s*(?:GB|TB)(?:\s*-|\s*SSD|\s*STORAGE)?', desc_upper)
    if storage_match:
        # Get the second number if exists (first is usually RAM)
        all_sizes = re.findall(r'(\d+)\s*(?:GB|TB)', desc_upper)
        if len(all_sizes) >= 2:
            size = all_sizes[1]
            unit = 'TB' if int(size) <= 4 else 'GB'
            details['storage'] = f"{size}{unit}"
        elif all_sizes:
            details['storage'] = f"{all_sizes[0]}GB"

    # Extract color
    colors = ['SILVER', 'SPACE GRAY', 'SPACE GREY', 'GOLD', 'MIDNIGHT', 'STARLIGHT']
    for color in colors:
        if color in desc_upper:
            details['color'] = color.title()
            break

    return details


def extract_from_attachment(attachment_path):
    """
    Main entry point to extract assets from a ticket attachment PDF
    """
    return extract_assets_from_pdf(attachment_path)
