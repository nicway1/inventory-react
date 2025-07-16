"""
Queue notification sender utility
Handles sending email notifications when tickets are created or moved to queues
"""

import logging
from utils.db_manager import DatabaseManager
from models.queue_notification import QueueNotification
from models.user import User
from utils.email_sender import send_queue_notification_email

logger = logging.getLogger(__name__)

def send_queue_notifications(ticket, action_type="created"):
    """
    Send queue notifications for a ticket
    
    Args:
        ticket: The ticket object
        action_type: "created" or "moved"
    """
    try:
        if not ticket.queue_id:
            logger.debug(f"Ticket {ticket.id} has no queue, skipping notifications")
            return
        
        db_manager = DatabaseManager()
        db_session = db_manager.get_session()
        
        try:
            # Get all active notifications for this queue
            notifications = db_session.query(QueueNotification).filter(
                QueueNotification.queue_id == ticket.queue_id,
                QueueNotification.is_active == True
            ).all()
            
            if not notifications:
                logger.debug(f"No active notifications found for queue {ticket.queue_id}")
                return
            
            # Filter notifications based on action type
            relevant_notifications = []
            for notification in notifications:
                if action_type == "created" and notification.notify_on_create:
                    relevant_notifications.append(notification)
                elif action_type == "moved" and notification.notify_on_move:
                    relevant_notifications.append(notification)
            
            if not relevant_notifications:
                logger.debug(f"No relevant notifications found for action '{action_type}' on queue {ticket.queue_id}")
                return
            
            logger.info(f"Sending {len(relevant_notifications)} queue notifications for ticket {ticket.id} (action: {action_type})")
            
            # Send notifications
            for notification in relevant_notifications:
                try:
                    # Check if user has permission to view this queue
                    if not notification.user.can_access_queue(ticket.queue_id):
                        logger.debug(f"User {notification.user.username} cannot access queue {ticket.queue_id}, skipping notification")
                        continue
                    
                    # Send the email notification
                    success = send_queue_notification_email(
                        user=notification.user,
                        ticket=ticket,
                        queue=notification.queue,
                        action_type=action_type
                    )
                    
                    if success:
                        logger.info(f"Queue notification sent to {notification.user.email} for ticket {ticket.id}")
                    else:
                        logger.warning(f"Failed to send queue notification to {notification.user.email} for ticket {ticket.id}")
                        
                except Exception as e:
                    logger.error(f"Error sending queue notification to {notification.user.email}: {str(e)}")
                    continue
                    
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error(f"Error in send_queue_notifications: {str(e)}")


def send_queue_move_notifications(ticket, old_queue_id, new_queue_id):
    """
    Send notifications when a ticket is moved between queues
    
    Args:
        ticket: The ticket object
        old_queue_id: Previous queue ID (can be None)
        new_queue_id: New queue ID (can be None)
    """
    try:
        # If ticket was moved to a new queue, send "moved" notifications
        if new_queue_id and new_queue_id != old_queue_id:
            # Temporarily set the queue_id to send notifications
            original_queue_id = ticket.queue_id
            ticket.queue_id = new_queue_id
            send_queue_notifications(ticket, action_type="moved")
            ticket.queue_id = original_queue_id
            
    except Exception as e:
        logger.error(f"Error in send_queue_move_notifications: {str(e)}")