#!/usr/bin/env python3
import sqlite3
import os
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


def check_database_schema(db_path):
    """Check the schema of a database file"""
    logger.info("\n=== Checking {db_path} ===")
    
    if not os.path.exists(db_path):
        logger.info("Database file does not exist: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if tickets table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tickets'")
        if not cursor.fetchone():
            logger.info("tickets table does not exist in this database")
            return
        
        # Get table structure
        cursor.execute("PRAGMA table_info(tickets)")
        columns = cursor.fetchall()
        
        logger.info("Found {len(columns)} columns in tickets table")
        
        # Look for shipping tracking columns
        shipping_columns = [col for col in columns if 'shipping_tracking' in col[1]]
        logger.info("Shipping tracking columns: {len(shipping_columns)}")
        
        for col in shipping_columns:
            logger.info("  - {col[1]} ({col[2]})")
        
        # Check specifically for the problematic column
        column_names = [col[1] for col in columns]
        problem_columns = ['shipping_tracking_3', 'shipping_tracking_4', 'shipping_tracking_5']
        
        for problem_col in problem_columns:
            if problem_col in column_names:
                logger.info("  ✓ {problem_col} EXISTS")
            else:
                logger.info("  ✗ {problem_col} MISSING")
        
    except Exception as e:
        logger.info("Error checking database: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def main():
    logger.info("=== Database Schema Checker ===")
    
    # Check both database files
    db_files = [
        'inventory.db',
        'instance/inventory.db'
    ]
    
    for db_file in db_files:
        check_database_schema(db_file)
    
    logger.info("\n=== Summary ===")
    logger.info("If columns are missing from instance/inventory.db, that's likely the problem.")
    logger.info("The Flask app probably uses the instance directory database.")

if __name__ == "__main__":
    main() 