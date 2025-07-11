#!/usr/bin/env python3
"""
Migration script to add Firecrawl API key management table
"""

from database import SessionLocal, init_db
from models.firecrawl_key import FirecrawlKey
from config import FIRECRAWL_API_KEY
import os
from dotenv import load_dotenv

def migrate_firecrawl_keys():
    """Add Firecrawl API keys table and migrate existing key"""
    logger.info("Creating Firecrawl API keys table...")
    
    # Initialize database (this will create the table)
    init_db()
    
    session = SessionLocal()
    try:
        # Check if we already have keys
        existing_keys = session.query(FirecrawlKey).count()
        if existing_keys > 0:
            logger.info("Found {existing_keys} existing Firecrawl keys. Skipping migration.")
            return
        
        # Load environment variables
        load_dotenv()
        
        # Get existing key from environment or config
        existing_key = os.environ.get('FIRECRAWL_API_KEY') or FIRECRAWL_API_KEY
        
        if existing_key and existing_key != 'fc-9e1ffc308a01434582ece2625a2a0da7':
            # Migrate existing key
            logger.info("Migrating existing Firecrawl API key...")
            
            firecrawl_key = FirecrawlKey(
                name="Default Key",
                api_key=existing_key,
                usage_count=0,
                limit_count=500,
                is_active=True,
                is_primary=True,
                notes="Migrated from environment configuration"
            )
            
            session.add(firecrawl_key)
            session.commit()
            logger.info("Successfully migrated existing Firecrawl API key as 'Default Key'")
        else:
            logger.info("No existing Firecrawl API key found to migrate.")
            logger.info("You can add new keys through the system configuration page.")
        
    except Exception as e:
        session.rollback()
        logger.info("Error during migration: {str(e)}")
        raise
    finally:
        session.close()
    
    logger.info("Migration completed successfully!")

if __name__ == "__main__":
    migrate_firecrawl_keys() 