#!/usr/bin/env python3
"""
Script to extract Order IDs from ticket descriptions and store them in firstbaseorderid field
"""

import re
import logging
import sqlite3
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database path
DB_PATH = 'inventory.db'

def extract_order_id_from_description(description):
    """
    Extract Order ID from ticket description
    Looks for patterns like:
    - Order ID: <uuid>
    - order_id: <uuid>
    - Order Id: <uuid>
    """
    if not description:
        return None

    # Pattern to match Order ID followed by a UUID or alphanumeric ID
    patterns = [
        r'-\s*Order ID:\s*([a-fA-F0-9-]{36})',  # With dash prefix (CSV import format)
        r'Order ID:\s*([a-fA-F0-9-]{36})',  # UUID format
        r'order_id:\s*([a-fA-F0-9-]{36})',  # lowercase
        r'Order Id:\s*([a-fA-F0-9-]{36})',  # Mixed case
        r'-\s*Order ID:\s*(\S+)',  # With dash prefix, any format
        r'Order ID:\s*(\S+)',  # Any non-whitespace after Order ID
        r'order_id:\s*(\S+)',  # Any non-whitespace (lowercase)
    ]

    for pattern in patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            order_id = match.group(1).strip()
            # Remove any trailing punctuation
            order_id = order_id.rstrip('.,;:')
            return order_id

    return None

def update_tickets_with_order_ids():
    """
    Find all tickets with Order IDs in descriptions and update firstbaseorderid field
    """
    if not os.path.exists(DB_PATH):
        logger.error(f"Database not found at {DB_PATH}")
        return False

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Get all tickets that don't have firstbaseorderid set
        cursor.execute("""
            SELECT id, subject, description, firstbaseorderid
            FROM tickets
            WHERE firstbaseorderid IS NULL OR firstbaseorderid = ''
        """)
        tickets = cursor.fetchall()

        logger.info(f"Found {len(tickets)} tickets without Order IDs")

        updated_count = 0
        skipped_count = 0

        for ticket_id, subject, description, current_order_id in tickets:
            order_id = extract_order_id_from_description(description)

            if order_id:
                logger.info(f"Ticket #{ticket_id}: Extracted Order ID: {order_id}")
                cursor.execute(
                    "UPDATE tickets SET firstbaseorderid = ? WHERE id = ?",
                    (order_id, ticket_id)
                )
                updated_count += 1
            else:
                skipped_count += 1

        # Commit all changes
        conn.commit()

        logger.info(f"✅ Successfully updated {updated_count} tickets with Order IDs")
        logger.info(f"⏭️  Skipped {skipped_count} tickets (no Order ID found in description)")

        return True

    except Exception as e:
        logger.error(f"❌ Error updating tickets: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

def preview_extraction():
    """
    Preview what Order IDs would be extracted without making changes
    """
    if not os.path.exists(DB_PATH):
        logger.error(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Get all tickets that don't have firstbaseorderid set but have "Order" in description
        cursor.execute("""
            SELECT id, subject, description
            FROM tickets
            WHERE (firstbaseorderid IS NULL OR firstbaseorderid = '')
            AND description LIKE '%Order%'
            LIMIT 20
        """)
        tickets = cursor.fetchall()

        logger.info(f"\n{'='*80}")
        logger.info("PREVIEW MODE - First 20 tickets without Order IDs")
        logger.info(f"{'='*80}\n")

        found_count = 0

        for ticket_id, subject, description in tickets:
            order_id = extract_order_id_from_description(description)

            if order_id:
                logger.info(f"\n--- Ticket #{ticket_id} ---")
                logger.info(f"Subject: {subject[:80] if subject else 'N/A'}...")
                logger.info(f"Extracted Order ID: {order_id}")
                if description:
                    logger.info(f"Description preview:\n{description[:200]}...\n")
                found_count += 1

        logger.info(f"\n{'='*80}")
        logger.info(f"Found {found_count} tickets with extractable Order IDs (from sample of 20)")
        logger.info(f"{'='*80}\n")

    except Exception as e:
        logger.error(f"❌ Error in preview: {str(e)}")
    finally:
        conn.close()

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--preview':
        logger.info("Running in PREVIEW mode...")
        preview_extraction()
    elif len(sys.argv) > 1 and sys.argv[1] == '--update':
        logger.info("Running UPDATE to extract and save Order IDs...")
        confirmation = input("This will update tickets in the database. Continue? (yes/no): ")
        if confirmation.lower() == 'yes':
            success = update_tickets_with_order_ids()
            if success:
                logger.info("🎉 Update completed successfully!")
            else:
                logger.error("💥 Update failed!")
        else:
            logger.info("Update cancelled by user")
    else:
        logger.info("Usage:")
        logger.info("  python extract_order_ids_from_descriptions.py --preview   # Preview extraction")
        logger.info("  python extract_order_ids_from_descriptions.py --update    # Update database")
