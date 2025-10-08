#!/usr/bin/env python3
"""
Verification script to check if all recent changes are deployed
Run this on PythonAnywhere to verify the deployment
"""

import os
import sys

def check_file_content(filepath, search_text, description):
    """Check if a file contains specific text"""
    try:
        if not os.path.exists(filepath):
            print(f"❌ {description}: File not found - {filepath}")
            return False

        with open(filepath, 'r') as f:
            content = f.read()
            if search_text in content:
                print(f"✅ {description}: Found")
                return True
            else:
                print(f"❌ {description}: NOT found")
                return False
    except Exception as e:
        print(f"❌ {description}: Error - {str(e)}")
        return False

def main():
    print("="*60)
    print("DEPLOYMENT VERIFICATION")
    print("="*60)
    print()

    checks = [
        # Order ID in ticket view
        (
            "templates/tickets/view.html",
            "Order ID",
            "Order ID field in ticket view"
        ),
        (
            "templates/tickets/view.html",
            "ticket.firstbaseorderid",
            "Order ID variable reference"
        ),

        # Duplicate prevention in import preview
        (
            "templates/ticket_import_preview.html",
            "ALREADY IMPORTED",
            "Duplicate prevention text"
        ),
        (
            "templates/ticket_import_preview.html",
            "ℹ️ Info:",
            "Changed warning to info message"
        ),

        # API expansions
        (
            "routes/api_simple.py",
            "cpu_type",
            "CPU type field in API"
        ),
        (
            "routes/api_simple.py",
            "current_customer",
            "Current customer field in API"
        ),
        (
            "routes/inventory.py",
            "# Hardware Specs",
            "Hardware specs comment in inventory API"
        ),

        # Accessories export fix
        (
            "templates/inventory/accessories.html",
            "JSON.stringify(selectedIds)",
            "Accessories export fix"
        ),

        # DEVELOPER role
        (
            "models/enums.py",
            "DEVELOPER",
            "DEVELOPER user type"
        ),
        (
            "models/permission.py",
            "can_access_debug_logs",
            "Debug logs permission"
        ),
    ]

    passed = 0
    failed = 0

    for filepath, search_text, description in checks:
        if check_file_content(filepath, search_text, description):
            passed += 1
        else:
            failed += 1
        print()

    print("="*60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*60)

    if failed > 0:
        print()
        print("❌ Some checks failed. Please:")
        print("   1. Make sure you ran 'git pull' in the correct directory")
        print("   2. Check that you're in the right branch (git branch)")
        print("   3. Reload your web app on PythonAnywhere")
        return 1
    else:
        print()
        print("✅ All checks passed! Files are up to date.")
        print("   If changes still don't appear:")
        print("   1. Make sure you RELOADED the web app on PythonAnywhere")
        print("   2. Clear your browser cache (Ctrl+Shift+R)")
        print("   3. Check the error logs on PythonAnywhere")
        return 0

if __name__ == '__main__':
    sys.exit(main())
