#!/usr/bin/env python3
"""
SQLite to MySQL Dump Script
===========================
Creates a MySQL-compatible SQL dump from SQLite database.
No MySQL installation required locally.

Usage:
    python3 sqlite_to_mysql_dump.py

Output:
    mysql_dump.sql - Import this on PythonAnywhere
"""

import sqlite3
import os
import sys
import re
from datetime import datetime

# Configuration
SQLITE_PATH = '/Users/user/invK/inventory/inventory.db'
OUTPUT_FILE = '/Users/user/invK/inventory/mysql_dump.sql'


def get_tables(cursor):
    """Get all table names."""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    return [row[0] for row in cursor.fetchall()]


def get_table_schema(cursor, table_name):
    """Get CREATE TABLE statement and convert to MySQL syntax."""
    cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    result = cursor.fetchone()
    if not result or not result[0]:
        return None

    schema = result[0]

    # Convert SQLite types to MySQL
    schema = re.sub(r'\bINTEGER PRIMARY KEY\b', 'INT AUTO_INCREMENT PRIMARY KEY', schema, flags=re.IGNORECASE)
    schema = re.sub(r'\bINTEGER\b', 'INT', schema, flags=re.IGNORECASE)
    schema = re.sub(r'\bTEXT\b', 'LONGTEXT', schema, flags=re.IGNORECASE)
    schema = re.sub(r'\bREAL\b', 'DOUBLE', schema, flags=re.IGNORECASE)
    schema = re.sub(r'\bBLOB\b', 'LONGBLOB', schema, flags=re.IGNORECASE)
    schema = re.sub(r'\bBOOLEAN\b', 'TINYINT(1)', schema, flags=re.IGNORECASE)

    # Fix VARCHAR without length - add default length of 255
    schema = re.sub(r'\bVARCHAR\b(?!\s*\()', 'VARCHAR(255)', schema, flags=re.IGNORECASE)

    # Remove DEFAULT values from TEXT/LONGTEXT/BLOB columns (MySQL doesn't allow this)
    schema = re.sub(r'(LONGTEXT|LONGBLOB|TEXT|BLOB)\s+DEFAULT\s+\'[^\']*\'', r'\1', schema, flags=re.IGNORECASE)
    schema = re.sub(r'(LONGTEXT|LONGBLOB|TEXT|BLOB)\s+DEFAULT\s+NULL', r'\1', schema, flags=re.IGNORECASE)

    # Remove AUTOINCREMENT (MySQL uses AUTO_INCREMENT which we already added)
    schema = re.sub(r'\bAUTOINCREMENT\b', '', schema, flags=re.IGNORECASE)

    # Quote ALL column names with backticks (handles reserved words like 'condition', 'key', 'index', etc.)
    # Pattern matches: word followed by space and type definition
    def quote_column(match):
        col_name = match.group(1)
        rest = match.group(2)
        # Don't quote if already quoted or if it's a keyword like PRIMARY, FOREIGN, UNIQUE, etc.
        if col_name.upper() in ('PRIMARY', 'FOREIGN', 'UNIQUE', 'CHECK', 'CONSTRAINT', 'KEY', 'INDEX', 'REFERENCES'):
            return match.group(0)
        return f'`{col_name}` {rest}'

    # Match column_name followed by type (handles inline definitions too)
    schema = re.sub(r'\b(\w+)\s+((?:INT|VARCHAR|FLOAT|DOUBLE|DATETIME|LONGTEXT|LONGBLOB|TINYINT|JSON|NUMERIC|DATE|TIME|BOOLEAN)\b[^,\n)]*)', quote_column, schema, flags=re.IGNORECASE)

    # Add IF NOT EXISTS and quote table name
    # Extract and quote table name
    table_match = re.search(r'CREATE TABLE\s+(\w+)', schema, flags=re.IGNORECASE)
    if table_match:
        old_table = table_match.group(0)
        table_name_only = table_match.group(1)
        schema = schema.replace(old_table, f'CREATE TABLE IF NOT EXISTS `{table_name_only}`', 1)
    else:
        schema = schema.replace('CREATE TABLE', 'CREATE TABLE IF NOT EXISTS', 1)

    # Add ENGINE and CHARSET
    schema = schema.rstrip().rstrip(';') + ' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;'

    return schema


def escape_value(value):
    """Escape a value for MySQL INSERT."""
    if value is None:
        return 'NULL'
    elif isinstance(value, bool):
        return '1' if value else '0'
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, bytes):
        return "X'" + value.hex() + "'"
    else:
        # String - escape quotes and backslashes
        escaped = str(value)
        escaped = escaped.replace('\\', '\\\\')
        escaped = escaped.replace("'", "\\'")
        escaped = escaped.replace('\n', '\\n')
        escaped = escaped.replace('\r', '\\r')
        escaped = escaped.replace('\t', '\\t')
        escaped = escaped.replace('\x00', '')
        return f"'{escaped}'"


def dump_table_data(cursor, table_name, output):
    """Dump table data as INSERT statements."""
    try:
        cursor.execute(f"SELECT * FROM [{table_name}]")
        rows = cursor.fetchall()

        if not rows:
            output.write(f"-- Table `{table_name}` is empty\n\n")
            return 0

        # Get column names
        columns = [desc[0] for desc in cursor.description]
        columns_str = ', '.join([f'`{col}`' for col in columns])

        output.write(f"-- Data for table `{table_name}` ({len(rows)} rows)\n")
        output.write(f"LOCK TABLES `{table_name}` WRITE;\n")

        # Write INSERT statements in batches
        batch_size = 100
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i+batch_size]
            values_list = []

            for row in batch:
                values = ', '.join([escape_value(v) for v in row])
                values_list.append(f"({values})")

            output.write(f"INSERT INTO `{table_name}` ({columns_str}) VALUES\n")
            output.write(',\n'.join(values_list))
            output.write(';\n')

        output.write(f"UNLOCK TABLES;\n\n")
        return len(rows)

    except sqlite3.DatabaseError as e:
        output.write(f"-- ERROR reading table `{table_name}`: {e}\n\n")
        return -1


def main():
    print("=" * 60)
    print("SQLite to MySQL Dump Script")
    print("=" * 60)

    if not os.path.exists(SQLITE_PATH):
        print(f"ERROR: SQLite database not found: {SQLITE_PATH}")
        sys.exit(1)

    print(f"\nSource: {SQLITE_PATH}")
    print(f"Output: {OUTPUT_FILE}")

    # Connect to SQLite
    conn = sqlite3.connect(SQLITE_PATH)
    cursor = conn.cursor()

    # Get tables
    tables = get_tables(cursor)
    print(f"\nFound {len(tables)} tables")

    # Open output file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        # Write header
        f.write("-- MySQL dump generated from SQLite\n")
        f.write(f"-- Generated: {datetime.now().isoformat()}\n")
        f.write(f"-- Source: {SQLITE_PATH}\n\n")
        f.write("SET NAMES utf8mb4;\n")
        f.write("SET FOREIGN_KEY_CHECKS = 0;\n")
        f.write("SET SQL_MODE = 'NO_AUTO_VALUE_ON_ZERO';\n\n")

        total_rows = 0
        success_tables = []
        failed_tables = []

        for table in tables:
            print(f"  Processing {table}...", end=" ")

            # Write schema
            schema = get_table_schema(cursor, table)
            if schema:
                f.write(f"-- Table structure for `{table}`\n")
                f.write(f"DROP TABLE IF EXISTS `{table}`;\n")
                f.write(schema + "\n\n")

            # Write data
            rows = dump_table_data(cursor, table, f)

            if rows >= 0:
                print(f"{rows} rows")
                total_rows += rows
                success_tables.append((table, rows))
            else:
                print("FAILED")
                failed_tables.append(table)

        # Write footer
        f.write("SET FOREIGN_KEY_CHECKS = 1;\n")
        f.write("-- Dump complete\n")

    conn.close()

    print("\n" + "=" * 60)
    print("DUMP COMPLETE")
    print("=" * 60)
    print(f"\nSuccessful tables: {len(success_tables)}")
    print(f"Failed tables: {len(failed_tables)}")
    print(f"Total rows: {total_rows}")

    if failed_tables:
        print(f"\nFailed tables: {', '.join(failed_tables)}")

    print(f"\nOutput file: {OUTPUT_FILE}")
    print(f"File size: {os.path.getsize(OUTPUT_FILE) / 1024 / 1024:.2f} MB")

    print("\n" + "=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    print("""
1. Upload mysql_dump.sql to PythonAnywhere

2. On PythonAnywhere, open a MySQL console or Bash:
   mysql -u nicway2 -p nicway2\\$inventory < mysql_dump.sql

   Or in MySQL console:
   source /home/nicway2/mysite3/mysql_dump.sql

3. Update WSGI to use MySQL and reload
""")


if __name__ == '__main__':
    main()
