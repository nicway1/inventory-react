#!/usr/bin/env python3
"""
Script to fix accessory quantity discrepancies.
The bug was that ASSET_INTAKE tickets were only updating available_quantity
but not total_quantity, causing available > total (impossible state).

This script fixes accessories where available_quantity > total_quantity
by setting total_quantity = available_quantity.

Usage: python fix_accessory_quantities.py
"""

import sqlite3
import os

# Determine database path
if os.path.exists('/home/nicway/inventory/inventory.db'):
    DB_PATH = '/home/nicway/inventory/inventory.db'
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory.db')

def fix_quantities():
    print(f"Fixing accessory quantities in: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Find accessories where available_quantity > total_quantity
    cursor.execute("""
        SELECT id, name, total_quantity, available_quantity
        FROM accessories
        WHERE available_quantity > total_quantity
    """)

    problematic = cursor.fetchall()

    if not problematic:
        print("No accessories found with quantity discrepancies.")
        conn.close()
        return

    print(f"Found {len(problematic)} accessories with available > total:")
    for acc in problematic:
        print(f"  ID {acc[0]}: {acc[1]} - total={acc[2]}, available={acc[3]}")

    # Fix by setting total_quantity = available_quantity
    cursor.execute("""
        UPDATE accessories
        SET total_quantity = available_quantity
        WHERE available_quantity > total_quantity
    """)

    rows_updated = cursor.rowcount
    conn.commit()

    # Verify the fix
    cursor.execute("""
        SELECT id, name, total_quantity, available_quantity
        FROM accessories
        WHERE id IN ({})
    """.format(','.join(str(acc[0]) for acc in problematic)))

    fixed = cursor.fetchall()
    print(f"\nFixed {rows_updated} accessories:")
    for acc in fixed:
        print(f"  ID {acc[0]}: {acc[1]} - total={acc[2]}, available={acc[3]}")

    conn.close()
    print("\nDone!")

if __name__ == '__main__':
    fix_quantities()
