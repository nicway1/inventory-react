#!/usr/bin/env python3
"""
SQLite Database Repair Script
=============================
Attempts to recover data from a corrupted SQLite database.

Usage:
    python repair_sqlite.py
"""

import os
import sys
import sqlite3
import shutil
from datetime import datetime

# Database path
DB_PATH = os.environ.get('SQLITE_DB_PATH', '/home/nicway2/mysite3/inventory.db')
BACKUP_PATH = DB_PATH + '.backup_' + datetime.now().strftime('%Y%m%d_%H%M%S')
RECOVERED_PATH = DB_PATH + '.recovered'


def check_integrity(db_path):
    """Check database integrity."""
    print(f"\n1. Checking integrity of {db_path}...")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchall()
        conn.close()

        if result[0][0] == 'ok':
            print("   Database integrity: OK")
            return True
        else:
            print("   Database integrity issues found:")
            for row in result[:10]:  # Show first 10 issues
                print(f"   - {row[0]}")
            return False
    except Exception as e:
        print(f"   Error checking integrity: {e}")
        return False


def backup_database(db_path, backup_path):
    """Create a backup of the database."""
    print(f"\n2. Creating backup at {backup_path}...")
    try:
        shutil.copy2(db_path, backup_path)
        print("   Backup created successfully")
        return True
    except Exception as e:
        print(f"   Error creating backup: {e}")
        return False


def recover_with_dump(db_path, recovered_path):
    """Try to recover using dump and restore."""
    print(f"\n3. Attempting recovery using dump method...")

    try:
        # Connect to corrupted database
        conn = sqlite3.connect(db_path)
        conn.text_factory = str

        # Get list of tables
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"   Found {len(tables)} tables")

        # Create new database
        if os.path.exists(recovered_path):
            os.remove(recovered_path)

        new_conn = sqlite3.connect(recovered_path)
        new_cursor = new_conn.cursor()

        recovered_tables = []
        failed_tables = []

        for table in tables:
            try:
                # Get table schema
                cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,))
                schema = cursor.fetchone()

                if schema and schema[0]:
                    # Create table in new database
                    new_cursor.execute(schema[0])

                    # Try to copy data
                    try:
                        cursor.execute(f"SELECT * FROM [{table}]")
                        rows = cursor.fetchall()

                        if rows:
                            # Get column count
                            placeholders = ','.join(['?' for _ in rows[0]])
                            new_cursor.executemany(f"INSERT INTO [{table}] VALUES ({placeholders})", rows)

                        recovered_tables.append((table, len(rows) if rows else 0))
                        print(f"   ✓ Recovered {table}: {len(rows) if rows else 0} rows")
                    except sqlite3.DatabaseError as e:
                        # Table data is corrupted, try row by row
                        print(f"   ! Table {table} has corrupted data, trying row-by-row recovery...")
                        recovered_rows = recover_table_rows(cursor, new_cursor, table)
                        if recovered_rows > 0:
                            recovered_tables.append((table, recovered_rows))
                            print(f"   ✓ Partially recovered {table}: {recovered_rows} rows")
                        else:
                            failed_tables.append(table)
                            print(f"   ✗ Could not recover {table}")

            except Exception as e:
                failed_tables.append(table)
                print(f"   ✗ Failed to recover {table}: {e}")

        new_conn.commit()
        new_conn.close()
        conn.close()

        print(f"\n   Recovery complete:")
        print(f"   - Recovered: {len(recovered_tables)} tables")
        print(f"   - Failed: {len(failed_tables)} tables")

        if failed_tables:
            print(f"   - Failed tables: {', '.join(failed_tables)}")

        return recovered_path, recovered_tables, failed_tables

    except Exception as e:
        print(f"   Error during recovery: {e}")
        return None, [], []


def recover_table_rows(source_cursor, dest_cursor, table):
    """Try to recover table data row by row."""
    recovered = 0
    try:
        # Get column info
        source_cursor.execute(f"PRAGMA table_info([{table}])")
        columns = source_cursor.fetchall()
        col_count = len(columns)

        # Try to get row count
        try:
            source_cursor.execute(f"SELECT COUNT(*) FROM [{table}]")
            total = source_cursor.fetchone()[0]
        except:
            total = "unknown"

        # Try to iterate through rows using rowid
        try:
            source_cursor.execute(f"SELECT rowid FROM [{table}]")
            rowids = source_cursor.fetchall()

            for (rowid,) in rowids:
                try:
                    source_cursor.execute(f"SELECT * FROM [{table}] WHERE rowid=?", (rowid,))
                    row = source_cursor.fetchone()
                    if row:
                        placeholders = ','.join(['?' for _ in row])
                        dest_cursor.execute(f"INSERT INTO [{table}] VALUES ({placeholders})", row)
                        recovered += 1
                except:
                    continue
        except:
            pass

    except Exception as e:
        print(f"      Row-by-row recovery error: {e}")

    return recovered


def recover_with_sqlite_cli():
    """Try recovery using SQLite CLI .recover command."""
    print("\n4. Attempting recovery using SQLite CLI .recover command...")

    import subprocess

    try:
        # Check if sqlite3 CLI is available
        result = subprocess.run(['sqlite3', '--version'], capture_output=True, text=True)
        print(f"   SQLite CLI version: {result.stdout.strip()}")

        # Create recovery script
        recover_sql = RECOVERED_PATH + '.sql'

        # Use .recover command
        cmd = f'sqlite3 "{DB_PATH}" ".recover" > "{recover_sql}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if os.path.exists(recover_sql) and os.path.getsize(recover_sql) > 0:
            print(f"   Recovery SQL generated: {recover_sql}")

            # Create new database from recovery SQL
            recovered_cli = RECOVERED_PATH + '.cli'
            if os.path.exists(recovered_cli):
                os.remove(recovered_cli)

            cmd = f'sqlite3 "{recovered_cli}" < "{recover_sql}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            if os.path.exists(recovered_cli):
                print(f"   CLI recovery database created: {recovered_cli}")
                return recovered_cli
        else:
            print("   .recover command produced no output")

    except FileNotFoundError:
        print("   SQLite CLI not available")
    except Exception as e:
        print(f"   CLI recovery error: {e}")

    return None


def compare_databases(original, recovered):
    """Compare row counts between original and recovered databases."""
    print("\n5. Comparing databases...")

    try:
        orig_conn = sqlite3.connect(original)
        rec_conn = sqlite3.connect(recovered)

        orig_cursor = orig_conn.cursor()
        rec_cursor = rec_conn.cursor()

        # Get tables from recovered
        rec_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in rec_cursor.fetchall()]

        print(f"\n   {'Table':<40} {'Original':>10} {'Recovered':>10} {'Status':>10}")
        print("   " + "-" * 72)

        for table in sorted(tables):
            try:
                orig_cursor.execute(f"SELECT COUNT(*) FROM [{table}]")
                orig_count = orig_cursor.fetchone()[0]
            except:
                orig_count = "ERROR"

            try:
                rec_cursor.execute(f"SELECT COUNT(*) FROM [{table}]")
                rec_count = rec_cursor.fetchone()[0]
            except:
                rec_count = "ERROR"

            if orig_count == "ERROR":
                status = "RECOVERED"
            elif orig_count == rec_count:
                status = "OK"
            else:
                status = "PARTIAL"

            print(f"   {table:<40} {str(orig_count):>10} {str(rec_count):>10} {status:>10}")

        orig_conn.close()
        rec_conn.close()

    except Exception as e:
        print(f"   Error comparing: {e}")


def main():
    print("=" * 60)
    print("SQLite Database Repair Script")
    print("=" * 60)
    print(f"\nDatabase: {DB_PATH}")

    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database file not found: {DB_PATH}")
        sys.exit(1)

    # Check integrity
    is_ok = check_integrity(DB_PATH)

    if is_ok:
        print("\nDatabase appears to be OK. No repair needed.")
        return

    # Backup
    backup_database(DB_PATH, BACKUP_PATH)

    # Try dump recovery
    recovered_path, recovered_tables, failed_tables = recover_with_dump(DB_PATH, RECOVERED_PATH)

    # Try CLI recovery as alternative
    cli_recovered = recover_with_sqlite_cli()

    # Compare results
    if recovered_path and os.path.exists(recovered_path):
        compare_databases(DB_PATH, recovered_path)

    print("\n" + "=" * 60)
    print("RECOVERY COMPLETE")
    print("=" * 60)
    print(f"\nFiles created:")
    print(f"  - Backup: {BACKUP_PATH}")
    if recovered_path and os.path.exists(recovered_path):
        print(f"  - Recovered DB: {recovered_path}")
    if cli_recovered and os.path.exists(cli_recovered):
        print(f"  - CLI Recovered: {cli_recovered}")

    print(f"\nNext steps:")
    print(f"  1. Review the recovered database")
    print(f"  2. If satisfied, replace the original:")
    print(f"     cp {RECOVERED_PATH} {DB_PATH}")
    print(f"  3. Then run the MySQL migration again")


if __name__ == '__main__':
    main()
