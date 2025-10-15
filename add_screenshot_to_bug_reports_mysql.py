#!/usr/bin/env python3
"""
Migration script to add screenshot_path column to bug_reports table (MySQL version)
"""

import pymysql
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_mysql_connection():
    """Get MySQL connection from environment variables"""
    # Parse DATABASE_URL or use individual env vars
    database_url = os.environ.get('DATABASE_URL', '')

    if database_url and 'mysql' in database_url:
        # Parse URL: mysql://user:password@host:port/database
        import re
        match = re.match(r'mysql://([^:]+):([^@]+)@([^:]+):?(\d+)?/(.+)', database_url)
        if match:
            user, password, host, port, database = match.groups()
            port = int(port) if port else 3306
        else:
            raise ValueError("Invalid DATABASE_URL format")
    else:
        # Use individual environment variables
        host = os.environ.get('DB_HOST', 'localhost')
        port = int(os.environ.get('DB_PORT', 3306))
        user = os.environ.get('DB_USER', 'root')
        password = os.environ.get('DB_PASSWORD', '')
        database = os.environ.get('DB_NAME', 'inventory')

    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset='utf8mb4'
    )

def add_screenshot_column():
    """Add screenshot_path column to bug_reports table"""
    try:
        # Connect to the database
        conn = get_mysql_connection()
        cursor = conn.cursor()

        logger.info(f"Connected to MySQL database: {conn.db.decode()}")

        # Check if column already exists
        cursor.execute("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'bug_reports'
            AND COLUMN_NAME = 'screenshot_path'
        """)

        result = cursor.fetchone()

        if result:
            logger.info("✅ screenshot_path column already exists in bug_reports table")
            conn.close()
            return

        # Add the screenshot_path column
        logger.info("Adding screenshot_path column to bug_reports table...")
        cursor.execute("""
            ALTER TABLE bug_reports
            ADD COLUMN screenshot_path VARCHAR(500) NULL
        """)

        conn.commit()
        logger.info("✅ screenshot_path column added successfully!")

        # Verify the column was added
        cursor.execute("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'bug_reports'
            AND COLUMN_NAME = 'screenshot_path'
        """)

        result = cursor.fetchone()

        if result:
            logger.info("✅ Verified: screenshot_path column exists in bug_reports table")
        else:
            logger.error("❌ Failed to add screenshot_path column")

        conn.close()

    except Exception as e:
        logger.error(f"❌ Error adding screenshot_path column: {str(e)}")
        raise

if __name__ == "__main__":
    add_screenshot_column()
