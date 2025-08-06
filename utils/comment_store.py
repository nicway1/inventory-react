import logging
from models.comment import Comment
from sqlalchemy.orm import joinedload

# Configure logger for this module
logger = logging.getLogger(__name__)

class CommentStore:
    def __init__(self, user_store, activity_store, ticket_store):
        self.user_store = user_store
        self.activity_store = activity_store
        self.ticket_store = ticket_store
        self.db_manager = ticket_store.db_manager
        logger.debug("Initializing database-based CommentStore")

    def add_comment(self, ticket_id, user_id, content):
        """Add a new comment to the database"""
        logger.debug(f"Adding comment for ticket {ticket_id} by user {user_id}: '{content}'")
        
        db_session = self.db_manager.get_session()
        try:
            # Create new comment
            comment = Comment(
                ticket_id=int(ticket_id),
                user_id=int(user_id),
                content=content
            )
            
            db_session.add(comment)
            db_session.commit()
            
            # Refresh to get the ID and relationships
            db_session.refresh(comment)
            
            logger.debug(f"Created comment with ID {comment.id}")
            
            # Notify mentioned users
            if comment.mentions:
                logger.debug(f"Found mentions in comment: {comment.mentions}")
                self._notify_mentions(comment)
            
            return comment
            
        except Exception as e:
            logger.error(f"Error adding comment: {e}")
            db_session.rollback()
            raise
        finally:
            db_session.close()

    def get_ticket_comments(self, ticket_id):
        """Get all comments for a ticket from the database"""
        ticket_id = int(ticket_id)
        
        db_session = self.db_manager.get_session()
        try:
            comments = db_session.query(Comment).options(
                joinedload(Comment.user)
            ).filter(
                Comment.ticket_id == ticket_id
            ).order_by(Comment.created_at.asc()).all()
            
            logger.debug(f"Retrieved {len(comments)} comments for ticket {ticket_id}")
            return comments
            
        except Exception as e:
            logger.error(f"Error retrieving comments for ticket {ticket_id}: {e}")
            return []
        finally:
            db_session.close()

    def delete_ticket_comments(self, ticket_id):
        """Delete all comments associated with a ticket"""
        logger.debug(f"Deleting comments for ticket {ticket_id}")
        
        ticket_id = int(ticket_id)
        
        db_session = self.db_manager.get_session()
        try:
            deletion_count = db_session.query(Comment).filter(
                Comment.ticket_id == ticket_id
            ).delete()
            
            db_session.commit()
            logger.debug(f"Deleted {deletion_count} comments for ticket {ticket_id}")
            return deletion_count
            
        except Exception as e:
            logger.error(f"Error deleting comments for ticket {ticket_id}: {e}")
            db_session.rollback()
            raise
        finally:
            db_session.close()

    def cleanup_orphaned_comments(self):
        """Remove comments that reference tickets that no longer exist"""
        logger.debug("Cleaning up orphaned comments")
        
        db_session = self.db_manager.get_session()
        try:
            # Get all ticket IDs that exist
            from models.ticket import Ticket
            valid_ticket_ids = db_session.query(Ticket.id).all()
            valid_ticket_ids = set(t[0] for t in valid_ticket_ids)
            
            logger.debug(f"Found {len(valid_ticket_ids)} valid tickets in database")
            
            # Delete comments for non-existent tickets
            deletion_count = db_session.query(Comment).filter(
                ~Comment.ticket_id.in_(valid_ticket_ids)
            ).delete(synchronize_session=False)
            
            db_session.commit()
            logger.debug(f"Deleted {deletion_count} orphaned comments")
            return deletion_count
            
        except Exception as e:
            logger.error(f"Error cleaning up orphaned comments: {e}")
            db_session.rollback()
            raise
        finally:
            db_session.close()

    def _notify_mentions(self, comment):
        """Send notifications to mentioned users"""
        try:
            from models.ticket import Ticket
            from models.user import User
            from utils.email_sender import send_mention_notification_email
            
            db_session = self.db_manager.get_session()
            try:
                # Get ticket and commenter from database
                ticket = db_session.query(Ticket).get(comment.ticket_id)
                commenter = db_session.query(User).get(comment.user_id)
                
                if not ticket or not commenter:
                    logger.warning(f"Could not find ticket {comment.ticket_id} or user {comment.user_id}")
                    return
                
                logger.debug(f"Found ticket {ticket.display_id} and commenter {commenter.username}")
                
                for username in comment.mentions:
                    # Find mentioned user by username
                    mentioned_user = db_session.query(User).filter(User.username == username).first()
                    if mentioned_user:
                        logger.debug(f"Notifying user {username} (ID: {mentioned_user.id}) about mention")
                        
                        # Clean up the content for notification (remove HTML tags)
                        import re
                        clean_content = re.sub(r'<span class="mention">(@[^<]+)</span>', r'\1', comment.content)
                        clean_content = re.sub(r'<[^>]+>', '', clean_content)  # Remove any other HTML tags
                        
                        # Add activity notification
                        self.activity_store.add_activity(
                            user_id=mentioned_user.id,
                            type='mention',
                            content=f"{commenter.username} mentioned you in ticket {ticket.display_id}: {clean_content[:100]}...",
                            reference_id=comment.ticket_id
                        )
                        
                        # Send email notification
                        logger.debug(f"Sending mention email to {mentioned_user.email}")
                        email_sent = send_mention_notification_email(
                            mentioned_user=mentioned_user,
                            commenter=commenter,
                            ticket=ticket,
                            comment_content=comment.content
                        )
                        
                        if email_sent:
                            logger.info(f"Mention email sent successfully to {mentioned_user.username}")
                        else:
                            logger.warning(f"Failed to send mention email to {mentioned_user.username}")
                            
                    else:
                        logger.warning(f"User {username} not found for mention notification")
            finally:
                db_session.close()
                
        except Exception as e:
            logger.error(f"Error sending mention notifications: {e}")
            import traceback
            traceback.print_exc()

    # Legacy methods for backwards compatibility (these methods are no longer used)
    def load_comments(self):
        """Legacy method - no longer used with database storage"""
        pass
        
    def save_comments(self):
        """Legacy method - no longer used with database storage"""
        pass