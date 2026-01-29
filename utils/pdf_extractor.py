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

# Apple part number prefix to model identifier mapping
# Format: Part number prefix (first 5-6 chars) -> Model identifier (e.g., A3113)
# Scraped from Apple Support and EveryMac.com
APPLE_PART_TO_MODEL = {
    # MacBook Air 13" M4 (2025) - A3240
    'MC6T4': 'A3240',  # Sky Blue
    'MW123': 'A3240',  # Midnight
    'MW0Y3': 'A3240',  # Starlight
    'MW0W3': 'A3240',  # Silver
    'MWW03': 'A3240',  # Possible OCR variant of MW0W3
    'MWOW3': 'A3240',  # OCR misread: 0->O in MWW03
    'MWOW0': 'A3240',  # OCR misread variant
    'MWO0W': 'A3240',  # OCR misread: W->0 (MWO0W3ZP/A)
    'MWOOW': 'A3240',  # OCR misread: 0->O (MWOOW3ZP/A)
    'MWOW8': 'A3240',  # OCR misread: 3->8
    # MacBook Air 15" M4 (2025) - A3241
    'MC7A4': 'A3241', 'MC7C4': 'A3241', 'MC7D4': 'A3241',  # Sky Blue configs
    'MW1L3': 'A3241', 'MW1M3': 'A3241', 'MC6L4': 'A3241',  # Midnight configs
    'MC6K4': 'A3241', 'MW1J3': 'A3241', 'MW1K3': 'A3241',  # Starlight configs
    'MW1G3': 'A3241', 'MW1H3': 'A3241', 'MC6J4': 'A3241',  # Silver configs
    # MacBook Air 13" M3 (2024) - A3113
    'MRXN3': 'A3113', 'MRXQ3': 'A3113', 'MRXT3': 'A3113', 'MRXV3': 'A3113',
    'MRXP3': 'A3113', 'MRXR3': 'A3113', 'MRXU3': 'A3113', 'MRXW3': 'A3113',
    'MXCR3': 'A3113', 'MXCT3': 'A3113', 'MXCU3': 'A3113', 'MXCV3': 'A3113',
    'MC8M4': 'A3113', 'MC8N4': 'A3113', 'MC8P4': 'A3113', 'MC8Q4': 'A3113',  # 24GB configs
    # MacBook Air 15" M3 (2024) - A3114
    'MRYM3': 'A3114', 'MRYN3': 'A3114', 'MRYP3': 'A3114', 'MRYQ3': 'A3114',
    'MRYR3': 'A3114', 'MRYT3': 'A3114', 'MRYU3': 'A3114', 'MRYV3': 'A3114',
    'MXD13': 'A3114', 'MXD23': 'A3114', 'MXD33': 'A3114', 'MXD43': 'A3114',
    # MacBook Air 13" M2 (2022) - A2681
    'MLXW3': 'A2681', 'MLXX3': 'A2681', 'MLXY3': 'A2681', 'MLY03': 'A2681',
    'MLY13': 'A2681', 'MLY23': 'A2681', 'MLY33': 'A2681', 'MLY43': 'A2681',
    'MNEQ3': 'A2681', 'MNER3': 'A2681', 'MNES3': 'A2681', 'MNET3': 'A2681',
    # MacBook Air 15" M2 (2023) - A2941
    'MQKP3': 'A2941', 'MQKQ3': 'A2941', 'MQKR3': 'A2941', 'MQKT3': 'A2941',
    'MQKU3': 'A2941', 'MQKV3': 'A2941', 'MQKW3': 'A2941', 'MQKX3': 'A2941',
    # MacBook Air 13" M1 (2020) - A2337
    'MGN63': 'A2337', 'MGN73': 'A2337', 'MGN93': 'A2337', 'MGNA3': 'A2337',
    'MGND3': 'A2337', 'MGNE3': 'A2337',
    # MacBook Pro 14" M3 Base (2023) - A2918
    'MR7J3': 'A2918', 'MR7K3': 'A2918', 'MRX23': 'A2918',
    'MTL73': 'A2918', 'MTL83': 'A2918', 'MTLC3': 'A2918',
    'MXE03': 'A2918', 'MXE13': 'A2918',
    # MacBook Pro 14" M3 Pro/Max (2023) - A2992
    'MRX33': 'A2992', 'MRX43': 'A2992', 'MRX53': 'A2992', 'MRX63': 'A2992',
    'MRX73': 'A2992', 'MRX83': 'A2992',
    # MacBook Pro 16" M3 Pro/Max (2023) - A2991
    'MRW13': 'A2991', 'MRW23': 'A2991', 'MRW33': 'A2991', 'MRW43': 'A2991',
    'MRW53': 'A2991', 'MRW63': 'A2991', 'MRW73': 'A2991', 'MUW63': 'A2991',
    # MacBook Pro 13" M2 (2022) - A2338
    'MNEH3': 'A2338', 'MNEJ3': 'A2338', 'MNEP3': 'A2338', 'MNEQ3': 'A2338',
    # MacBook Pro 14" M2 Pro/Max (2023) - A2779
    'MPHE3': 'A2779', 'MPHF3': 'A2779', 'MPHG3': 'A2779', 'MPHH3': 'A2779',
    'MPHJ3': 'A2779', 'MPHK3': 'A2779',
    # MacBook Pro 16" M2 Pro/Max (2023) - A2780
    'MNW83': 'A2780', 'MNW93': 'A2780', 'MNWA3': 'A2780', 'MNWC3': 'A2780',
    'MNWD3': 'A2780', 'MNWE3': 'A2780', 'MNWF3': 'A2780', 'MNWG3': 'A2780',
    # MacBook Pro 14" M1 Pro/Max (2021) - A2442
    'MKGP3': 'A2442', 'MKGQ3': 'A2442', 'MKGR3': 'A2442', 'MKGT3': 'A2442',
    # MacBook Pro 16" M1 Pro/Max (2021) - A2485
    'MK183': 'A2485', 'MK193': 'A2485', 'MK1A3': 'A2485', 'MK1E3': 'A2485',
    'MK1F3': 'A2485', 'MK1H3': 'A2485',
    # MacBook Pro 13" M1 (2020) - A2338
    'MYD83': 'A2338', 'MYD92': 'A2338', 'MYDA2': 'A2338', 'MYDC2': 'A2338',
    # MacBook Pro 14" M4 Base (2024) - A3283
    'MWV73': 'A3283', 'MWV83': 'A3283', 'MWV93': 'A3283', 'MWVA3': 'A3283',
    # MacBook Pro 14" M4 Pro/Max (2024) - A3284
    'MWX33': 'A3284', 'MWX43': 'A3284', 'MWX53': 'A3284', 'MWX63': 'A3284',
    'MWX73': 'A3284', 'MWX83': 'A3284', 'MWX93': 'A3284', 'MWXA3': 'A3284',
    'MXY23': 'A3284', 'MXY33': 'A3284', 'MXY43': 'A3284', 'MXY53': 'A3284',
    # MacBook Pro 16" M4 Pro/Max (2024) - A3287
    'MWX13': 'A3287', 'MWX23': 'A3287', 'MWW73': 'A3287', 'MWW83': 'A3287',
    'MWW93': 'A3287', 'MWWA3': 'A3287', 'MXY12': 'A3287', 'MXY22': 'A3287',
    'MXY32': 'A3287', 'MXY42': 'A3287', 'MXY52': 'A3287', 'MXY62': 'A3287',
    'MX2Y3': 'A3287',  # OCR misread: MXY32 -> MX2Y3 (char swap)
}


def get_apple_model_identifier(part_number):
    """
    Convert Apple part number to model identifier
    e.g., "MWW03ZP/A-SG0001" -> "A3114"
    """
    if not part_number:
        return None

    # Extract the first 5 characters (the unique part number prefix)
    # Part numbers look like: MWW03ZP/A-SG0001 or MWW03ZP/A
    prefix = part_number[:5].upper()

    # Look up in mapping
    model_id = APPLE_PART_TO_MODEL.get(prefix)

    if model_id:
        logger.info(f"Converted part number {part_number} -> {model_id}")
        return model_id

    logger.warning(f"Unknown Apple part number prefix: {prefix}")
    return None


def extract_text_with_ocr(pdf_path):
    """
    Extract text from a PDF using OCR (for scanned documents)
    Falls back to regular text extraction if OCR fails or isn't needed
    """
    import time
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.error("PyMuPDF (fitz) not installed")
        return None

    all_text = ""
    start_time = time.time()

    try:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        logger.info(f"PDF has {total_pages} pages, starting extraction...")

        for page_num, page in enumerate(doc):
            page_start = time.time()

            # First try regular text extraction (fast)
            text = page.get_text()

            # If no text found, try OCR (slow)
            if not text.strip():
                logger.info(f"Page {page_num + 1}/{total_pages}: No text found, attempting OCR...")
                ocr_text = ocr_page(page)
                if ocr_text:
                    text = ocr_text
                    page_time = time.time() - page_start
                    logger.info(f"Page {page_num + 1}/{total_pages}: OCR extracted {len(ocr_text)} chars in {page_time:.1f}s")
            else:
                page_time = time.time() - page_start
                logger.info(f"Page {page_num + 1}/{total_pages}: Text extracted ({len(text)} chars) in {page_time:.1f}s")

            all_text += text + "\n"

        doc.close()
        total_time = time.time() - start_time
        logger.info(f"PDF extraction complete: {len(all_text)} chars in {total_time:.1f}s")
        return all_text

    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        return None


def ocr_page(page, dpi=200):
    """
    Perform OCR on a PDF page using pytesseract

    Args:
        page: PyMuPDF page object
        dpi: Resolution for rendering (200 balances speed vs accuracy)
             - 150: Too fast, garbage output on tables
             - 200: Good balance for shared hosting like PythonAnywhere
             - 300: Best quality but causes timeout on shared hosting
    """
    import time
    import os
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        logger.error("pytesseract or Pillow not installed")
        return None

    # Configure tesseract path for macOS (Homebrew installation)
    if os.path.exists('/opt/homebrew/bin/tesseract'):
        pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'
    elif os.path.exists('/usr/local/bin/tesseract'):
        pytesseract.pytesseract.tesseract_cmd = '/usr/local/bin/tesseract'

    try:
        ocr_start = time.time()

        # Render page to image at 300 DPI for accurate OCR
        # Lower DPI causes garbage output on table-formatted documents
        pix = page.get_pixmap(dpi=dpi)
        render_time = time.time() - ocr_start

        # Convert to PIL Image
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        logger.info(f"  Rendered page at {dpi} DPI ({pix.width}x{pix.height}) in {render_time:.1f}s")

        # Perform OCR with default settings (PSM 3 = fully automatic page segmentation)
        # PSM 6 doesn't work well with table layouts
        ocr_start2 = time.time()
        text = pytesseract.image_to_string(img, lang='eng')
        ocr_time = time.time() - ocr_start2
        logger.info(f"  Tesseract OCR completed in {ocr_time:.1f}s")

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

        # Detect document format and use appropriate parser
        if is_success_tech_delivery_order(all_text):
            logger.info("Detected Success Tech Delivery Order format")
            return parse_success_tech_delivery_order(all_text)
        elif is_asiacloud_delivery_order(all_text):
            logger.info("Detected AsiaCloud Delivery Order format")
            return parse_asiacloud_delivery_order(all_text)
        else:
            # Standard packing list format
            return parse_packing_list_text(all_text)

    except Exception as e:
        logger.error(f"Error extracting PDF: {e}")
        return None


def is_success_tech_delivery_order(text):
    """
    Detect if the document is a Success Tech Delivery Order format
    """
    text_upper = text.upper()
    indicators = [
        'SUCCESS TECH' in text_upper or 'SUCCESSTECH' in text_upper,
        'DELIVERY ORDER' in text_upper,
        'DO NUMBER' in text_upper or 'SCT-DO' in text_upper,
        'GST REGISTRATION' in text_upper,
    ]
    # Need at least 2 indicators to confirm
    return sum(indicators) >= 2


def parse_success_tech_delivery_order(text):
    """
    Parse Success Tech Delivery Order format

    Format:
    - Header: DELIVERY ORDER with Success Tech Pte Ltd
    - Delivery Date, DO Number (SCT-DO250XXX), Account Number
    - Reference (PO Number like 4500153441)
    - Deliver to section with "On Behalf of [Customer]"
    - Description with product details
    - S/N: section with serial numbers
    - Quantity
    """
    result = {
        'po_number': None,
        'reference': None,
        'do_number': None,
        'ship_date': None,
        'supplier': 'Success Tech Pte Ltd',
        'receiver': None,
        'customer': None,
        'total_quantity': 0,
        'assets': [],
        'raw_text': text[:2000]
    }

    # Extract PO Number from Reference field (e.g., "Reference PO 4500153441")
    po_match = re.search(r'Reference\s*(?:PO\s*)?(\d{10})', text, re.IGNORECASE)
    if po_match:
        result['po_number'] = po_match.group(1)

    # Also check for "PO Number: 4500153441" at bottom
    if not result['po_number']:
        po_match2 = re.search(r'PO\s*Number[:\s]*(\d{10})', text, re.IGNORECASE)
        if po_match2:
            result['po_number'] = po_match2.group(1)

    # Extract DO Number (e.g., "SCT-DO250154")
    do_match = re.search(r'DO\s*Number\s*(SCT-DO\d+)', text, re.IGNORECASE)
    if do_match:
        result['do_number'] = do_match.group(1)
    else:
        # Try alternate pattern
        do_match2 = re.search(r'(SCT-DO\d+)', text, re.IGNORECASE)
        if do_match2:
            result['do_number'] = do_match2.group(1)

    result['reference'] = result['do_number']

    # Extract Delivery Date (e.g., "13 Jan 2026")
    date_match = re.search(r'Delivery\s*Date\s*(\d{1,2}\s+\w{3}\s+\d{4})', text, re.IGNORECASE)
    if date_match:
        result['ship_date'] = date_match.group(1)

    # Extract Customer from "On Behalf of" line
    customer_match = re.search(r'On\s*Behalf\s*of\s+([^\n]+)', text, re.IGNORECASE)
    if customer_match:
        result['customer'] = customer_match.group(1).strip()
        result['receiver'] = result['customer']

    # Extract Quantity (e.g., "1.00" or "7.00")
    qty_match = re.search(r'Quantity\s*\n?\s*(\d+)\.?\d*', text, re.IGNORECASE)
    if qty_match:
        result['total_quantity'] = int(float(qty_match.group(1)))

    # Extract product description
    product_details = parse_success_tech_description(text)

    # Extract serial numbers from S/N section
    serials = extract_success_tech_serials(text)
    logger.info(f"Success Tech: Found {len(serials)} serial numbers")

    # Update quantity if we found more serials than expected
    if len(serials) > result['total_quantity']:
        result['total_quantity'] = len(serials)

    # Create assets for each serial
    for serial in serials:
        asset = {
            'serial_num': serial,
            'name': product_details.get('name', 'Surface Laptop'),
            'model': product_details.get('model', ''),
            'manufacturer': product_details.get('manufacturer', 'Microsoft'),
            'category': 'Laptop',
            'cpu_type': product_details.get('cpu_type', ''),
            'cpu_cores': product_details.get('cpu_cores', ''),
            'gpu_cores': product_details.get('gpu_cores', ''),
            'memory': product_details.get('memory', ''),
            'harddrive': product_details.get('storage', ''),
            'hardware_type': 'Laptop',
            'condition': 'New',
            'keyboard': product_details.get('keyboard', ''),
            'notes': f"PO: {result['po_number']}, DO: {result['do_number']}",
        }
        result['assets'].append(asset)

    return result


def parse_success_tech_description(text):
    """
    Parse the Description field from Success Tech Delivery Order

    Examples:
    - "EP2-22236, Surface Laptop (7th Edition) Intel Core Ultra 512GB CU5 32GB 3.8" Black (Windows 11 Pro) Keyboard Layout: US - English"
    - "Surface Laptop (7th Edition) Intel Core Ultra 512GB CU5 32GB 13.8" Black (Windows 11 Pro) Keyboard Layout: US - English"
    """
    details = {
        'name': 'Surface Laptop',
        'model': '',
        'manufacturer': 'Microsoft',
        'cpu_type': '',
        'cpu_cores': '',
        'gpu_cores': '',
        'memory': '',
        'storage': '',
        'keyboard': '',
        'color': '',
    }

    text_upper = text.upper()

    # Extract product name - Surface Laptop
    if 'SURFACE LAPTOP' in text_upper:
        details['name'] = 'Surface Laptop'
        details['model'] = 'Surface Laptop'
        details['manufacturer'] = 'Microsoft'

        # Get edition (e.g., "7th Edition")
        edition_match = re.search(r'Surface\s+Laptop\s*\((\d+\w*\s*Edition)\)', text, re.IGNORECASE)
        if edition_match:
            details['model'] = f"Surface Laptop {edition_match.group(1)}"
    elif 'SURFACE PRO' in text_upper:
        details['name'] = 'Surface Pro'
        details['model'] = 'Surface Pro'
        details['manufacturer'] = 'Microsoft'
    elif 'MACBOOK' in text_upper:
        details['manufacturer'] = 'Apple'
        if 'MACBOOK PRO' in text_upper:
            details['name'] = 'MacBook Pro'
            details['model'] = 'MacBook Pro'
        elif 'MACBOOK AIR' in text_upper:
            details['name'] = 'MacBook Air'
            details['model'] = 'MacBook Air'

    # Extract CPU type (e.g., "Intel Core Ultra")
    cpu_match = re.search(r'(Intel\s+Core\s+(?:Ultra|i\d))', text, re.IGNORECASE)
    if cpu_match:
        details['cpu_type'] = cpu_match.group(1)

    # Extract Memory (e.g., "32GB" - usually appears after storage in this format)
    # Pattern: "512GB CU5 32GB" - storage first, then code, then memory
    mem_match = re.search(r'(?:CU\d|SSD|GB)\s+(\d+)GB(?:\s+\d|"|\s+Black|\s+Silver)', text, re.IGNORECASE)
    if mem_match:
        details['memory'] = mem_match.group(1) + 'GB'
    else:
        # Fallback: find all GB values and take the smaller one as RAM
        gb_values = re.findall(r'(\d+)GB', text, re.IGNORECASE)
        if len(gb_values) >= 2:
            # Convert to integers and sort
            gb_ints = sorted([int(v) for v in gb_values])
            # Smaller value is usually RAM, larger is storage
            if gb_ints[0] <= 64:  # RAM is typically <= 64GB
                details['memory'] = str(gb_ints[0]) + 'GB'
            if gb_ints[-1] >= 128:  # Storage is typically >= 128GB
                details['storage'] = str(gb_ints[-1]) + 'GB'

    # Extract Storage (e.g., "512GB")
    if not details['storage']:
        storage_match = re.search(r'(\d+)GB\s*(?:CU\d|SSD)', text, re.IGNORECASE)
        if storage_match:
            details['storage'] = storage_match.group(1) + 'GB'

    # Extract Keyboard Layout (e.g., "US - English")
    keyboard_match = re.search(r'Keyboard\s*Layout[:\s]*([^\n\(]+)', text, re.IGNORECASE)
    if keyboard_match:
        details['keyboard'] = keyboard_match.group(1).strip()

    # Extract Color (e.g., "Black", "Silver", "Platinum")
    colors = ['BLACK', 'SILVER', 'PLATINUM', 'SAPPHIRE', 'GRAPHITE']
    for color in colors:
        if color in text_upper:
            details['color'] = color.title()
            break

    # Extract screen size if present
    size_match = re.search(r'(\d+\.?\d*)["\']', text)
    if size_match:
        size = size_match.group(1)
        if float(size) > 10:  # Screen size, not something else
            details['name'] = f'{size}" {details["name"]}'

    logger.info(f"Success Tech description parsed: {details}")
    return details


def extract_success_tech_serials(text):
    """
    Extract serial numbers from Success Tech Delivery Order format

    Serial numbers appear after "S/N:" and can be:
    - Single: "S/N: 0F3P86Y25463P7"
    - Multiple lines:
        S/N:
        0F36YW925483P7
        0F3P87C25463P7
        ...
    """
    serials = []

    # Find the S/N section
    sn_section_match = re.search(r'S/N[:\s]*([\s\S]*?)(?:PO\s*Number|We\s*confirm|Customer|$)', text, re.IGNORECASE)
    if sn_section_match:
        sn_section = sn_section_match.group(1)
    else:
        # Fallback to searching whole text
        sn_section = text

    # Microsoft Surface serial patterns - alphanumeric, typically start with 0F or similar
    # Format: 0F3P86Y25463P7 (14 chars, alphanumeric)
    # Note: OCR may render "0F" as "OF" (zero to letter O), so we accept both
    serial_pattern = r'\b([0O]F[A-Z0-9]{12})\b'

    # Find all matches
    for match in re.finditer(serial_pattern, sn_section, re.IGNORECASE):
        serial = match.group(1).upper()
        # Normalize OCR variation: "OF" -> "0F" (letter O to zero)
        if serial.startswith('OF'):
            serial = '0F' + serial[2:]
        if serial not in serials:
            serials.append(serial)

    # If no Microsoft serials found, try a more generic pattern
    if not serials:
        # Generic alphanumeric serial pattern (10-14 chars starting with digit or letter)
        generic_pattern = r'\b([A-Z0-9]{10,14})\b'

        # Exclude patterns
        exclude_patterns = [
            r'^\d+$',  # Pure numbers
            r'^SCT',  # DO numbers
            r'^450\d+',  # PO numbers
            r'^GST',  # GST numbers
            r'^S\d{6}$',  # Postal codes
            r'^\d{9}[A-Z]',  # UEN numbers
        ]

        for match in re.finditer(generic_pattern, sn_section):
            serial = match.group(1).upper()

            # Skip excluded patterns
            skip = False
            for exc in exclude_patterns:
                if re.match(exc, serial, re.IGNORECASE):
                    skip = True
                    break

            if skip:
                continue

            # Must have mix of letters and numbers
            has_letters = sum(1 for c in serial if c.isalpha()) >= 2
            has_numbers = sum(1 for c in serial if c.isdigit()) >= 2

            if has_letters and has_numbers and serial not in serials:
                serials.append(serial)

    return serials


def is_asiacloud_delivery_order(text):
    """
    Detect if the document is an AsiaCloud Delivery Order format
    """
    text_upper = text.upper()
    indicators = [
        'ASIACLOUD' in text_upper,
        'DELIVERY ORDER' in text_upper,
        'CUSTOMER PO NO' in text_upper,
        'SO NO.' in text_upper or 'SO NO:' in text_upper,
    ]
    # Need at least 2 indicators to confirm
    return sum(indicators) >= 2


def parse_asiacloud_delivery_order(text):
    """
    Parse AsiaCloud Delivery Order format
    Format has: Part No, Description with specs, Serial numbers listed at bottom
    """
    result = {
        'po_number': None,
        'reference': None,
        'ship_date': None,
        'supplier': 'AsiaCloud Solutions',
        'receiver': None,
        'total_quantity': 0,
        'assets': [],
        'raw_text': text[:2000]
    }

    # Extract Customer PO Number (e.g., "PO# 100010699 HackerOne")
    po_match = re.search(r'(?:Customer\s*)?PO\s*(?:No\.?|#)[:\s]*(?:PO#\s*)?(\d+)', text, re.IGNORECASE)
    if po_match:
        result['po_number'] = po_match.group(1)

    # Extract SO Number as reference (e.g., "AT251210060")
    so_match = re.search(r'SO\s*No\.?[:\s]*([A-Z0-9]+)', text, re.IGNORECASE)
    if so_match:
        result['reference'] = so_match.group(1)

    # Extract Date (e.g., "26-12-25")
    date_match = re.search(r'Date[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', text, re.IGNORECASE)
    if date_match:
        result['ship_date'] = date_match.group(1)

    # Extract Ship-to address receiver
    ship_match = re.search(r'Ship-to\s*Address[:\s]*([^\n]+)', text, re.IGNORECASE)
    if ship_match:
        result['receiver'] = ship_match.group(1).strip()

    # Extract quantity from table
    qty_match = re.search(r'Quantity\s+(\d+)', text, re.IGNORECASE)
    if qty_match:
        result['total_quantity'] = int(qty_match.group(1))

    # Extract product details from Description field
    product_details = parse_asiacloud_description(text)

    # Extract serial numbers - look for "Serial No:" section
    serials = extract_asiacloud_serials(text)
    logger.info(f"AsiaCloud: Found {len(serials)} serial numbers")

    # Create assets for each serial
    for serial in serials:
        asset = {
            'serial_num': serial,
            'name': product_details.get('name', 'MacBook Pro'),
            'model': product_details.get('model', ''),
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
        result['assets'].append(asset)

    if not result['total_quantity']:
        result['total_quantity'] = len(serials)

    return result


def parse_asiacloud_description(text):
    """
    Parse the Description field from AsiaCloud Delivery Order
    Extracts specs from format like:
    - Apple "14-inch MacBook Pro: Space Black
    - Chip (Processor): (065-CJG1) - Apple M4 Pro chip with 14-core CPU, 20-core GPU
    - Memory: (065-CJG6) - 48GB unified
    - Storage: (065-CJGC) - 512GB SSD
    """
    details = {
        'name': 'MacBook Pro',
        'model': '',
        'cpu_type': '',
        'cpu_cores': '',
        'gpu_cores': '',
        'memory': '',
        'storage': '',
    }

    text_upper = text.upper()

    # Extract product name from Description field
    # Pattern: Apple "14-inch MacBook Pro: Space Black
    name_match = re.search(r'Apple\s*["\']?(\d+)[-\s]?inch\s+(MacBook\s+(?:Pro|Air))[:\s]*([^"\n]+)?', text, re.IGNORECASE)
    if name_match:
        size = name_match.group(1)
        model_type = name_match.group(2)
        color = name_match.group(3).strip() if name_match.group(3) else ''
        details['name'] = f'{size}" {model_type}'
        if 'Pro' in model_type:
            details['model'] = 'MacBook Pro'
        else:
            details['model'] = 'MacBook Air'
    elif 'MACBOOK PRO' in text_upper:
        details['name'] = 'MacBook Pro'
        details['model'] = 'MacBook Pro'
        # Try to get screen size
        size_match = re.search(r'(\d+)[-\s]?inch', text, re.IGNORECASE)
        if size_match:
            details['name'] = f'{size_match.group(1)}" MacBook Pro'
    elif 'MACBOOK AIR' in text_upper:
        details['name'] = 'MacBook Air'
        details['model'] = 'MacBook Air'
        size_match = re.search(r'(\d+)[-\s]?inch', text, re.IGNORECASE)
        if size_match:
            details['name'] = f'{size_match.group(1)}" MacBook Air'

    # Extract CPU info from Chip (Processor) line
    # Pattern: Apple M4 Pro chip with 14-core CPU, 20-core GPU
    chip_match = re.search(r'Apple\s+(M\d+(?:\s+Pro|\s+Max)?)\s+chip\s+with\s+(\d+)[-\s]?core\s+CPU[,\s]+(\d+)[-\s]?core\s+GPU', text, re.IGNORECASE)
    if chip_match:
        details['cpu_type'] = chip_match.group(1)
        details['cpu_cores'] = chip_match.group(2)
        details['gpu_cores'] = chip_match.group(3)
    else:
        # Fallback: just look for M4/M4 Pro/M4 Max
        cpu_match = re.search(r'\b(M\d+(?:\s+Pro|\s+Max)?)\b', text, re.IGNORECASE)
        if cpu_match:
            details['cpu_type'] = cpu_match.group(1)

        # Look for CPU cores
        cpu_cores_match = re.search(r'(\d+)[-\s]?core\s+CPU', text, re.IGNORECASE)
        if cpu_cores_match:
            details['cpu_cores'] = cpu_cores_match.group(1)

        # Look for GPU cores
        gpu_cores_match = re.search(r'(\d+)[-\s]?core\s+GPU', text, re.IGNORECASE)
        if gpu_cores_match:
            details['gpu_cores'] = gpu_cores_match.group(1)

    # Extract Memory
    # Pattern: Memory: (065-CJG6) - 48GB unified
    mem_match = re.search(r'Memory[:\s]*(?:\([^)]+\)\s*-?\s*)?(\d+)GB', text, re.IGNORECASE)
    if mem_match:
        details['memory'] = mem_match.group(1) + 'GB'

    # Extract Storage
    # Pattern: Storage: (065-CJGC) - 512GB SSD
    storage_match = re.search(r'Storage[:\s]*(?:\([^)]+\)\s*-?\s*)?(\d+)(?:GB|TB)\s*(?:SSD|SSE|SSt)?', text, re.IGNORECASE)
    if storage_match:
        storage_val = storage_match.group(1)
        # OCR often misreads "512GB" as "12GB" - detect this by checking if value is unrealistically low
        # Apple storage is always >= 128GB, never 12GB
        if int(storage_val) < 100:
            # Try to find more specific storage mentions in description
            # Look for patterns like "512GB SSD" anywhere in text
            alt_storage = re.search(r'\b(128|256|512|1024|2048)\s*GB', text, re.IGNORECASE)
            if alt_storage:
                storage_val = alt_storage.group(1)
            else:
                # Check for TB
                tb_match = re.search(r'\b([1248])\s*TB', text, re.IGNORECASE)
                if tb_match:
                    details['storage'] = tb_match.group(1) + 'TB'
                    storage_val = None  # Already set

        if storage_val:
            if int(storage_val) <= 4:
                details['storage'] = storage_val + 'TB'
            else:
                details['storage'] = storage_val + 'GB'

    # Sanity check: storage should be larger than memory
    # If not, try to infer from common Apple configs
    if details['memory'] and details['storage']:
        try:
            mem_gb = int(details['memory'].replace('GB', '').replace('TB', ''))
            storage_num = int(details['storage'].replace('GB', '').replace('TB', ''))
            if 'TB' not in details['storage'] and storage_num < mem_gb:
                # Storage can't be less than RAM - likely OCR error
                # For 48GB RAM configs, storage is typically 512GB or higher
                if mem_gb >= 48:
                    details['storage'] = '512GB'
                elif mem_gb >= 24:
                    details['storage'] = '512GB'
                else:
                    details['storage'] = '256GB'
                logger.warning(f"Storage {storage_num}GB < Memory {mem_gb}GB - corrected to {details['storage']}")
        except (ValueError, AttributeError):
            pass

    logger.info(f"AsiaCloud description parsed: {details}")
    return details


def extract_asiacloud_serials(text):
    """
    Extract serial numbers from AsiaCloud Delivery Order format
    They appear after "Serial No:" in two columns:
    Serial No:    SFDGJG97N27
    SFD7T2H5C9C   SFDK6F7D7LW
    SFDGDW5952K   SH6WT329MW7
    """
    serials = []

    # Find the Serial No section
    serial_section_match = re.search(r'Serial\s*No\s*[:\s]*([\s\S]*?)(?:Remarks:|Received|$)', text, re.IGNORECASE)
    if serial_section_match:
        serial_section = serial_section_match.group(1)
    else:
        serial_section = text

    # Apple serial patterns - typically 10-12 alphanumeric starting with letter
    # MacBook Pro serials often start with S, C, F, or other letters
    serial_pattern = r'\b([A-Z][A-Z0-9]{9,11})\b'

    # Exclude patterns
    exclude_patterns = [
        r'^\d+$',  # Pure numbers
        r'^AT\d+',  # SO numbers like AT251210060
        r'^Z\d+',  # Part numbers like Z1FE00012
        r'^PO\d+',
        r'^\d{6,}$',
    ]

    for match in re.finditer(serial_pattern, serial_section):
        serial = match.group(1)

        # Skip excluded patterns
        skip = False
        for exc in exclude_patterns:
            if re.match(exc, serial, re.IGNORECASE):
                skip = True
                break

        if skip:
            continue

        # Apple serials must have mix of letters and numbers
        has_letters = sum(1 for c in serial if c.isalpha()) >= 2
        has_numbers = sum(1 for c in serial if c.isdigit()) >= 2

        if has_letters and has_numbers and serial not in serials:
            serials.append(serial)

    return serials


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
        r'PO\s*n[ro]?[:\s]*(\d+)',  # PO nr: 100010948
        r'PO\s*Number[:\s]*(\d+)',  # PO Number: 100010948
        r'(\d{9,})\s*WISE',  # 100010948 WISE -> capture only number
        r'(\d{9,})\s+[A-Z]+',  # 100010948 followed by any word -> capture only number
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

    # Generate breakdown by counting FULL PART NUMBER occurrences directly in text
    # This is the most accurate method - count exact part number strings
    breakdown = {}
    breakdown_serials = {}  # Track which serials belong to each model
    text_upper = text.upper()

    # Full part number patterns with OCR variations (0 vs O confusion)
    # Each entry: (list of patterns to count, description, list of model prefixes)
    part_number_groups = [
        # Starlight: MW0Y3 and MWOY3 (OCR reads 0 as O)
        (['MW0Y3ZP/A', 'MWOY3ZP/A'], '13" MacBook Air Starlight M4 (10C CPU, 8C GPU, 16GB RAM, 256GB SSD)', ['MW0Y3', 'MWOY3']),
        # Sky Blue: MC6T4 (no OCR variation issue)
        (['MC6T4ZP/A'], '13" MacBook Air Sky Blue M4 (10C CPU, 8C GPU, 16GB RAM, 256GB SSD)', ['MC6T4']),
        # Silver: MW0W3 and MWOW3 (OCR reads 0 as O)
        (['MW0W3ZP/A', 'MWOW3ZP/A'], '13" MacBook Air Silver M4 (10C CPU, 8C GPU, 16GB RAM, 256GB SSD)', ['MW0W3', 'MWOW3']),
        # Midnight: MW123 (no OCR variation issue with numbers)
        (['MW123ZP/A'], '13" MacBook Air Midnight M4 (10C CPU, 8C GPU, 16GB RAM, 256GB SSD)', ['MW123']),
        # MacBook Pro models
        (['MXD33ZP/A'], '14" MacBook Pro Space Black M4 Pro', ['MXD33']),
        (['MXD53ZP/A'], '14" MacBook Pro Space Black M4 Pro', ['MXD53']),
        (['MXD93ZP/A'], '16" MacBook Pro Space Black M4 Pro', ['MXD93']),
        (['MXF53ZP/A'], '16" MacBook Pro Space Black M4 Max', ['MXF53']),
    ]

    # Count each part number group (summing all OCR variations)
    for patterns, description, model_prefixes in part_number_groups:
        total_count = 0
        for pattern in patterns:
            total_count += text_upper.count(pattern)
        if total_count > 0:
            breakdown[description] = total_count
            breakdown_serials[description] = []

    # Match assets to breakdown categories based on their model prefix
    for asset in assets:
        asset_model = asset.get('model', '') or ''
        serial = asset.get('serial', '')
        matched = False
        for patterns, description, model_prefixes in part_number_groups:
            if any(asset_model.upper().startswith(prefix) for prefix in model_prefixes):
                if description in breakdown_serials:
                    breakdown_serials[description].append(serial)
                    matched = True
                    break
        # If no match found, add to "Other" category
        if not matched and serial:
            other_key = f"Other ({asset_model})" if asset_model else "Other"
            if other_key not in breakdown_serials:
                breakdown_serials[other_key] = []
            breakdown_serials[other_key].append(serial)

    # If no breakdown from full part numbers, fall back to counting by model field
    if not breakdown and assets:
        for asset in assets:
            model = asset.get('model', '') or 'Unknown'
            name = asset.get('name', 'MacBook')
            serial = asset.get('serial', '')
            key = f"{name} ({model})" if model and model != 'Unknown' else name
            if key not in breakdown:
                breakdown[key] = 0
                breakdown_serials[key] = []
            breakdown[key] += 1
            if serial:
                breakdown_serials[key].append(serial)

    result['breakdown'] = breakdown
    result['breakdown_serials'] = breakdown_serials

    return result


def extract_assets_from_text(text):
    """
    Extract individual assets with serial numbers from text.
    Handles multiple product types by associating each serial with its nearby part number.
    """
    assets = []

    # Normalize text - convert to uppercase for consistent matching
    text_upper = text.upper()

    # Common Apple serial number patterns (alphanumeric, 10-14 chars)
    # Match both uppercase and original text
    serial_pattern = r'\b([A-Za-z0-9]{10,14})\b'

    # Part number patterns - captures Apple part numbers like MW0Y3ZP/A, MC6T4ZP/A
    # CDW format often has suffix like -SG0001 after the /A
    part_number_patterns = [
        r'\b(M[A-Z0-9]{5,6})[PZ]/[A-Z](?:-[A-Z0-9]+)?',  # Apple M-prefix: MW0Y3ZP/A-SG0001, MC6T4ZP/A-SG0001
        r'\b([A-Z]{2}[A-Z0-9]{3,5})[PZ]/[A-Z](?:-[A-Z0-9]+)?',  # 2-letter prefix: MW0Y3ZP/A, MC6T4ZP/A
        r'\b([A-Z]{2,4}[A-Z0-9]{2,4})[PZ]/[A-Z]',  # General format
        r'\b(M[WCXYQNKLRT][A-Z0-9]{3,5})[PZ]/[A-Z]',  # Apple M-series parts
    ]

    # Filter patterns for non-serial strings
    exclude_patterns = [
        r'^\d+$',  # Pure numbers
        r'^[A-Z]+$',  # Pure letters (no numbers) - colors, words
        r'^100\d{6,8}$',  # PO numbers (100XXXXXXX)
        r'^847\d{5}$',  # Commodity codes
        r'^656\d{8}$',  # Tracking numbers
        r'^\d{9}[A-Z]$',  # Singapore UEN numbers
        r'^\d{8}[A-Z]$',  # Singapore UEN numbers (older format)
        r'^[A-Z]\d{8}[A-Z]$',  # Singapore UEN
        r'^SINGAPORE\d*$',
        r'^[A-Z]{2}\d{6}$',
        r'^\d{6}[A-Z]{2}\d{4}$',
        r'^SG\d{4,}$',  # SG followed by numbers (like SG0001)
        r'^\d+X\d+X\d+',  # Dimensions like 120X100X185CM
        r'.*X\d+X\d+.*',  # Any dimension pattern with X separators
        r'.*\d+CM$',  # Anything ending with CM (centimeters)
        r'.*\d+MM$',  # Anything ending with MM (millimeters)
        r'.*\d+KG$',  # Anything ending with KG (kilograms)
    ]

    # Common words/colors that should never be serial numbers
    exclude_words = [
        'SPACEBLACK', 'SPACEGRAY', 'SPACEGREY', 'MIDNIGHT', 'STARLIGHT', 'SILVER',
        'SENTINELON', 'SENTINEL', 'MACBOOKPRO', 'MACBOOKAIR', 'MACBOOK',
        'DESCRIPTION', 'SERIALNUMB', 'SINGAPORE', 'COLLECTION', 'REFERENCE',
        'AUTHORIZED', 'CERTIFICATE', 'CONSOLIDATED', 'DECONSOLID', 'QUANTITY',
        'COMMODITY', 'KEYBOARD', 'PROCESSOR', 'STORAGE', 'MEMORY',
        'SKYBLUE', 'ROSEGOLD', 'GOLDCOLOR', 'BLACKCOLOR', 'WHITECOLOR',
        'AUTHORIZED1', 'COLLECTION1', 'DECONSOLIDA', 'DESCRIPTION1',
    ]

    # Initialize serial matches list early
    serial_matches = []
    seen_serial_values = set()

    # Normalize text - remove extra whitespace and normalize line endings
    text_normalized = ' '.join(text_upper.split())

    # Apple serials are typically 10-12 alphanumeric characters
    # Common patterns: SC2WXQ39W20, SH54VW1MWYP, SG0W347FYJG
    # They usually have a mix of letters and numbers

    # Pattern 1: Find all 10-12 character alphanumeric sequences
    # This is more aggressive to catch all potential serials
    all_potential_serials = re.findall(r'\b([A-Z0-9]{10,12})\b', text_normalized)

    logger.info(f"Found {len(all_potential_serials)} potential 10-12 char sequences")

    for serial in all_potential_serials:
        # Skip if already seen
        if serial in seen_serial_values:
            continue

        # Skip if in exclude words
        if serial in exclude_words:
            continue

        # Apple serials typically start with these letters (factory codes)
        # S=Shenzhen, C/D=Cork Ireland, F=Fremont, G/H=China, etc.
        apple_serial_prefixes = ['S', 'C', 'D', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'P', 'Q', 'R', 'T', 'V', 'W', 'X', 'Y']

        # Reject if it doesn't start with a known Apple prefix
        if serial[0] not in apple_serial_prefixes:
            continue

        # Apple serials starting with 'S' and exactly 11 chars can be all-letters
        # (e.g., SCDQXCNXWVL) - these are valid Shenzhen factory serials
        is_likely_apple_serial = serial[0] == 'S' and len(serial) == 11

        # Skip if matches exclude patterns (UNLESS it's a likely Apple all-letter serial)
        if not is_likely_apple_serial:
            skip = False
            for exc_pattern in exclude_patterns:
                if re.match(exc_pattern, serial, re.IGNORECASE):
                    skip = True
                    break
            if skip:
                continue

        # For non-Apple-serial patterns, require both letters and numbers
        if not is_likely_apple_serial:
            has_letters = any(c.isalpha() for c in serial)
            has_numbers = any(c.isdigit() for c in serial)
            if not (has_letters and has_numbers):
                continue

        # Skip if contains dimension patterns (120X100X185)
        if 'X' in serial and re.search(r'\d+X\d+', serial):
            continue

        seen_serial_values.add(serial)

        # Find position in original text_upper for matching
        pos = text_upper.find(serial)
        serial_matches.append({
            'serial': serial,
            'start': pos if pos >= 0 else 0,
            'end': (pos + len(serial)) if pos >= 0 else len(serial)
        })

    logger.info(f"Found {len(serial_matches)} valid serial numbers after filtering")

    # Find all part numbers with their positions (try multiple patterns)
    # Each occurrence represents ONE asset, so we keep all occurrences in order
    part_matches = []
    seen_positions = set()
    for pattern in part_number_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            # Avoid duplicate matches at same position
            if match.start() in seen_positions:
                continue
            seen_positions.add(match.start())

            part_prefix = match.group(1).upper()
            # Normalize OCR variations
            normalized_prefix = part_prefix[:5]  # First 5 chars for lookup
            part_matches.append({
                'prefix': normalized_prefix,
                'full': match.group(0).upper(),
                'start': match.start(),
                'end': match.end()
            })
    # Sort by position in text - ORDER MATTERS for matching with serials
    part_matches.sort(key=lambda x: x['start'])
    logger.info(f"Found {len(part_matches)} part number occurrences: {[p['prefix'] for p in part_matches]}")

    # Second pass: Find additional potential serials (not starting with S)
    # This catches any edge cases the Apple serial pattern might miss
    for match in re.finditer(serial_pattern, text_upper):
        serial = match.group(1).upper()

        # Skip if already found
        if serial in seen_serial_values:
            continue

        # Skip if matches exclude patterns
        skip = False
        for exc_pattern in exclude_patterns:
            if re.match(exc_pattern, serial, re.IGNORECASE):
                skip = True
                break
        if skip:
            continue

        # Skip if matches exclude words (colors, product names, etc.)
        if serial in exclude_words:
            continue

        # Skip if too short or all numbers
        if len(serial) < 10 or serial.isdigit():
            continue

        # Apple serials starting with 'S' and exactly 11 chars can be all-letters
        is_likely_apple_serial = serial[0] == 'S' and len(serial) == 11

        # Skip if all letters (no numbers) - unless it's a likely Apple serial
        if serial.isalpha() and not is_likely_apple_serial:
            continue

        # For non-Apple patterns, require mix of letters and numbers
        has_letters = any(c.isalpha() for c in serial)
        has_numbers = any(c.isdigit() for c in serial)

        if (has_letters and has_numbers) or is_likely_apple_serial:
            seen_serial_values.add(serial)
            serial_matches.append({
                'serial': serial,
                'start': match.start(),
                'end': match.end()
            })

    # Sort serials by position in text for proper matching
    serial_matches.sort(key=lambda x: x['start'])
    logger.info(f"Total unique serials found: {len(serial_matches)}")

    # Match each serial to its nearest PRECEDING part number
    # This handles packing lists where one part number is listed, then multiple serials follow
    logger.info(f"Unique serials: {len(serial_matches)}, Part numbers: {len(part_matches)}")

    # Create a list of unique serials (already deduplicated via seen_serial_values)
    unique_serials = serial_matches

    for idx, serial_info in enumerate(unique_serials):
        serial = serial_info['serial']
        serial_pos = serial_info['start']

        # Find the nearest PRECEDING part number (part number that comes BEFORE this serial)
        best_part = None
        best_distance = float('inf')

        for part in part_matches:
            # Part number must come BEFORE the serial
            if part['end'] < serial_pos:
                distance = serial_pos - part['end']
                if distance < best_distance:
                    best_distance = distance
                    best_part = part

        # If no preceding part found, use the first part number (fallback for edge cases)
        if best_part is None and part_matches:
            best_part = part_matches[0]

        # Get part number prefix and look up model
        part_prefix = best_part['prefix'] if best_part else None
        model_identifier = get_apple_model_identifier(part_prefix) if part_prefix else None

        # Extract product description from text near the PART NUMBER (not serial)
        # Since we're matching by index, use the part number's position to find specs
        product_details = {'name': 'MacBook', 'cpu_type': '', 'cpu_cores': '', 'gpu_cores': '', 'memory': '', 'storage': ''}

        # Build context around the part number occurrence
        # The description is usually right AFTER the part number (not before)
        # Use minimal before context to avoid picking up previous product's specs
        if best_part:
            part_pos = best_part['start']
            context_start = max(0, best_part['end'])  # Start FROM the end of part number
            context_end = min(len(text), best_part['end'] + 300)
            context = text[context_start:context_end]
        else:
            # Fallback: use serial position
            serial_pos = serial_info['start']
            context_start = max(0, serial_pos - 500)
            context_end = min(len(text), serial_info['end'] + 300)
            context = text[context_start:context_end]

        context_upper = context.upper()

        # Determine if MacBook Air or Pro from MODEL IDENTIFIER (more reliable than context)
        # A3240/A3241 = MacBook Air, A3283/A3284/A3287 = MacBook Pro
        if model_identifier in ['A3240', 'A3241', 'A3113', 'A3114', 'A2681', 'A2941', 'A2337']:
            product_details['name'] = 'MacBook Air'
        elif model_identifier in ['A3283', 'A3284', 'A3287', 'A2918', 'A2992', 'A2991', 'A2338', 'A2779', 'A2780', 'A2442', 'A2485']:
            product_details['name'] = 'MacBook Pro'
        elif 'MACBOOK PRO' in context_upper:
            product_details['name'] = 'MacBook Pro'
        elif 'MACBOOK AIR' in context_upper:
            product_details['name'] = 'MacBook Air'

        # Extract screen size
        size_match = re.search(r'(\d+)["\']?\s*(?:IN|INCH|MACBOOK)', context, re.IGNORECASE)
        if size_match:
            size = size_match.group(1)
            if size in ['13', '14', '15', '16']:
                product_details['name'] = f'{size}" {product_details["name"]}'

        # Extract CPU type (M1, M2, M3, M4)
        cpu_match = re.search(r'\b(M\d+)\b', context_upper)
        if cpu_match:
            product_details['cpu_type'] = cpu_match.group(1)

        # Extract CPU cores
        cpu_cores_match = re.search(r'(\d+)C?\s*CPU', context_upper)
        if cpu_cores_match:
            product_details['cpu_cores'] = cpu_cores_match.group(1)

        # Extract GPU cores
        gpu_cores_match = re.search(r'(\d+)C?\s*GPU', context_upper)
        if gpu_cores_match:
            product_details['gpu_cores'] = gpu_cores_match.group(1)

        # Extract RAM and storage - look for patterns like "16GB 256GB" or "48GB 512GB"
        ram_storage = re.search(r'(\d+)GB\s+(\d+)(?:GB|TB)', context, re.IGNORECASE)
        if ram_storage:
            ram_value = ram_storage.group(1)
            # OCR correction: 46GB is not a valid Apple RAM config, likely OCR misread of 16GB (1→4)
            if ram_value == '46':
                ram_value = '16'
            product_details['memory'] = ram_value + "GB"
            storage_num = int(ram_storage.group(2))
            if storage_num <= 4:
                product_details['storage'] = str(storage_num) + "TB"
            else:
                product_details['storage'] = str(storage_num) + "GB"

        # Detect M4 Pro/Max based on CPU cores (M4 Pro has 12-14 cores, M4 Max has 14-16)
        if product_details['cpu_type'] == 'M4' and product_details['cpu_cores']:
            cores = int(product_details['cpu_cores'])
            if cores >= 12:
                product_details['cpu_type'] = 'M4 Pro'

        logger.info(f"Serial {serial} -> Part: {part_prefix}, Model: {model_identifier}, Name: {product_details['name']}")

        asset = {
            'serial_num': serial,
            'name': product_details.get('name', 'MacBook'),
            'model': model_identifier or '',
            'manufacturer': 'Apple',
            'category': 'Laptop',
            'cpu_type': product_details.get('cpu_type', ''),
            'cpu_cores': product_details.get('cpu_cores', ''),
            'gpu_cores': product_details.get('gpu_cores', ''),
            'memory': product_details.get('memory', ''),
            'harddrive': product_details.get('storage', ''),
            'hardware_type': 'Laptop',
            'condition': 'New',
            'part_prefix': part_prefix,  # Store for breakdown
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
