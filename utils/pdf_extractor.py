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
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        logger.error("pytesseract or Pillow not installed")
        return None

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

    return result


def extract_assets_from_text(text):
    """
    Extract individual assets with serial numbers from text.
    Handles multiple product types by associating each serial with its nearby part number.
    """
    assets = []

    # Common Apple serial number patterns (alphanumeric, 10-12 chars)
    serial_pattern = r'\b([A-Z0-9]{10,14})\b'

    # Part number patterns - captures Apple part numbers like MWW03ZP/A or MXY32P/A
    # Need multiple patterns due to OCR variations
    part_number_patterns = [
        r'\b([A-Z]{2,4}[A-Z0-9]{2,4})[PZ]/[A-Z]',  # General: MWW03ZP/A, MXY32P/A, MX2Y3ZP/A
        r'\b(M[A-Z0-9]{4,5})[PZ]/[A-Z]',  # M-prefix: MWOW3ZP/A, MX2Y3ZP/A
    ]

    # Filter patterns for non-serial strings
    exclude_patterns = [
        r'^\d+$',  # Pure numbers
        r'^100\d{7}',  # PO numbers
        r'^847\d{5}',  # Commodity codes
        r'^656\d{8}',  # Tracking numbers
        r'^\d{9}[A-Z]$',  # Singapore UEN numbers
        r'^\d{8}[A-Z]$',  # Singapore UEN numbers (older format)
        r'^[A-Z]\d{8}[A-Z]$',  # Singapore UEN
        r'^SINGAPORE\d*$',
        r'^[A-Z]{2}\d{6}$',
        r'^\d{6}[A-Z]{2}\d{4}$',
    ]

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

    # Find all potential serials with positions
    serial_matches = []
    for match in re.finditer(serial_pattern, text):
        serial = match.group(1)

        # Skip if matches exclude patterns
        skip = False
        for exc_pattern in exclude_patterns:
            if re.match(exc_pattern, serial):
                skip = True
                break
        if skip:
            continue

        # Skip if too short or all numbers
        if len(serial) < 10 or serial.isdigit():
            continue

        # Apple serials need mix of letters and numbers (or start with S)
        has_letters = any(c.isalpha() for c in serial)
        has_numbers = any(c.isdigit() for c in serial)

        if has_letters and has_numbers:
            serial_matches.append({
                'serial': serial,
                'start': match.start(),
                'end': match.end()
            })
        elif serial.startswith('S') and has_letters and 10 <= len(serial) <= 12:
            serial_matches.append({
                'serial': serial,
                'start': match.start(),
                'end': match.end()
            })

    logger.info(f"Found {len(serial_matches)} potential serial numbers")

    # Match serials to part numbers in order
    # Each part number occurrence represents ONE asset
    # So if we have 19 MacBook Air part numbers + 8 MacBook Pro part numbers = 27 part numbers
    # And 27 serial numbers, they should match 1:1 in order

    # Remove duplicate serials while preserving order
    seen_serials = set()
    unique_serials = []
    for serial_info in serial_matches:
        if serial_info['serial'] not in seen_serials:
            seen_serials.add(serial_info['serial'])
            unique_serials.append(serial_info)

    logger.info(f"Unique serials: {len(unique_serials)}, Part numbers: {len(part_matches)}")

    # Match serials to part numbers by index (1:1 in order of appearance)
    for idx, serial_info in enumerate(unique_serials):
        serial = serial_info['serial']

        # Get the corresponding part number by index
        if idx < len(part_matches):
            best_part = part_matches[idx]
        else:
            # More serials than part numbers - use the last part number
            best_part = part_matches[-1] if part_matches else None

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
            context_end = min(len(text), best_part['end'] + 150)
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
