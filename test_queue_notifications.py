#!/usr/bin/env python3
"""
Test queue notifications to debug why emails aren't being sent
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from utils.db_manager import DatabaseManager
from models.queue_notification import QueueNotification
from models.queue import Queue
from models.user import User
from models.ticket import Ticket
from utils.queue_notification_sender import send_queue_notifications
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_queue_notifications():
    """Test the queue notification system"""
    with app.app_context():
        try:
            logger.info("🚀 Testing Queue Notification System...")
            
            db_manager = DatabaseManager()
            db_session = db_manager.get_session()
            
            try:
                # 1. Check existing queue notifications
                logger.info("\n📋 Checking existing queue notifications...")
                notifications = db_session.query(QueueNotification).all()
                
                if not notifications:
                    logger.warning("❌ No queue notifications found in database!")
                    logger.info("Please set up notifications in the admin panel first.")
                    return False
                
                logger.info(f"✅ Found {len(notifications)} queue notification(s):")
                for notification in notifications:
                    logger.info(f"   - User: {notification.user.username} ({notification.user.email})")
                    logger.info(f"     Queue: {notification.queue.name} (ID: {notification.queue.id})")
                    logger.info(f"     Notify on Create: {notification.notify_on_create}")
                    logger.info(f"     Notify on Move: {notification.notify_on_move}")
                    logger.info(f"     Active: {notification.is_active}")
                    logger.info(f"     User can access queue: {notification.user.can_access_queue(notification.queue.id)}")
                    logger.info("")
                
                # 2. Check recent tickets
                logger.info("🎫 Checking recent tickets...")
                recent_tickets = db_session.query(Ticket).order_by(Ticket.created_at.desc()).limit(5).all()
                
                if not recent_tickets:
                    logger.warning("❌ No tickets found in database!")
                    return False
                
                logger.info(f"✅ Found {len(recent_tickets)} recent ticket(s):")
                for ticket in recent_tickets:
                    logger.info(f"   - Ticket #{ticket.id}: {ticket.subject}")
                    logger.info(f"     Queue: {ticket.queue.name if ticket.queue else 'No Queue'} (ID: {ticket.queue_id})")
                    logger.info(f"     Created: {ticket.created_at}")
                    logger.info("")
                
                # 3. Test notification sending with the most recent ticket
                if recent_tickets:
                    test_ticket = recent_tickets[0]
                    if test_ticket.queue_id:
                        logger.info(f"🧪 Testing notification sending for ticket #{test_ticket.id}...")
                        try:
                            send_queue_notifications(test_ticket, action_type="created")
                            logger.info("✅ Notification sending completed (check logs for details)")
                        except Exception as e:
                            logger.error(f"❌ Error sending notifications: {str(e)}")
                            import traceback
                            logger.error(traceback.format_exc())
                    else:
                        logger.warning("❌ Test ticket has no queue assigned")
                
                return True
                
            finally:
                db_session.close()
                
        except Exception as e:
            logger.error(f"❌ Error in test: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

if __name__ == '__main__':
    success = test_queue_notifications()
    if success:
        print("\n🎉 Queue notification test completed!")
    else:
        print("\n❌ Queue notification test failed!")
        sys.exit(1)