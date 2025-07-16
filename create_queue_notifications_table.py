#!/usr/bin/env python3
"""
Create queue_notifications table for email notifications when tickets are created or moved to queues
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db_manager import DatabaseManager
from models.queue_notification import QueueNotification
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_queue_notifications_table():
    """Create the queue_notifications table"""
    try:
        logger.info("🚀 Creating queue_notifications table...")
        
        db_manager = DatabaseManager()
        
        # Create the table
        QueueNotification.__table__.create(db_manager.engine, checkfirst=True)
        
        logger.info("✅ Queue notifications table created successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating queue_notifications table: {str(e)}")
        return False

if __name__ == '__main__':
    success = create_queue_notifications_table()
    if success:
        print("🎉 Queue notifications table is ready!")
    else:
        print("❌ Failed to create queue notifications table")
        sys.exit(1)