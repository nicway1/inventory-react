"""
PDF Asset Extractor
Extracts asset information from packing list PDFs for automatic asset creation
Supports both text-based PDFs and scanned images (via OCR)
"""
import re
import logging
import io
from datetime import datetime

logger = logging.getLogger(__name__)


def extract_text_with_ocr(pdf_path):
    """
    Extract text from a PDF using OCR (for scanned documents)
    Falls back to regular text extraction if OCR fails or isn't needed
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.error("PyMuPDF (fitz) not installed")
        return None

    all_text = ""

    try:
        doc = fitz.open(pdf_path)

        for page_num, page in enumerate(doc):
            # First try regular text extraction
            text = page.get_text()

            # If no text found, try OCR
            if not text.strip():
                logger.info(f"Page {page_num + 1}: No text found, attempting OCR...")
                ocr_text = ocr_page(page)
                if ocr_text:
                    text = ocr_text
                    logger.info(f"Page {page_num + 1}: OCR extracted {len(ocr_text)} characters")

            all_text += text + "\n"

        doc.close()
        return all_text

    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        return None


def ocr_page(page):
    """
    Perform OCR on a PDF page using pytesseract
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        logger.error("pytesseract or Pillow not installed")
        return None

    try:
        # Render page to image at high resolution for better OCR
        zoom = 2  # 2x zoom for better quality
        mat = page.parent.__class__.Matrix(zoom, zoom) if hasattr(page.parent, 'Matrix') else None

        # Get pixmap (image) of the page
        if mat:
            pix = page.get_pixmap(matrix=mat)
        else:
            pix = page.get_pixmap(dpi=300)

        # Convert to PIL Image
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))

        # Perform OCR
        text = pytesseract.image_to_string(img, lang='eng')

        return text

    except Exception as e:
        logger.error(f"OCR error: {e}")
        return None


def extract_shipping_info_from_pdf(pdf_path):
    """
    Extract shipping/PO information from the first page of a PDF (waybill/shipping label)

    Returns:
        dict with shipping details for ticket description
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.error("PyMuPDF (fitz) not installed")
        return None

    try:
        doc = fitz.open(pdf_path)

        # Get text from first page only
        if len(doc) == 0:
            return None

        first_page = doc[0]
        first_page_text = first_page.get_text()

        # If no text found, try OCR on first page
        if not first_page_text.strip():
            logger.info("First page has no text, attempting OCR...")
            first_page_text = ocr_page(first_page) or ""

        doc.close()

        return parse_shipping_label_text(first_page_text)

    except Exception as e:
        logger.error(f"Error extracting shipping info: {e}")
        return None


def parse_shipping_label_text(text):
    """
    Parse shipping label/waybill text to extract PO info
    """
    result = {
        'reference': None,
        'date': None,
        'shipper_name': None,
        'shipper_address': None,
        'receiver_name': None,
        'receiver_address': None,
        'contact_name': None,
        'contact_phone': None,
        'description': None,
        'pieces': None,
        'special_instructions': None,
        'tracking_number': None,
        'weight': None,
    }

    lines = text.split('\n')
    lines = [l.strip() for l in lines if l.strip()]

    # Extract Reference number
    ref_match = re.search(r'REFERENCE[#:\s]*(\d+)', text, re.IGNORECASE)
    if ref_match:
        result['reference'] = ref_match.group(1)

    # Extract Date
    date_patterns = [
        r'DATE[:\s]*(\d{1,2}[-/]\w{3}[-/]\d{2,4})',
        r'DATE[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['date'] = match.group(1)
            break

    # Extract tracking/barcode number (usually a long number)
    barcode_match = re.search(r'\b(656\d{9,})\b', text)
    if barcode_match:
        result['tracking_number'] = barcode_match.group(1)

    # Extract FROM (SHIPPER) section
    shipper_match = re.search(r'FROM\s*\(SHIPPER\)[:\s]*(.+?)(?=TO\s*\(RECEIVER\)|REFERENCE|$)', text, re.DOTALL | re.IGNORECASE)
    if shipper_match:
        shipper_text = shipper_match.group(1).strip()
        shipper_lines = [l.strip() for l in shipper_text.split('\n') if l.strip()]
        if shipper_lines:
            result['shipper_name'] = shipper_lines[0] if shipper_lines else None
            result['shipper_address'] = ', '.join(shipper_lines[1:]) if len(shipper_lines) > 1 else None

    # Extract TO (RECEIVER) section
    receiver_match = re.search(r'TO\s*\(RECEIVER\)[:\s]*(.+?)(?=CONTACT|TELEPHONE|DESCRIPTION|$)', text, re.DOTALL | re.IGNORECASE)
    if receiver_match:
        receiver_text = receiver_match.group(1).strip()
        receiver_lines = [l.strip() for l in receiver_text.split('\n') if l.strip()]
        if receiver_lines:
            result['receiver_name'] = receiver_lines[0] if receiver_lines else None
            # Filter out non-address lines
            addr_lines = [l for l in receiver_lines[1:] if not re.match(r'^(CONTACT|TELEPHONE|DESCRIPTION)', l, re.IGNORECASE)]
            result['receiver_address'] = ', '.join(addr_lines) if addr_lines else None

    # Extract Contact Name
    contact_match = re.search(r'CONTACT\s*NAME[:\s]*([^\n]+)', text, re.IGNORECASE)
    if contact_match:
        result['contact_name'] = contact_match.group(1).strip()

    # Extract Telephone
    phone_match = re.search(r'TELEPHONE[:\s]*(\d[\d\s-]+)', text, re.IGNORECASE)
    if phone_match:
        result['contact_phone'] = phone_match.group(1).strip()

    # Extract Description
    desc_match = re.search(r'DESCRIPTION[:\s]*([A-Z][A-Z\s]+?)(?=\d|RECEIVED|TIME|$)', text, re.IGNORECASE)
    if desc_match:
        result['description'] = desc_match.group(1).strip()

    # Extract Pieces
    pieces_match = re.search(r'PIECES[:\s]*(\d+)', text, re.IGNORECASE)
    if pieces_match:
        result['pieces'] = pieces_match.group(1)

    # Extract Special Instructions (like "1 PALLET - 56 PCS")
    special_match = re.search(r'SPECIAL\s*INSTRUCTIONS[:\s]*(.+?)(?=FROM|$)', text, re.DOTALL | re.IGNORECASE)
    if special_match:
        result['special_instructions'] = special_match.group(1).strip().replace('\n', ' ')
    else:
        # Try to find pallet info
        pallet_match = re.search(r'(\d+\s*PALLET[S]?\s*[-–]\s*\d+\s*PCS)', text, re.IGNORECASE)
        if pallet_match:
            result['special_instructions'] = pallet_match.group(1)

    # Extract Weight
    weight_match = re.search(r'WEIGHT[:\s]*\(?KG\)?[:\s]*([\d.]+)', text, re.IGNORECASE)
    if weight_match:
        result['weight'] = weight_match.group(1) + ' kg'

    return result


def format_shipping_info_for_description(info):
    """
    Format extracted shipping info into a nice ticket description
    """
    if not info:
        return None

    lines = []
    lines.append("=" * 50)
    lines.append("SHIPMENT INFORMATION (Extracted from PDF)")
    lines.append("=" * 50)

    if info.get('reference'):
        lines.append(f"Reference #: {info['reference']}")

    if info.get('date'):
        lines.append(f"Date: {info['date']}")

    if info.get('tracking_number'):
        lines.append(f"Tracking #: {info['tracking_number']}")

    lines.append("")
    lines.append("FROM (Shipper):")
    if info.get('shipper_name'):
        lines.append(f"  {info['shipper_name']}")
    if info.get('shipper_address'):
        lines.append(f"  {info['shipper_address']}")

    lines.append("")
    lines.append("TO (Receiver):")
    if info.get('receiver_name'):
        lines.append(f"  {info['receiver_name']}")
    if info.get('receiver_address'):
        lines.append(f"  {info['receiver_address']}")

    if info.get('contact_name') or info.get('contact_phone'):
        lines.append("")
        lines.append("Contact:")
        if info.get('contact_name'):
            lines.append(f"  Name: {info['contact_name']}")
        if info.get('contact_phone'):
            lines.append(f"  Phone: {info['contact_phone']}")

    lines.append("")
    lines.append("Shipment Details:")
    if info.get('description'):
        lines.append(f"  Description: {info['description']}")
    if info.get('special_instructions'):
        lines.append(f"  Quantity: {info['special_instructions']}")
    if info.get('pieces'):
        lines.append(f"  Pieces: {info['pieces']}")
    if info.get('weight'):
        lines.append(f"  Weight: {info['weight']}")

    lines.append("=" * 50)

    return '\n'.join(lines)


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
        # Use OCR-enabled extraction (handles both text PDFs and scanned images)
        all_text = extract_text_with_ocr(pdf_path)

        if not all_text:
            logger.error("Failed to extract text from PDF")
            return None

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
