#!/usr/bin/env python3
"""
Automated Widget Screenshot Capture Tool
Uses Playwright to capture screenshots of all dashboard widgets.

Usage:
    pip install playwright
    playwright install chromium
    python capture_widget_screenshots.py

Options:
    --base-url     Base URL of the app (default: http://localhost:5009)
    --username     Login username (default: admin)
    --password     Login password (default: admin)
    --output-dir   Output directory (default: static/images/widgets)
"""

import os
import sys
import argparse
import time
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("Playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)


# Widget IDs to capture (from dashboard_widget.py)
WIDGETS = [
    'inventory_stats',
    'ticket_stats',
    'customer_stats',
    'queue_stats',
    'weekly_tickets_chart',
    'asset_status_chart',
    'recent_activities',
    'shipments_list',
    'quick_actions',
    'import_tickets',
    'import_assets',
    'system_management',
    'development_console',
    'inventory_audit',
    'clock_widget',
    'reports_link',
    'knowledge_base_link',
    'documents_link',
    'billing_generator',
    'user_overview',
    'view_inventory',
    'view_tickets',
    'view_customers',
    'launchpad',
]

# Map widget IDs to their screenshot filenames
WIDGET_SCREENSHOT_MAP = {
    'inventory_stats': 'inventory_overview.png',
    'ticket_stats': 'ticket_overview.png',
    'customer_stats': 'customer_overview.png',
    'queue_stats': 'support_queues.png',
    'weekly_tickets_chart': 'weekly_tickets_chart.png',
    'asset_status_chart': 'asset_status_chart.png',
    'recent_activities': 'recent_activities.png',
    'shipments_list': 'active_shipments.png',
    'quick_actions': 'quick_actions.png',
    'import_tickets': 'import_tickets.png',
    'import_assets': 'import_assets.png',
    'system_management': 'system_management.png',
    'development_console': 'development_console.png',
    'inventory_audit': 'inventory_audit.png',
    'clock_widget': 'clock_widget.png',
    'reports_link': 'reports.png',
    'knowledge_base_link': 'knowledge_base.png',
    'documents_link': 'documents.png',
    'billing_generator': 'billing_generator.png',
    'user_overview': 'user_overview.png',
    'view_inventory': 'view_inventory.png',
    'view_tickets': 'view_tickets.png',
    'view_customers': 'view_customers.png',
    'launchpad': 'app_launcher.png',
}

# Map widget IDs to their destination URLs (for direct navigation)
WIDGET_URL_MAP = {
    'inventory_stats': '/inventory',
    'ticket_stats': '/tickets',
    'customer_stats': '/customers',
    'queue_stats': '/tickets',  # Shows queue view
    'weekly_tickets_chart': None,  # Chart only, no page
    'asset_status_chart': None,  # Chart only, no page
    'recent_activities': '/activity-log',
    'shipments_list': '/shipments',
    'quick_actions': None,  # Action buttons, no single page
    'import_tickets': '/tickets/import',
    'import_assets': '/inventory/import',
    'system_management': '/admin',
    'development_console': '/development',
    'inventory_audit': '/inventory/audit',
    'clock_widget': None,  # Clock only, no page
    'reports_link': '/reports',
    'knowledge_base_link': '/knowledge-base',
    'documents_link': '/documents',
    'billing_generator': '/billing',
    'user_overview': '/admin/users',
    'view_inventory': '/inventory',
    'view_tickets': '/tickets',
    'view_customers': '/customers',
    'launchpad': None,  # App grid, no single page
}


def capture_widgets(base_url: str, username: str, password: str, output_dir: str, headless: bool = True):
    """Capture screenshots of all widgets."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print("Widget Screenshot Capture Tool")
    print(f"{'='*60}")
    print(f"Base URL: {base_url}")
    print(f"Output: {output_path.absolute()}")
    print(f"Headless: {headless}")
    print(f"{'='*60}\n")

    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(
            headless=headless,
            args=['--disable-web-security']  # Allow local resources
        )

        # Create context with larger viewport
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            device_scale_factor=2,  # Retina quality
        )

        page = context.new_page()

        # Step 1: Login
        print("[1/4] Logging in...")
        try:
            page.goto(f"{base_url}/", wait_until='networkidle')
            page.fill('input[name="username"]', username)
            page.fill('input[name="password"]', password)
            page.click('button[type="submit"]')
            page.wait_for_url('**/dashboard**', timeout=10000)
            print("      ✓ Login successful")
        except PlaywrightTimeout:
            print("      ✗ Login failed - check credentials or URL")
            browser.close()
            return False

        # Step 2: Navigate to dashboard
        print("[2/4] Loading dashboard...")
        try:
            page.goto(f"{base_url}/dashboard", wait_until='networkidle')
            time.sleep(2)  # Wait for widgets to render
            print("      ✓ Dashboard loaded")
        except Exception as e:
            print(f"      ✗ Failed to load dashboard: {e}")
            browser.close()
            return False

        # Step 3: Capture each widget
        print("[3/4] Capturing widgets...")
        captured = 0
        failed = []

        for widget_id in WIDGETS:
            filename = WIDGET_SCREENSHOT_MAP.get(widget_id, f"{widget_id}.png")
            filepath = output_path / filename
            dest_url = WIDGET_URL_MAP.get(widget_id)

            try:
                # First, capture the widget itself from the dashboard
                page.goto(f"{base_url}/dashboard", wait_until='networkidle')
                time.sleep(1)

                widget_selector = f'[data-widget-id="{widget_id}"]'
                widget = page.locator(widget_selector)

                # Save widget screenshot with _widget suffix
                widget_filename = filename.replace('.png', '_widget.png')
                widget_filepath = output_path / widget_filename

                if widget.count() > 0:
                    widget.first.scroll_into_view_if_needed()
                    time.sleep(0.5)
                    widget.first.screenshot(path=str(widget_filepath), animations='disabled')
                    print(f"      ✓ {widget_id} -> {widget_filename} (widget)")
                    captured += 1

                # Then capture the destination page if it exists
                if dest_url:
                    page.goto(f"{base_url}{dest_url}", wait_until='networkidle')
                    time.sleep(2)  # Wait for page to fully render

                    # Save page screenshot with _page suffix
                    page_filename = filename.replace('.png', '_page.png')
                    page_filepath = output_path / page_filename
                    page.screenshot(path=str(page_filepath))
                    print(f"      ✓ {widget_id} -> {page_filename} ({dest_url})")
                    captured += 1

            except Exception as e:
                print(f"      ✗ {widget_id}: {str(e)[:50]}")
                failed.append(widget_id)

        # Step 4: Summary
        print(f"\n[4/4] Summary")
        print(f"      Captured: {captured}/{len(WIDGETS)} widgets")
        if failed:
            print(f"      Skipped: {', '.join(failed)}")

        browser.close()

        print(f"\n{'='*60}")
        print(f"Screenshots saved to: {output_path.absolute()}")
        print(f"{'='*60}\n")

        return True


def capture_widget_preview_page(base_url: str, username: str, password: str, output_dir: str, headless: bool = True):
    """
    Alternative method: Capture widgets from a special preview page.
    This creates isolated widget screenshots with consistent styling.
    """

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print("Widget Preview Screenshot Capture")
    print(f"{'='*60}\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            viewport={'width': 800, 'height': 600},
            device_scale_factor=2,
        )
        page = context.new_page()

        # Login first
        print("[1/3] Logging in...")
        page.goto(f"{base_url}/", wait_until='networkidle')
        page.fill('input[name="username"]', username)
        page.fill('input[name="password"]', password)
        page.click('button[type="submit"]')

        try:
            page.wait_for_url('**/dashboard**', timeout=10000)
        except:
            print("      ✗ Login failed")
            browser.close()
            return False

        print("      ✓ Logged in")

        # Capture from widget preview route (if it exists)
        print("[2/3] Capturing widget previews...")
        captured = 0

        for widget_id in WIDGETS:
            filename = WIDGET_SCREENSHOT_MAP.get(widget_id, f"{widget_id}.png")
            filepath = output_path / filename

            try:
                # Try the preview route
                preview_url = f"{base_url}/admin/widget-preview/{widget_id}"
                response = page.goto(preview_url, wait_until='networkidle', timeout=5000)

                if response and response.status == 200:
                    time.sleep(1)  # Wait for rendering
                    page.screenshot(path=str(filepath))
                    print(f"      ✓ {widget_id}")
                    captured += 1
                else:
                    print(f"      ○ {widget_id} (no preview route)")

            except Exception as e:
                print(f"      ○ {widget_id} (skipped)")

        print(f"\n[3/3] Done - {captured} screenshots captured")
        browser.close()

        return True


def main():
    parser = argparse.ArgumentParser(description='Capture widget screenshots')
    parser.add_argument('--base-url', default='http://localhost:5009', help='Base URL of the app')
    parser.add_argument('--username', default='admin', help='Login username')
    parser.add_argument('--password', default='admin', help='Login password')
    parser.add_argument('--output-dir', default='static/images/widget_screenshots', help='Output directory for page screenshots')
    parser.add_argument('--show-browser', action='store_true', help='Show browser window')
    parser.add_argument('--method', choices=['dashboard', 'preview'], default='dashboard',
                       help='Capture method: dashboard (default) or preview page')

    args = parser.parse_args()

    if args.method == 'dashboard':
        success = capture_widgets(
            base_url=args.base_url,
            username=args.username,
            password=args.password,
            output_dir=args.output_dir,
            headless=not args.show_browser
        )
    else:
        success = capture_widget_preview_page(
            base_url=args.base_url,
            username=args.username,
            password=args.password,
            output_dir=args.output_dir,
            headless=not args.show_browser
        )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
