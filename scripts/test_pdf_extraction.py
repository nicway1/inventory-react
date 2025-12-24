#!/usr/bin/env python3
"""
Test PDF extraction on PythonAnywhere
Run: python scripts/test_pdf_extraction.py <path_to_pdf>
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.pdf_extractor import extract_text_with_ocr, extract_assets_from_text, extract_assets_from_pdf

def test_extraction(pdf_path):
    print(f"Testing extraction on: {pdf_path}")
    print("=" * 80)

    # Step 1: Extract text
    print("\n1. Extracting text from PDF...")
    text = extract_text_with_ocr(pdf_path)

    if not text:
        print("   ERROR: No text extracted!")
        return

    print(f"   Extracted {len(text)} characters")
    print(f"\n   First 1000 chars:\n   {'-'*40}")
    print(text[:1000])
    print(f"   {'-'*40}")

    # Step 2: Find part numbers
    print("\n2. Looking for Apple part numbers...")
    import re
    part_patterns = [
        r'\b([A-Z]{2,4}[A-Z0-9]{2,4})[PZ]/[A-Z]',
        r'\b(M[A-Z0-9]{4,5})[PZ]/[A-Z]',
    ]
    for pattern in part_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        print(f"   Pattern '{pattern}': {len(matches)} matches")
        if matches[:5]:
            print(f"   First 5: {matches[:5]}")

    # Step 3: Find serial numbers
    print("\n3. Looking for serial numbers...")
    serial_pattern = r'\b([A-Z0-9]{10,14})\b'
    serials = re.findall(serial_pattern, text)
    print(f"   Found {len(serials)} potential serials")
    if serials[:10]:
        print(f"   First 10: {serials[:10]}")

    # Step 4: Full extraction
    print("\n4. Running full extraction...")
    result = extract_assets_from_pdf(pdf_path)

    if result:
        print(f"   PO Number: {result.get('po_number')}")
        print(f"   Total Quantity: {result.get('total_quantity')}")
        print(f"   Assets found: {len(result.get('assets', []))}")

        if result.get('assets'):
            print("\n   First 5 assets:")
            for i, asset in enumerate(result['assets'][:5]):
                print(f"   {i+1}. Serial: {asset.get('serial_num')}, Name: {asset.get('name')}, Model: {asset.get('model')}")
    else:
        print("   ERROR: Extraction returned None")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Try to find a PDF in uploads
        uploads_dir = "static/uploads"
        if os.path.exists(uploads_dir):
            pdfs = [f for f in os.listdir(uploads_dir) if f.endswith('.pdf')]
            if pdfs:
                print(f"Found PDFs in uploads: {pdfs[:5]}")
                print(f"\nUsage: python scripts/test_pdf_extraction.py <path_to_pdf>")
                print(f"Example: python scripts/test_pdf_extraction.py static/uploads/{pdfs[0]}")
            else:
                print("No PDFs found in static/uploads")
        sys.exit(1)

    test_extraction(sys.argv[1])
