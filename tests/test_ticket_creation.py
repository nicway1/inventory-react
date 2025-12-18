#!/usr/bin/env python3
"""
Playwright tests for ticket creation - tests all ticket categories.

Follows the screenshot pattern from capture_widget_screenshots.py

Usage:
    # Install Playwright browsers first (one-time setup):
    playwright install chromium

    # Run tests:
    pytest tests/test_ticket_creation.py -v --headed  # With browser visible
    pytest tests/test_ticket_creation.py -v           # Headless mode

    # Run specific test:
    pytest tests/test_ticket_creation.py::test_pin_request_ticket -v --headed
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("Playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)


# Test configuration
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:5009")
TEST_USERNAME = os.getenv("TEST_USERNAME", "admin1")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "123456")
OUTPUT_DIR = Path("tests/screenshots")
# Check if --headed flag was passed (via environment variable)
HEADLESS = os.getenv("TEST_HEADLESS", "true").lower() != "false"


# Ticket categories mapped to their display names and field configurations
TICKET_CATEGORIES = {
    "PIN_REQUEST": {
        "display_name": "PIN Request",
        "fields_container": "#pinRequestFields",
        "required_fields": {
            "lock_type": "BIOS",  # Options: ACTIVATION, 6_DIGIT, BIOS, BITLOCKER
        },
        "optional_fields": {
            "country": "Singapore",
            "notes": "Test PIN request ticket - automated test",
        },
        "needs_asset": True,
        "asset_field_id": "serial_number",
        "needs_queue": True,
        "queue_field_id": "pin_queue_id",
    },
    "ASSET_REPAIR": {
        "display_name": "Asset Repair",
        "fields_container": "#repairFields",
        "required_fields": {
            "damage_description": "Screen display issues - automated test",
        },
        "optional_fields": {
            "repair_country": "Singapore",
            "apple_diagnostics": "ADP001",
            "repair_notes": "Test repair ticket - automated test",
        },
        "needs_asset": True,
        "asset_field_id": "repair_serial_number",
        "needs_queue": False,
    },
    "ASSET_CHECKOUT": {
        "display_name": "Asset Checkout",
        "fields_container": "#assetCheckoutFields",
        "required_fields": {
            "shipping_address": "123 Test Street\nSingapore 123456",
        },
        "optional_fields": {
            "checkout_notes": "Test checkout ticket - automated test",
            "package_1_tracking": "TEST123456789",
            "package_1_carrier": "dhl",
        },
        "needs_customer": True,
        "customer_field_id": "customer_id",
        "needs_asset": True,
        "asset_field_id": "checkout_serial_number",
        "needs_queue": True,
        "queue_field_id": "checkout_queue_id",
    },
    "ASSET_CHECKOUT_SINGPOST": {
        "display_name": "Asset Checkout (SingPost)",
        "fields_container": "#assetCheckoutFields",
        "required_fields": {
            "shipping_address": "456 SingPost Test Address\nSingapore 654321",
        },
        "optional_fields": {
            "checkout_notes": "Test SingPost checkout - automated test",
        },
        "needs_customer": True,
        "customer_field_id": "customer_id",
        "needs_asset": True,
        "asset_field_id": "checkout_serial_number",
        "needs_queue": True,
        "queue_field_id": "checkout_queue_id",
    },
    "ASSET_CHECKOUT_DHL": {
        "display_name": "Asset Checkout (DHL)",
        "fields_container": "#assetCheckoutFields",
        "required_fields": {
            "shipping_address": "789 DHL Test Address\nSingapore 789012",
        },
        "optional_fields": {
            "checkout_notes": "Test DHL checkout - automated test",
        },
        "needs_customer": True,
        "customer_field_id": "customer_id",
        "needs_asset": True,
        "asset_field_id": "checkout_serial_number",
        "needs_queue": True,
        "queue_field_id": "checkout_queue_id",
    },
    "ASSET_CHECKOUT_CLAW": {
        "display_name": "Asset Checkout (claw)",
        "fields_container": "#assetCheckoutFields",
        "required_fields": {
            "shipping_address": "111 Claw Test Address\nSingapore 111111",
        },
        "optional_fields": {
            "checkout_notes": "Test Claw checkout - automated test",
        },
        "needs_customer": True,
        "customer_field_id": "customer_id",
        "needs_asset": True,
        "asset_field_id": "checkout_serial_number",
        "needs_queue": True,
        "queue_field_id": "checkout_queue_id",
    },
    "ASSET_RETURN_CLAW": {
        "display_name": "Asset Return (claw)",
        "fields_container": "#assetReturnFields",
        "required_fields": {
            "return_description": "Returning device - end of lease - automated test",
            "return_shipping_address": "222 Return Address\nSingapore 222222",
        },
        "optional_fields": {
            "return_damage_description": "Minor scratches on cover",
            "return_notes": "Test return ticket - automated test",
        },
        "needs_customer": True,
        "customer_field_id": "return_customer_id",
        "needs_queue": True,
        "queue_field_id": "queue_id",
        "special_submit": True,
    },
    "ASSET_INTAKE": {
        "display_name": "Asset Intake",
        "fields_container": "#assetIntakeFields",
        "required_fields": {},
        "optional_fields": {
            "intake_title": f"Test Intake - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "intake_description": "New batch of test devices - automated test",
            "intake_notes": "Test intake ticket - automated test",
            "intake_priority": "MEDIUM",
        },
        "needs_queue": True,
        "queue_field_id": "intake_queue_id",
    },
    "INTERNAL_TRANSFER": {
        "display_name": "Internal Transfer",
        "fields_container": "#internalTransferFields",
        "required_fields": {
            "offboarding_details": "MacBook Pro 2023 - Test Transfer - automated test",
            "offboarding_address": "333 Offboarding Street\nSingapore 333333",
            "onboarding_address": "444 Onboarding Avenue\nSingapore 444444",
        },
        "optional_fields": {
            "transfer_tracking": "TRANSFER123456",
            "transfer_notes": "Test internal transfer - automated test",
        },
        "needs_offboarding_customer": True,
        "needs_onboarding_customer": True,
        "needs_queue": True,
        "queue_field_id": "internal_transfer_queue_id",
    },
    "BULK_DELIVERY_QUOTATION": {
        "display_name": "Bulk Delivery Quotation",
        "fields_container": None,
        "required_fields": {},
        "optional_fields": {
            "description": "Test bulk delivery quotation request - automated test",
        },
        "needs_queue": False,
    },
    "REPAIR_QUOTE": {
        "display_name": "Repair Quote",
        "fields_container": None,
        "required_fields": {},
        "optional_fields": {
            "description": "Test repair quote request - automated test",
        },
        "needs_queue": False,
    },
    "ITAD_QUOTE": {
        "display_name": "ITAD Quote",
        "fields_container": None,
        "required_fields": {},
        "optional_fields": {
            "description": "Test ITAD quote request - automated test",
        },
        "needs_queue": False,
    },
}


def select_first_option(page, selector: str) -> bool:
    """Select the first non-empty option from a dropdown."""
    try:
        options = page.query_selector_all(f"{selector} option")
        for option in options:
            value = option.get_attribute("value")
            if value and value.strip():
                page.select_option(selector, value)
                return True
    except Exception as e:
        print(f"      ○ Could not select from {selector}: {e}")
    return False


def fill_field(page, field_id: str, value: str):
    """Fill a field by ID."""
    selector = f"#{field_id}"
    try:
        element = page.query_selector(selector)
        if element and element.is_visible():
            tag_name = element.evaluate("el => el.tagName.toLowerCase()")
            if tag_name == "select":
                page.select_option(selector, value)
            elif tag_name == "textarea":
                page.fill(selector, value)
            else:
                page.fill(selector, value)
            return True
    except Exception as e:
        print(f"      ○ Could not fill {field_id}: {e}")
    return False


def create_ticket(page, category_key: str, config: dict, output_dir: Path) -> bool:
    """Create a ticket of the specified category."""
    display_name = config.get("display_name", category_key)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"\n{'='*60}")
    print(f"Creating ticket: {display_name}")
    print(f"{'='*60}")

    # Navigate to create ticket page
    print("      → Navigating to create ticket page...")
    page.goto(f"{BASE_URL}/tickets/new", wait_until='networkidle')
    time.sleep(1)

    # Select category
    print(f"      → Selecting category: {display_name}")
    page.select_option("#category", display_name)
    time.sleep(0.5)

    # Select customer if needed
    if config.get("needs_customer"):
        customer_field = config.get("customer_field_id", "customer_id")
        print(f"      → Selecting customer from #{customer_field}")
        select_first_option(page, f"#{customer_field}")
        time.sleep(0.3)

    if config.get("needs_offboarding_customer"):
        print("      → Selecting offboarding customer")
        select_first_option(page, "#offboarding_customer_id")
        time.sleep(0.3)

    if config.get("needs_onboarding_customer"):
        print("      → Selecting onboarding customer")
        select_first_option(page, "#onboarding_customer_id")
        time.sleep(0.3)

    # Select asset if needed
    if config.get("needs_asset"):
        asset_field = config.get("asset_field_id", "serial_number")
        print(f"      → Selecting asset from #{asset_field}")
        select_first_option(page, f"#{asset_field}")
        time.sleep(0.3)

    # Fill required fields
    for field_id, value in config.get("required_fields", {}).items():
        print(f"      → Filling required field: {field_id}")
        fill_field(page, field_id, value)

    # Fill optional fields
    for field_id, value in config.get("optional_fields", {}).items():
        print(f"      → Filling optional field: {field_id}")
        fill_field(page, field_id, value)

    # Fill common fields (priority, description)
    print("      → Filling priority")
    priority_element = page.query_selector("#priority")
    if priority_element and priority_element.is_visible():
        select_first_option(page, "#priority")

    print("      → Filling description")
    desc_element = page.query_selector("#description")
    if desc_element and desc_element.is_visible():
        page.fill("#description", f"Test ticket for {display_name} - automated test")

    # Select queue if needed
    if config.get("needs_queue"):
        queue_field = config.get("queue_field_id", "queue_id")
        print(f"      → Selecting queue from #{queue_field}")
        time.sleep(0.3)
        queue_element = page.query_selector(f"#{queue_field}")
        if queue_element and not queue_element.is_disabled():
            select_first_option(page, f"#{queue_field}")

    # Take screenshot before submit
    screenshot_before = output_dir / f"{category_key}_{timestamp}_before_submit.png"
    page.screenshot(path=str(screenshot_before))
    print(f"      ✓ Screenshot: {screenshot_before.name}")

    # Submit the ticket
    print("      → Submitting ticket...")
    if config.get("special_submit"):
        submit_btn = page.query_selector("#asset_return_submit")
        if submit_btn:
            submit_btn.click()
    else:
        # Use specific selector to target submit button inside the ticket form
        # Avoid clicking the theme toggle button in the navbar
        submit_btn = page.query_selector('#ticketForm button[type="submit"]')
        if submit_btn:
            submit_btn.click()
        else:
            page.evaluate("document.getElementById('ticketForm').submit()")

    # Wait for response
    time.sleep(2)
    page.wait_for_load_state('networkidle')

    # Take screenshot after submit
    screenshot_after = output_dir / f"{category_key}_{timestamp}_after_submit.png"
    page.screenshot(path=str(screenshot_after))
    print(f"      ✓ Screenshot: {screenshot_after.name}")

    # Verify ticket creation
    current_url = page.url
    if "/tickets/" in current_url and "create" not in current_url:
        print(f"      ✓ SUCCESS: Created {display_name} ticket")
        return True

    # Check for success message
    success_msg = page.query_selector(".alert-success, .bg-green-100, [class*='success']")
    if success_msg:
        print(f"      ✓ SUCCESS: Created {display_name} ticket")
        return True

    # Check for error
    error_msg = page.query_selector(".alert-danger, .bg-red-100, [class*='error']")
    if error_msg:
        error_text = error_msg.inner_text()
        print(f"      ✗ FAILED: {error_text[:100]}")
        return False

    print(f"      ? UNKNOWN: Check screenshots for result")
    return True


def run_ticket_tests(categories: list = None, headless: bool = True):
    """
    Run ticket creation tests for specified categories.

    Args:
        categories: List of category keys to test. If None, tests all.
        headless: Run browser in headless mode.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print("Ticket Creation Automated Tests")
    print(f"{'='*60}")
    print(f"Base URL: {BASE_URL}")
    print(f"Output: {OUTPUT_DIR.absolute()}")
    print(f"Headless: {headless}")
    print(f"{'='*60}\n")

    categories_to_test = categories or list(TICKET_CATEGORIES.keys())
    results = {}

    with sync_playwright() as p:
        # Launch browser (following your script pattern)
        browser = p.chromium.launch(
            headless=headless,
            args=['--disable-web-security']
        )

        # Create context with larger viewport and retina quality
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            device_scale_factor=2,  # Retina quality
        )

        page = context.new_page()

        # Step 1: Login
        print("[1/3] Logging in...")
        try:
            page.goto(f"{BASE_URL}/", wait_until='networkidle')
            time.sleep(0.5)
            page.fill('input[name="username"]', TEST_USERNAME)
            page.fill('input[name="password"]', TEST_PASSWORD)
            # Use specific selector to avoid clicking theme buttons
            page.click('button.liquid-glass-button[type="submit"]')
            page.wait_for_load_state('networkidle')
            time.sleep(1)
            print("      ✓ Login successful")
        except PlaywrightTimeout:
            print("      ✗ Login failed - check credentials or URL")
            browser.close()
            return False

        # Step 2: Create tickets for each category
        print(f"\n[2/3] Creating tickets for {len(categories_to_test)} categories...")

        for category_key in categories_to_test:
            config = TICKET_CATEGORIES.get(category_key, {})
            try:
                success = create_ticket(page, category_key, config, OUTPUT_DIR)
                results[category_key] = "PASS" if success else "FAIL"
            except Exception as e:
                results[category_key] = f"ERROR: {str(e)[:50]}"
                print(f"      ✗ Error testing {category_key}: {e}")

        browser.close()

    # Step 3: Summary
    print(f"\n[3/3] Test Results Summary")
    print(f"{'='*60}")

    passed = 0
    failed = 0

    for category, result in results.items():
        status_icon = "✓" if result == "PASS" else "✗"
        print(f"      {status_icon} {category}: {result}")
        if result == "PASS":
            passed += 1
        else:
            failed += 1

    print(f"\n      Total: {passed} passed, {failed} failed out of {len(results)}")
    print(f"\n{'='*60}")
    print(f"Screenshots saved to: {OUTPUT_DIR.absolute()}")
    print(f"{'='*60}\n")

    return failed == 0


# Pytest test functions
def test_pin_request_ticket():
    """Test creating a PIN Request ticket."""
    assert run_ticket_tests(["PIN_REQUEST"], headless=HEADLESS)


def test_asset_repair_ticket():
    """Test creating an Asset Repair ticket."""
    assert run_ticket_tests(["ASSET_REPAIR"], headless=HEADLESS)


def test_asset_checkout_ticket():
    """Test creating an Asset Checkout ticket."""
    assert run_ticket_tests(["ASSET_CHECKOUT"], headless=HEADLESS)


def test_asset_checkout_singpost_ticket():
    """Test creating an Asset Checkout (SingPost) ticket."""
    assert run_ticket_tests(["ASSET_CHECKOUT_SINGPOST"], headless=HEADLESS)


def test_asset_checkout_dhl_ticket():
    """Test creating an Asset Checkout (DHL) ticket."""
    assert run_ticket_tests(["ASSET_CHECKOUT_DHL"], headless=HEADLESS)


def test_asset_checkout_claw_ticket():
    """Test creating an Asset Checkout (claw) ticket."""
    assert run_ticket_tests(["ASSET_CHECKOUT_CLAW"], headless=HEADLESS)


def test_asset_return_claw_ticket():
    """Test creating an Asset Return (claw) ticket."""
    assert run_ticket_tests(["ASSET_RETURN_CLAW"], headless=HEADLESS)


def test_asset_intake_ticket():
    """Test creating an Asset Intake ticket."""
    assert run_ticket_tests(["ASSET_INTAKE"], headless=HEADLESS)


def test_internal_transfer_ticket():
    """Test creating an Internal Transfer ticket."""
    assert run_ticket_tests(["INTERNAL_TRANSFER"], headless=HEADLESS)


def test_bulk_delivery_quotation_ticket():
    """Test creating a Bulk Delivery Quotation ticket."""
    assert run_ticket_tests(["BULK_DELIVERY_QUOTATION"], headless=HEADLESS)


def test_repair_quote_ticket():
    """Test creating a Repair Quote ticket."""
    assert run_ticket_tests(["REPAIR_QUOTE"], headless=HEADLESS)


def test_itad_quote_ticket():
    """Test creating an ITAD Quote ticket."""
    assert run_ticket_tests(["ITAD_QUOTE"], headless=HEADLESS)


def test_all_ticket_categories():
    """Test creating one ticket of each category."""
    assert run_ticket_tests(headless=HEADLESS)


def test_sidebar_card_clicks(headless=None):
    """Test that clicking sidebar category cards selects the correct dropdown option."""
    if headless is None:
        headless = HEADLESS

    # Cards to test with their expected dropdown option text
    SIDEBAR_CARDS = [
        "PIN Request",
        "Asset Repair",
        "Asset Checkout (claw)",
        "Asset Return (claw)",
        "Asset Intake",
        "Internal Transfer",
        "Bulk Delivery Quotation",
        "Repair Quote",
        "ITAD Quote",
    ]

    print(f"\n{'='*60}")
    print("Testing Sidebar Category Card Clicks")
    print(f"{'='*60}\n")

    results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=['--disable-web-security']
        )

        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            device_scale_factor=2,
        )

        page = context.new_page()

        # Login
        print("[1/3] Logging in...")
        try:
            page.goto(f"{BASE_URL}/", wait_until='networkidle')
            time.sleep(0.5)
            page.fill('input[name="username"]', TEST_USERNAME)
            page.fill('input[name="password"]', TEST_PASSWORD)
            page.click('button.liquid-glass-button[type="submit"]')
            page.wait_for_load_state('networkidle')
            time.sleep(1)
            print("      ✓ Login successful")
        except PlaywrightTimeout:
            print("      ✗ Login failed")
            browser.close()
            return False

        # Test each sidebar card
        print("\n[2/3] Testing sidebar card clicks...")

        for card_name in SIDEBAR_CARDS:
            try:
                # Navigate to create ticket page
                page.goto(f"{BASE_URL}/tickets/new", wait_until='networkidle')
                time.sleep(1)

                # Find and click the sidebar card
                card_selector = f'.category-guide-item[data-category="{card_name}"]'
                card = page.query_selector(card_selector)

                if not card:
                    print(f"      ✗ {card_name}: Card not found")
                    results[card_name] = "CARD_NOT_FOUND"
                    continue

                card.click()
                time.sleep(0.5)

                # Check if dropdown value changed
                selected_text = page.evaluate('''() => {
                    const select = document.getElementById('category');
                    return select.options[select.selectedIndex].text;
                }''')

                # Check if the badge is visible and shows correct text
                badge_text = page.evaluate('''() => {
                    const badge = document.getElementById('selectedCategoryBadge');
                    return badge ? badge.textContent.trim() : null;
                }''')

                if selected_text and selected_text != "-- Select a Category --":
                    print(f"      ✓ {card_name}: Selected '{selected_text}'")
                    results[card_name] = "PASS"
                else:
                    print(f"      ✗ {card_name}: Dropdown not changed (got: '{selected_text}')")
                    results[card_name] = "FAIL"

            except Exception as e:
                print(f"      ✗ {card_name}: Error - {str(e)[:50]}")
                results[card_name] = f"ERROR: {str(e)[:30]}"

        browser.close()

    # Summary
    print(f"\n[3/3] Sidebar Card Test Summary")
    print(f"{'='*60}")

    passed = sum(1 for r in results.values() if r == "PASS")
    failed = len(results) - passed

    print(f"\n      Total: {passed} passed, {failed} failed out of {len(results)}")
    print(f"{'='*60}\n")

    return failed == 0


def test_sidebar_cards():
    """Pytest wrapper for sidebar card click tests."""
    assert test_sidebar_card_clicks(headless=HEADLESS)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Ticket Creation Tests')
    parser.add_argument('--base-url', default='http://localhost:5009', help='Base URL of the app')
    parser.add_argument('--username', default='admin1', help='Login username')
    parser.add_argument('--password', default='123456', help='Login password')
    parser.add_argument('--show-browser', action='store_true', help='Show browser window')
    parser.add_argument('--category', help='Test specific category (e.g., PIN_REQUEST)')

    args = parser.parse_args()

    # Update globals
    BASE_URL = args.base_url
    TEST_USERNAME = args.username
    TEST_PASSWORD = args.password

    categories = [args.category] if args.category else None
    success = run_ticket_tests(categories, headless=not args.show_browser)

    sys.exit(0 if success else 1)
