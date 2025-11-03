#!/usr/bin/env python3
"""
Add indexes to assets table for better performance
"""
import sqlite3
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_asset_indexes():
    """Add indexes to assets table for commonly filtered/searched columns"""
    db_path = os.path.join(os.path.dirname(__file__), 'inventory.db')

    if not os.path.exists(db_path):
        logger.error(f"Database not found at {db_path}")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get existing indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='assets'")
        existing_indexes = [row[0] for row in cursor.fetchall()]
        logger.info(f"Existing indexes: {existing_indexes}")

        # Define indexes to create
        indexes = [
            ('idx_assets_status', 'CREATE INDEX IF NOT EXISTS idx_assets_status ON assets(status)'),
            ('idx_assets_country', 'CREATE INDEX IF NOT EXISTS idx_assets_country ON assets(country)'),
            ('idx_assets_manufacturer', 'CREATE INDEX IF NOT EXISTS idx_assets_manufacturer ON assets(manufacturer)'),
            ('idx_assets_category', 'CREATE INDEX IF NOT EXISTS idx_assets_category ON assets(category)'),
            ('idx_assets_asset_type', 'CREATE INDEX IF NOT EXISTS idx_assets_asset_type ON assets(asset_type)'),
            ('idx_assets_company_id', 'CREATE INDEX IF NOT EXISTS idx_assets_company_id ON assets(company_id)'),
            ('idx_assets_assigned_to_id', 'CREATE INDEX IF NOT EXISTS idx_assets_assigned_to_id ON assets(assigned_to_id)'),
            ('idx_assets_location_id', 'CREATE INDEX IF NOT EXISTS idx_assets_location_id ON assets(location_id)'),
            ('idx_assets_customer', 'CREATE INDEX IF NOT EXISTS idx_assets_customer ON assets(customer)'),
            ('idx_assets_erased', 'CREATE INDEX IF NOT EXISTS idx_assets_erased ON assets(erased)'),
            # Composite indexes for common query patterns
            ('idx_assets_company_customer', 'CREATE INDEX IF NOT EXISTS idx_assets_company_customer ON assets(company_id, customer)'),
        ]

        created_count = 0
        for index_name, sql in indexes:
            if index_name not in existing_indexes:
                logger.info(f"Creating index: {index_name}...")
                cursor.execute(sql)
                created_count += 1
                logger.info(f"✓ Created {index_name}")
            else:
                logger.info(f"Index {index_name} already exists")

        conn.commit()
        logger.info(f"✓ Successfully created {created_count} indexes")

        # Analyze the table to update statistics
        logger.info("Running ANALYZE to update query optimizer statistics...")
        cursor.execute("ANALYZE assets")
        conn.commit()
        logger.info("✓ ANALYZE completed")

        conn.close()
        return True

    except Exception as e:
        logger.error(f"Error creating indexes: {str(e)}")
        if 'conn' in locals():
            conn.close()
        return False

if __name__ == '__main__':
    logger.info("Starting migration: Add indexes to assets table")
    success = add_asset_indexes()
    if success:
        logger.info("Migration completed successfully!")
    else:
        logger.error("Migration failed!")
