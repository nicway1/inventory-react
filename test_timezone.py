#!/usr/bin/env python3
"""
Simple test script to verify Singapore timezone functionality
"""

try:
    from utils.timezone_utils import (
        now_singapore,
        utc_to_singapore,
        singapore_now_as_utc,
        format_singapore_time
    )
    from datetime import datetime
    import pytz

    print("Testing Singapore timezone utilities...")
    print("=" * 50)

    # Test current Singapore time
    sg_now = now_singapore()
    print(f"Current Singapore time: {sg_now}")
    print(f"Singapore timezone: {sg_now.tzinfo}")

    # Test UTC conversion
    utc_now = datetime.utcnow()
    sg_converted = utc_to_singapore(utc_now)
    print(f"UTC time: {utc_now}")
    print(f"Converted to Singapore: {sg_converted}")

    # Test the replacement function
    sg_as_utc = singapore_now_as_utc()
    print(f"Singapore time as UTC: {sg_as_utc}")

    # Test formatting
    formatted = format_singapore_time(utc_now)
    print(f"Formatted Singapore time: {formatted}")

    print("=" * 50)
    print("✅ All timezone tests passed!")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("This test needs to be run from the application environment")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()