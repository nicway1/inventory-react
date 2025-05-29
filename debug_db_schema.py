#!/usr/bin/env python3
"""
Debug Database Schema Script
This script inspects the database schema to understand the current structure.
"""

import os
import sqlite3
from sqlalchemy import create_engine, inspect
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_url():
    """Get database URL from environment or use default SQLite"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        # Use PythonAnywhere production path
        database_url = 'sqlite:////home/nicway2/inventory/inventory.db'
        logger.info(f"📍 Using production database path: {database_url}")
    else:
        logger.info(f"📍 Using environment database URL: {database_url}")
    return database_url

def main():
    logger.info("🔍 Starting database schema debug...")
    
    # Get database connection
    database_url = get_database_url()
    logger.info(f"📊 Connecting to database: {database_url}")
    
    try:
        engine = create_engine(database_url)
        inspector = inspect(engine)
        
        # List all tables
        tables = inspector.get_table_names()
        logger.info(f"📋 Found {len(tables)} tables: {tables}")
        
        # Check tickets table specifically
        if 'tickets' in tables:
            logger.info("🎫 Inspecting tickets table structure:")
            columns = inspector.get_columns('tickets')
            for i, col in enumerate(columns, 1):
                logger.info(f"   {i}. {col['name']} ({col['type']}) - nullable: {col['nullable']}")
        else:
            logger.warning("⚠️  tickets table not found!")
            
        # Check users table
        if 'users' in tables:
            logger.info("👥 Inspecting users table structure:")
            columns = inspector.get_columns('users')
            for i, col in enumerate(columns, 1):
                logger.info(f"   {i}. {col['name']} ({col['type']}) - nullable: {col['nullable']}")
        else:
            logger.warning("⚠️  users table not found!")
            
        # Check firecrawl_keys table
        if 'firecrawl_keys' in tables:
            logger.info("🔑 Inspecting firecrawl_keys table structure:")
            columns = inspector.get_columns('firecrawl_keys')
            for i, col in enumerate(columns, 1):
                logger.info(f"   {i}. {col['name']} ({col['type']}) - nullable: {col['nullable']}")
        else:
            logger.warning("⚠️  firecrawl_keys table not found!")
            
        # Count records in each table
        logger.info("📊 Record counts:")
        with engine.connect() as conn:
            for table in tables:
                try:
                    result = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                    count = result[0] if result else 0
                    logger.info(f"   {table}: {count} records")
                except Exception as e:
                    logger.warning(f"   {table}: Could not count records - {e}")
        
    except Exception as e:
        logger.error(f"❌ Database inspection failed: {e}")
        return 1
    
    logger.info("✅ Database schema debug completed!")
    return 0

if __name__ == "__main__":
    main() 