#!/usr/bin/env python3
"""
Migration script to add case_progress column to feature_requests table (MySQL version)
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

def add_case_progress_column():
    """Add case_progress column to feature_requests table"""
    try:
        # Connect to the database
        conn = get_mysql_connection()
        cursor = conn.cursor()

        logger.info(f"Connected to MySQL database: {conn.db.decode()}")

        # Check if column already exists
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'feature_requests'
            AND COLUMN_NAME = 'case_progress'
        """)

        exists = cursor.fetchone()[0]

        if exists:
            logger.info("✓ Column 'case_progress' already exists in feature_requests table")
            cursor.close()
            conn.close()
            return True

        # Add the column
        logger.info("Adding 'case_progress' column to feature_requests table...")
        cursor.execute("""
            ALTER TABLE feature_requests
            ADD COLUMN case_progress INT DEFAULT 0
            COMMENT 'Progress percentage 0-100'
        """)

        conn.commit()
        logger.info("✓ Migration completed successfully!")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        logger.error(f"✗ Migration failed: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == '__main__':
    logger.info("Running feature case_progress migration...")
    success = add_case_progress_column()
    exit(0 if success else 1)
