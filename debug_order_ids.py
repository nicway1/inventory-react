#!/usr/bin/env python3
"""
Debug script to check Order ID extraction and storage
Run this on PythonAnywhere to diagnose why Order IDs aren't being saved
"""

import sqlite3
import os
import re

def check_database_files():
    """Find all database files"""
    print("="*80)
    print("1. CHECKING DATABASE FILES")
    print("="*80)

    db_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.db'):
                db_path = os.path.join(root, file)
                size = os.path.getsize(db_path)
                db_files.append((db_path, size))

    if db_files:
        print(f"\nFound {len(db_files)} database file(s):")
        for db_path, size in db_files:
            print(f"  - {db_path} ({size:,} bytes)")
    else:
        print("\n❌ No database files found!")

    return db_files

def check_config():
    """Check config for database path"""
    print("\n" + "="*80)
    print("2. CHECKING CONFIG FILES")
    print("="*80)

    config_files = ['config.py', 'database.py', '.env']

    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"\n📄 {config_file}:")
            with open(config_file, 'r') as f:
                for line in f:
                    if 'DATABASE' in line.upper() or 'DB' in line.upper():
                        print(f"  {line.strip()}")
        else:
            print(f"\n⚠️  {config_file} not found")

def check_column_exists(db_path):
    """Check if firstbaseorderid column exists"""
    print("\n" + "="*80)
    print(f"3. CHECKING TABLE STRUCTURE IN {db_path}")
    print("="*80)

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get table structure
        cursor.execute("PRAGMA table_info(tickets)")
        columns = cursor.fetchall()

        print("\nColumns in 'tickets' table:")
        has_orderid_column = False
        for col in columns:
            col_id, col_name, col_type = col[0], col[1], col[2]
            if 'orderid' in col_name.lower():
                print(f"  ✅ {col_name} ({col_type})")
                has_orderid_column = True
            else:
                print(f"     {col_name} ({col_type})")

        if not has_orderid_column:
            print("\n❌ No 'firstbaseorderid' column found!")

        conn.close()
        return has_orderid_column

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False

def check_order_ids(db_path):
    """Check Order ID data"""
    print("\n" + "="*80)
    print(f"4. CHECKING ORDER ID DATA IN {db_path}")
    print("="*80)

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Total tickets
        cursor.execute("SELECT COUNT(*) FROM tickets")
        total_tickets = cursor.fetchone()[0]
        print(f"\nTotal tickets: {total_tickets}")

        # Tickets with Order IDs
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE firstbaseorderid IS NOT NULL AND firstbaseorderid != ''")
        with_orderid = cursor.fetchone()[0]
        print(f"Tickets with Order IDs: {with_orderid}")

        # Tickets without Order IDs
        without_orderid = total_tickets - with_orderid
        print(f"Tickets without Order IDs: {without_orderid}")

        # Sample of tickets with Order IDs
        if with_orderid > 0:
            print("\nSample of tickets WITH Order IDs:")
            cursor.execute("SELECT id, subject, firstbaseorderid FROM tickets WHERE firstbaseorderid IS NOT NULL AND firstbaseorderid != '' LIMIT 5")
            for ticket_id, subject, orderid in cursor.fetchall():
                print(f"  Ticket #{ticket_id}: {orderid} - {subject[:60]}...")

        # Check tickets with "Order ID:" in description but no firstbaseorderid
        cursor.execute("""
            SELECT COUNT(*) FROM tickets
            WHERE (firstbaseorderid IS NULL OR firstbaseorderid = '')
            AND description LIKE '%Order ID:%'
        """)
        missing_orderid = cursor.fetchone()[0]
        print(f"\n⚠️  Tickets with 'Order ID:' in description but missing firstbaseorderid: {missing_orderid}")

        if missing_orderid > 0:
            print("\nSample of tickets that SHOULD have Order IDs:")
            cursor.execute("""
                SELECT id, subject, substr(description, 1, 200)
                FROM tickets
                WHERE (firstbaseorderid IS NULL OR firstbaseorderid = '')
                AND description LIKE '%Order ID:%'
                LIMIT 3
            """)
            for ticket_id, subject, desc in cursor.fetchall():
                print(f"\n  Ticket #{ticket_id}: {subject[:60]}")
                # Extract Order ID from description
                match = re.search(r'Order ID:\s*([a-fA-F0-9-]{36})', desc)
                if match:
                    print(f"  Found Order ID in description: {match.group(1)}")
                else:
                    print(f"  Description preview: {desc[:100]}...")

        conn.close()

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

def test_extraction():
    """Test Order ID extraction logic"""
    print("\n" + "="*80)
    print("5. TESTING ORDER ID EXTRACTION LOGIC")
    print("="*80)

    test_descriptions = [
        "Order ID: 5ba37192-c882-474c-a67c-a21e6c1f9a6b",
        "- Order ID: 5ba37192-c882-474c-a67c-a21e6c1f9a6b",
        "order_id: 5ba37192-c882-474c-a67c-a21e6c1f9a6b",
        "No order ID here",
    ]

    patterns = [
        r'-\s*Order ID:\s*([a-fA-F0-9-]{36})',
        r'Order ID:\s*([a-fA-F0-9-]{36})',
        r'order_id:\s*([a-fA-F0-9-]{36})',
    ]

    for desc in test_descriptions:
        print(f"\nTesting: {desc[:60]}...")
        found = False
        for pattern in patterns:
            match = re.search(pattern, desc, re.IGNORECASE)
            if match:
                print(f"  ✅ Matched with pattern: {pattern}")
                print(f"  Extracted: {match.group(1)}")
                found = True
                break
        if not found:
            print(f"  ❌ No match found")

def main():
    print("\n🔍 ORDER ID DEBUGGING SCRIPT")
    print("="*80)

    # 1. Find database files
    db_files = check_database_files()

    # 2. Check config
    check_config()

    # 3. Check each database
    for db_path, size in db_files:
        if check_column_exists(db_path):
            check_order_ids(db_path)

    # 4. Test extraction
    test_extraction()

    print("\n" + "="*80)
    print("SUMMARY & RECOMMENDATIONS")
    print("="*80)
    print("""
If you see tickets with 'Order ID:' in description but missing firstbaseorderid:
1. Make sure you're using the correct database file
2. Run: python3 extract_order_ids_from_descriptions.py --update
3. Type 'yes' when prompted
4. Check the output for any errors

If the column doesn't exist:
1. Run: python3 add_firstbaseorderid_migration.py

If you see multiple database files:
1. Check config.py to see which one is being used by the web app
2. Update DB_PATH in extract_order_ids_from_descriptions.py to match
    """)

if __name__ == '__main__':
    main()
