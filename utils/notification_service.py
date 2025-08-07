import logging
from models.notification import Notification
from models.user import User
from utils.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def create_mention_notification(self, mentioned_user_id, commenter_user_id, ticket_id, comment_content):
        """Create a notification for when a user is mentioned in a comment"""
        try:
            # Prevent self-mentions
            if mentioned_user_id == commenter_user_id:
                logger.info(f"Skipping self-mention for user {commenter_user_id}")
                return True  # Not an error, just skip
            
            db_session = self.db_manager.get_session()
            try:
                # Get the commenter's username
                commenter = db_session.query(User).get(commenter_user_id)
                if not commenter:
                    logger.error(f"Commenter user {commenter_user_id} not found")
                    return False
                
                # Get ticket info
                from models.ticket import Ticket
                ticket = db_session.query(Ticket).get(ticket_id)
                if not ticket:
                    logger.error(f"Ticket {ticket_id} not found")
                    return False
                
                # Clean comment content for notification
                import re
                clean_content = re.sub(r'<[^>]+>', '', comment_content)  # Remove HTML tags
                clean_content = clean_content.strip()
                if len(clean_content) > 100:
                    clean_content = clean_content[:100] + "..."
                
                # Create notification
                notification = Notification(
                    user_id=mentioned_user_id,
                    type='mention',
                    title=f'{commenter.username} mentioned you',
                    message=f'{commenter.username} mentioned you in ticket #{ticket.display_id}: "{clean_content}"',
                    reference_type='ticket',
                    reference_id=ticket_id
                )
                
                db_session.add(notification)
                db_session.commit()
                
                logger.info(f"Created mention notification for user {mentioned_user_id}")
                return True
                
            finally:
                db_session.close()
                
        except Exception as e:
            logger.error(f"Error creating mention notification: {str(e)}")
            return False
    
    def get_user_notifications(self, user_id, limit=50, unread_only=False):
        """Get notifications for a user"""
        try:
            db_session = self.db_manager.get_session()
            try:
                query = db_session.query(Notification).filter(Notification.user_id == user_id)
                
                if unread_only:
                    query = query.filter(Notification.is_read == False)
                
                notifications = query.order_by(Notification.created_at.desc()).limit(limit).all()
                return notifications
                
            finally:
                db_session.close()
                
        except Exception as e:
            logger.error(f"Error getting notifications for user {user_id}: {str(e)}")
            return []
    
    def get_unread_count(self, user_id):
        """Get count of unread notifications for a user"""
        try:
            db_session = self.db_manager.get_session()
            try:
                count = db_session.query(Notification).filter(
                    Notification.user_id == user_id,
                    Notification.is_read == False
                ).count()
                return count
                
            finally:
                db_session.close()
                
        except Exception as e:
            logger.error(f"Error getting unread count for user {user_id}: {str(e)}")
            return 0
    
    def mark_notification_as_read(self, notification_id, user_id):
        """Mark a specific notification as read"""
        try:
            db_session = self.db_manager.get_session()
            try:
                notification = db_session.query(Notification).filter(
                    Notification.id == notification_id,
                    Notification.user_id == user_id
                ).first()
                
                if notification:
                    notification.mark_as_read()
                    db_session.commit()
                    return True
                else:
                    logger.warning(f"Notification {notification_id} not found for user {user_id}")
                    return False
                
            finally:
                db_session.close()
                
        except Exception as e:
            logger.error(f"Error marking notification as read: {str(e)}")
            return False
    
    def mark_all_as_read(self, user_id):
        """Mark all notifications as read for a user"""
        try:
            db_session = self.db_manager.get_session()
            try:
                from datetime import datetime
                db_session.query(Notification).filter(
                    Notification.user_id == user_id,
                    Notification.is_read == False
                ).update({
                    'is_read': True,
                    'read_at': datetime.utcnow()
                })
                
                db_session.commit()
                return True
                
            finally:
                db_session.close()
                
        except Exception as e:
            logger.error(f"Error marking all notifications as read for user {user_id}: {str(e)}")
            return False