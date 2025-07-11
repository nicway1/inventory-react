from sqlalchemy import create_engine, text
import os
import sqlite3
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


def check_duplicates():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all serial numbers from the database
    cursor.execute("""
        SELECT serial_num, COUNT(*) as count 
        FROM assets 
        WHERE serial_num IS NOT NULL 
        GROUP BY serial_num 
        HAVING COUNT(*) >= 1
        ORDER BY count DESC
    """)
    
    results = cursor.fetchall()
    
    logger.info("Serial numbers in database:")
    logger.info("---------------------------")
    for serial_num, count in results:
        logger.info("Serial number: {serial_num} (appears {count} time(s))")
    
    logger.info("\nTotal unique serial numbers:", len(results))
    
    # Get the serial numbers from your import that are already in the database
    duplicates = [
        'SGWV41VXHGJ', 'SG04HR7F5FJ', 'SC956QXWQVT', 'SC4QHX9P6PM',
        'SFL446RX63T', 'SH3YDC46NW1', 'SGGX1WNLKPM', 'SCP2VY2FCJ4',
        'SG4XPWQR9Y3', 'SF47N2NK923'
    ]
    
    logger.info("\nChecking specific serial numbers from import:")
    logger.info("--------------------------------------------")
    for serial in duplicates:
        cursor.execute("SELECT COUNT(*) FROM assets WHERE serial_num = ?", (serial,))
        count = cursor.fetchone()[0]
        if count > 0:
            logger.info("Serial number {serial} already exists in database")
            # Get more details about this asset
            cursor.execute("""
                SELECT asset_tag, name, model, customer, country 
                FROM assets 
                WHERE serial_num = ?
            """, (serial,))
            details = cursor.fetchone()
            if details:
                logger.info("Details: Asset Tag: {details[0]}, Name: {details[1]}, Model: {details[2]}, Customer: {details[3]}, Country: {details[4]}")
    
    conn.close()

if __name__ == "__main__":
    check_duplicates() 