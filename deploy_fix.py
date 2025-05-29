#!/usr/bin/env python3
"""
Deployment Fix Script for PythonAnywhere
This script fixes database schema issues after deploying new changes.
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import OperationalError
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_url():
    """Get database URL from environment or use default SQLite"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        # Default SQLite database path
        database_url = 'sqlite:///instance/inventory.db'
    return database_url

def check_column_exists(engine, table_name, column_name):
    """Check if a column exists in a table"""
    try:
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception:
        return False

def check_table_exists(engine, table_name):
    """Check if a table exists"""
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        return table_name in tables
    except Exception:
        return False

def run_sql_safe(engine, sql, description):
    """Run SQL safely with error handling"""
    try:
        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
        logger.info(f"✅ {description}")
        return True
    except Exception as e:
        logger.warning(f"⚠️  {description} - {str(e)}")
        return False

def main():
    logger.info("🚀 Starting deployment fix script...")
    
    # Get database connection
    database_url = get_database_url()
    logger.info(f"📊 Connecting to database: {database_url}")
    
    try:
        engine = create_engine(database_url)
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection successful")
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return 1
    
    # Fix 1: Add return_carrier column to tickets table if missing
    logger.info("🔧 Checking tickets table for return_carrier column...")
    if check_table_exists(engine, 'tickets'):
        if not check_column_exists(engine, 'tickets', 'return_carrier'):
            run_sql_safe(
                engine,
                "ALTER TABLE tickets ADD COLUMN return_carrier VARCHAR(50) DEFAULT 'singpost'",
                "Added return_carrier column to tickets table"
            )
        else:
            logger.info("✅ return_carrier column already exists in tickets table")
    else:
        logger.warning("⚠️  tickets table does not exist")
    
    # Fix 2: Create firecrawl_keys table if missing
    logger.info("🔧 Checking for firecrawl_keys table...")
    if not check_table_exists(engine, 'firecrawl_keys'):
        firecrawl_table_sql = """
        CREATE TABLE firecrawl_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255),
            is_active BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            usage_count INTEGER DEFAULT 0,
            limit_count INTEGER DEFAULT 500,
            is_primary BOOLEAN DEFAULT 0,
            last_used TIMESTAMP,
            notes TEXT
        )
        """
        run_sql_safe(
            engine,
            firecrawl_table_sql,
            "Created firecrawl_keys table"
        )
    else:
        logger.info("✅ firecrawl_keys table already exists")
        
        # Check if firecrawl_keys table has correct columns
        required_columns = ['api_key', 'name', 'is_active', 'usage_count', 'limit_count']
        for column in required_columns:
            if not check_column_exists(engine, 'firecrawl_keys', column):
                logger.warning(f"⚠️  Missing column {column} in firecrawl_keys table")
    
    # Fix 3: Add updated_at column to firecrawl_keys if missing
    if check_table_exists(engine, 'firecrawl_keys'):
        if not check_column_exists(engine, 'firecrawl_keys', 'updated_at'):
            run_sql_safe(
                engine,
                "ALTER TABLE firecrawl_keys ADD COLUMN updated_at TIMESTAMP",
                "Added updated_at column to firecrawl_keys table"
            )
    
    # Fix 4: Check and fix any other common issues
    logger.info("🔧 Running additional database checks...")
    
    # Check if users table exists (should always exist)
    if not check_table_exists(engine, 'users'):
        logger.error("❌ users table missing - this indicates a major database issue")
        return 1
    
    # Check if tickets table has essential columns
    if check_table_exists(engine, 'tickets'):
        essential_columns = ['id', 'title', 'status', 'created_at']
        missing_columns = []
        for column in essential_columns:
            if not check_column_exists(engine, 'tickets', column):
                missing_columns.append(column)
        
        if missing_columns:
            logger.error(f"❌ tickets table missing essential columns: {missing_columns}")
            return 1
        else:
            logger.info("✅ tickets table has all essential columns")
    
    # Fix 5: Set up default Firecrawl API key if none exists
    logger.info("🔧 Checking for default Firecrawl API key...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) as count FROM firecrawl_keys")).fetchone()
            if result and result[0] == 0:
                # Add default API key from environment
                default_key = os.environ.get('FIRECRAWL_API_KEY', 'fc-default-key')
                insert_sql = """
                INSERT INTO firecrawl_keys (api_key, name, is_active, is_primary, created_at)
                VALUES (?, 'Default Key', 1, 1, CURRENT_TIMESTAMP)
                """
                conn.execute(text(insert_sql), (default_key,))
                conn.commit()
                logger.info("✅ Added default Firecrawl API key")
            else:
                logger.info("✅ Firecrawl API keys already exist")
    except Exception as e:
        logger.warning(f"⚠️  Could not check/add default Firecrawl key: {e}")
    
    logger.info("🎉 Deployment fix script completed successfully!")
    logger.info("📝 Next steps:")
    logger.info("   1. Restart your PythonAnywhere web app")
    logger.info("   2. Check the error logs if issues persist")
    logger.info("   3. Test the application functionality")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 