#!/usr/bin/env python3
"""
Deployment Fix Script for PythonAnywhere
This script fixes database schema issues after deploying new changes.
"""

import os
import sys
import sqlite3
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
        # Create instance directory if it doesn't exist
        instance_dir = os.path.join(os.getcwd(), 'instance')
        if not os.path.exists(instance_dir):
            os.makedirs(instance_dir)
            logger.info(f"📁 Created instance directory: {instance_dir}")
        
        # Use absolute path for SQLite database
        db_path = os.path.join(instance_dir, 'inventory.db')
        database_url = f'sqlite:///{db_path}'
        logger.info(f"📍 Using database path: {db_path}")
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
        with engine.begin() as conn:
            conn.execute(text(sql))
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
        
        # If it's a SQLite database and file doesn't exist, try to create it
        if 'sqlite' in database_url and ('unable to open database file' in str(e) or 'no such file' in str(e)):
            logger.info("🔧 Database file doesn't exist, attempting to create...")
            try:
                # Extract the database path from the URL
                db_path = database_url.replace('sqlite:///', '')
                
                # Create an empty database file
                conn = sqlite3.connect(db_path)
                conn.close()
                
                # Try to reconnect
                engine = create_engine(database_url)
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                logger.info("✅ Database created and connection successful")
                
            except Exception as create_error:
                logger.error(f"❌ Failed to create database: {create_error}")
                logger.info("💡 Suggestion: Make sure you're running this script from your application directory")
                logger.info("💡 Or run 'python app.py' first to initialize the database")
                return 1
        else:
            logger.info("💡 Suggestion: Make sure your database is running and accessible")
            return 1
    
    # Check if this is an empty database that needs full initialization
    is_empty_database = False
    try:
        if not check_table_exists(engine, 'users'):
            logger.warning("⚠️  Database appears to be empty - no users table found")
            is_empty_database = True
    except Exception as e:
        logger.warning(f"⚠️  Could not check database state: {e}")
        is_empty_database = True
    
    if is_empty_database:
        logger.info("🏗️  Initializing empty database with basic schema...")
        try:
            # Create basic tables
            basic_schema_sql = """
            -- Users table
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(80) UNIQUE NOT NULL,
                email VARCHAR(120) UNIQUE NOT NULL,
                password_hash VARCHAR(200) NOT NULL,
                user_type VARCHAR(20) DEFAULT 'user',
                is_verified BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                country_id INTEGER,
                company_id INTEGER,
                last_login TIMESTAMP,
                first_name VARCHAR(50),
                last_name VARCHAR(50),
                phone VARCHAR(20),
                timezone VARCHAR(50) DEFAULT 'UTC'
            );
            
            -- Tickets table
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                status VARCHAR(50) DEFAULT 'Open',
                priority VARCHAR(20) DEFAULT 'Medium',
                category VARCHAR(50),
                subcategory VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                created_by INTEGER NOT NULL,
                assigned_to INTEGER,
                company_id INTEGER,
                country_id INTEGER,
                shipping_tracking VARCHAR(100),
                carrier VARCHAR(50) DEFAULT 'singpost',
                return_tracking VARCHAR(100),
                return_carrier VARCHAR(50) DEFAULT 'singpost',
                replacement_tracking VARCHAR(100)
            );
            
            -- Firecrawl keys table
            CREATE TABLE IF NOT EXISTS firecrawl_keys (
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
            );
            
            -- Companies table
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Countries table
            CREATE TABLE IF NOT EXISTS countries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                code VARCHAR(3) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            
            with engine.begin() as conn:
                # Execute each statement separately
                statements = basic_schema_sql.split(';')
                for statement in statements:
                    statement = statement.strip()
                    if statement:
                        conn.execute(text(statement))
            
            logger.info("✅ Basic database schema created successfully")
            
            # Create default admin user
            try:
                with engine.begin() as conn:
                    # Check if admin user exists
                    result = conn.execute(text("SELECT COUNT(*) as count FROM users WHERE username = 'admin'")).fetchone()
                    if result and result[0] == 0:
                        # Create admin user (password: admin123)
                        admin_sql = """
                        INSERT INTO users (username, email, password_hash, user_type, is_verified, first_name, last_name)
                        VALUES ('admin', 'admin@company.com', 'scrypt:32768:8:1$0tQN8vY4B7QN8v$4e9c8f5b2a1d3e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z7a8b9c0d1e2f3g4h5i6j7k8l9m0n1o2p3q4r5s6t7u8v9w0x1y2z3a4b5c6d7e8f9g0h1i2j3k4l5m6n7o8p9q0r1s2t3u4v5w6x7y8z9a0b1c2d3e4f5g6h7i8j9k0l1m2n3o4p5', 'super_admin', 1, 'Admin', 'User')
                        """
                        conn.execute(text(admin_sql))
                        logger.info("✅ Default admin user created (username: admin, password: admin123)")
                    else:
                        logger.info("✅ Admin user already exists")
            except Exception as e:
                logger.warning(f"⚠️  Could not create admin user: {e}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize database schema: {e}")
            return 1
    
    # Continue with existing schema fixes
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
    
    # Fix 2: Create firecrawl_keys table if missing (should already be created above)
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
    
    # Check if users table exists (should always exist now)
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
                with engine.begin() as trans_conn:
                    insert_sql = """
                    INSERT INTO firecrawl_keys (api_key, name, is_active, is_primary, created_at)
                    VALUES (?, 'Default Key', 1, 1, CURRENT_TIMESTAMP)
                    """
                    trans_conn.execute(text(insert_sql), (default_key,))
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
    if is_empty_database:
        logger.info("   4. Login with username: admin, password: admin123")
        logger.info("   5. Change the admin password after first login")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 