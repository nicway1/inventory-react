import json
import os
from datetime import datetime
from models.comment import Comment
import logging

class CommentStore:
    COMMENTS_FILE = 'data/comments.json'

    def __init__(self, user_store, activity_store, ticket_store):
        self.comments = {}
        self.user_store = user_store
        self.activity_store = activity_store
        self.ticket_store = ticket_store
        print("[DEBUG] Initializing CommentStore")
        self.load_comments()
        print(f"[DEBUG] Loaded {len(self.comments)} comments")

    def load_comments(self):
        print(f"[DEBUG] Loading comments from {self.COMMENTS_FILE}")
        if os.path.exists(self.COMMENTS_FILE):
            try:
                with open(self.COMMENTS_FILE, 'r') as f:
                    comments_data = json.load(f)
                    print(f"[DEBUG] Found {len(comments_data)} comments in file")
                    for comment_data in comments_data:
                        # Fix content with nested mentions
                        content = comment_data['content']
                        original_content = content
                        
                        # Remove nested mention spans
                        while "<span class=\"mention\"><span class=\"mention\">" in content:
                            content = content.replace("<span class=\"mention\"><span class=\"mention\">", "<span class=\"mention\">")
                        
                        # Remove any unmatched closing spans
                        open_spans = content.count("<span")
                        close_spans = content.count("</span>")
                        if close_spans > open_spans:
                            # Too many closing spans, remove the extras
                            content = content.replace("</span>", "", close_spans - open_spans)
                        
                        if content != original_content:
                            print(f"[DEBUG] Fixed comment {comment_data['id']}: '{original_content}' -> '{content}'")
                        
                        comment = Comment(
                            id=comment_data['id'],
                            ticket_id=comment_data['ticket_id'],
                            user_id=comment_data['user_id'],
                            content=content,  # Use fixed content
                            created_at=datetime.fromisoformat(comment_data['created_at'])
                        )
                        self.comments[comment.id] = comment
                        print(f"[DEBUG] Loaded comment {comment.id} for ticket {comment.ticket_id}")
            except Exception as e:
                print(f"[ERROR] Error loading comments: {e}")
                # If there's an error, initialize with empty dict
                self.comments = {}

    def save_comments(self):
        print(f"[DEBUG] Saving {len(self.comments)} comments")
        os.makedirs(os.path.dirname(self.COMMENTS_FILE), exist_ok=True)
        comments_data = []
        for comment in self.comments.values():
            # Make sure content doesn't have nested mention spans
            content = comment.content
            original_content = content
            
            # Remove nested mention spans
            while "<span class=\"mention\"><span class=\"mention\">" in content:
                content = content.replace("<span class=\"mention\"><span class=\"mention\">", "<span class=\"mention\">")
            
            # Remove any unmatched closing spans
            open_spans = content.count("<span")
            close_spans = content.count("</span>")
            if close_spans > open_spans:
                # Too many closing spans, remove the extras
                content = content.replace("</span>", "", close_spans - open_spans)
                
            if content != original_content:
                print(f"[DEBUG] Fixed comment {comment.id} before saving: '{original_content}' -> '{content}'")
                
            comments_data.append({
                'id': comment.id,
                'ticket_id': comment.ticket_id,
                'user_id': comment.user_id,
                'content': content,
                'created_at': comment.created_at.isoformat()
            })
        
        try:
            with open(self.COMMENTS_FILE, 'w') as f:
                json.dump(comments_data, f, indent=2)
            print(f"[DEBUG] Successfully saved {len(comments_data)} comments")
        except Exception as e:
            print(f"[ERROR] Error saving comments: {e}")

    def add_comment(self, ticket_id, user_id, content):
        print(f"[DEBUG] Adding comment for ticket {ticket_id} by user {user_id}: '{content}'")
        comment = Comment.create(ticket_id, user_id, content)
        self.comments[comment.id] = comment
        print(f"[DEBUG] Created comment with ID {comment.id}")
        self.save_comments()
        
        # Notify mentioned users
        if comment.mentions:
            print(f"[DEBUG] Found mentions in comment: {comment.mentions}")
            self._notify_mentions(comment)
        
        return comment

    def _notify_mentions(self, comment):
        """Send notifications to mentioned users"""
        try:
            # Get ticket from database instead of ticket_store
            from utils.store_instances import db_manager
            from models.ticket import Ticket
            from models.user import User
            from utils.email_sender import send_mention_notification_email
            
            db_session = db_manager.get_session()
            try:
                # Get ticket and commenter from database
                ticket = db_session.query(Ticket).get(comment.ticket_id)
                commenter = db_session.query(User).get(comment.user_id)
                
                if not ticket or not commenter:
                    print(f"[WARNING] Could not find ticket {comment.ticket_id} or user {comment.user_id}")
                    return
                
                print(f"[DEBUG] Found ticket {ticket.display_id} and commenter {commenter.username}")
                
                for username in comment.mentions:
                    # Find mentioned user by username
                    mentioned_user = db_session.query(User).filter(User.username == username).first()
                    if mentioned_user:
                        print(f"[DEBUG] Notifying user {username} (ID: {mentioned_user.id}) about mention")
                        
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
                        print(f"[DEBUG] Sending mention email to {mentioned_user.email}")
                        email_sent = send_mention_notification_email(
                            mentioned_user=mentioned_user,
                            commenter=commenter,
                            ticket=ticket,
                            comment_content=comment.content
                        )
                        
                        if email_sent:
                            print(f"[SUCCESS] Mention email sent successfully to {mentioned_user.username}")
                        else:
                            print(f"[WARNING] Failed to send mention email to {mentioned_user.username}")
                            
                    else:
                        print(f"[WARNING] User {username} not found for mention notification")
            finally:
                db_session.close()
                
        except Exception as e:
            print(f"[ERROR] Error sending mention notifications: {e}")
            import traceback
            traceback.print_exc()

    def get_ticket_comments(self, ticket_id):
        comments = [
            comment for comment in self.comments.values()
            if comment.ticket_id == ticket_id
        ]
        print(f"[DEBUG] Retrieved {len(comments)} comments for ticket {ticket_id}")
        for comment in comments:
            print(f"[DEBUG] Comment {comment.id}: '{comment.content}'")
        return comments 

    def delete_ticket_comments(self, ticket_id):
        """Delete all comments associated with a ticket"""
        print(f"[DEBUG] Deleting comments for ticket {ticket_id}")
        
        # Find comment IDs associated with this ticket
        comment_ids_to_delete = [
            comment_id for comment_id, comment in self.comments.items()
            if comment.ticket_id == ticket_id
        ]
        
        # Remove the comments
        deletion_count = 0
        for comment_id in comment_ids_to_delete:
            if comment_id in self.comments:
                del self.comments[comment_id]
                deletion_count += 1
                
        print(f"[DEBUG] Deleted {deletion_count} comments for ticket {ticket_id}")
        
        # Save changes to file
        self.save_comments()
        
        return deletion_count
        
    def cleanup_orphaned_comments(self):
        """Remove comments that reference tickets that no longer exist"""
        print("[DEBUG] Cleaning up orphaned comments")
        
        # Get all current valid ticket IDs from the database
        valid_ticket_ids = set()
        try:
            # Get all ticket IDs from the database
            from models.ticket import Ticket
            db_session = self.ticket_store.db_manager.get_session()
            try:
                tickets = db_session.query(Ticket.id).all()
                valid_ticket_ids = set(t[0] for t in tickets)
            finally:
                db_session.close()
        except Exception as e:
            print(f"[ERROR] Error fetching valid ticket IDs: {e}")
            return 0
            
        print(f"[DEBUG] Found {len(valid_ticket_ids)} valid tickets in database")
        
        # Find comment IDs for comments referencing non-existent tickets
        comment_ids_to_delete = [
            comment_id for comment_id, comment in self.comments.items()
            if comment.ticket_id not in valid_ticket_ids
        ]
        
        # Remove the orphaned comments
        deletion_count = 0
        for comment_id in comment_ids_to_delete:
            if comment_id in self.comments:
                orphaned_ticket_id = self.comments[comment_id].ticket_id
                print(f"[DEBUG] Deleting orphaned comment {comment_id} for non-existent ticket {orphaned_ticket_id}")
                del self.comments[comment_id]
                deletion_count += 1
                
        print(f"[DEBUG] Deleted {deletion_count} orphaned comments")
        
        # Save changes to file if any comments were deleted
        if deletion_count > 0:
            self.save_comments()
            
        return deletion_count 