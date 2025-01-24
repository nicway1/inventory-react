import json
import os
from datetime import datetime
from models.comment import Comment

class CommentStore:
    COMMENTS_FILE = 'data/comments.json'

    def __init__(self, user_store, activity_store, ticket_store):
        self.comments = {}
        self.user_store = user_store
        self.activity_store = activity_store
        self.ticket_store = ticket_store
        self.load_comments()

    def load_comments(self):
        if os.path.exists(self.COMMENTS_FILE):
            with open(self.COMMENTS_FILE, 'r') as f:
                comments_data = json.load(f)
                for comment_data in comments_data:
                    comment = Comment(
                        id=comment_data['id'],
                        ticket_id=comment_data['ticket_id'],
                        user_id=comment_data['user_id'],
                        content=comment_data['content'],
                        created_at=datetime.fromisoformat(comment_data['created_at'])
                    )
                    self.comments[comment.id] = comment

    def save_comments(self):
        os.makedirs(os.path.dirname(self.COMMENTS_FILE), exist_ok=True)
        comments_data = []
        for comment in self.comments.values():
            comments_data.append({
                'id': comment.id,
                'ticket_id': comment.ticket_id,
                'user_id': comment.user_id,
                'content': comment.content,
                'created_at': comment.created_at.isoformat()
            })
        with open(self.COMMENTS_FILE, 'w') as f:
            json.dump(comments_data, f, indent=2)

    def add_comment(self, ticket_id, user_id, content):
        comment = Comment.create(ticket_id, user_id, content)
        self.comments[comment.id] = comment
        self.save_comments()
        
        # Notify mentioned users
        if comment.mentions:
            self._notify_mentions(comment)
        
        return comment

    def _notify_mentions(self, comment):
        """Send notifications to mentioned users"""
        ticket = self.ticket_store.get_ticket(comment.ticket_id)
        commenter = self.user_store.get_user_by_id(comment.user_id)
        
        for username in comment.mentions:
            user = self.user_store.get_user_by_username(username)
            if user:
                self.activity_store.add_activity(
                    user_id=user.id,
                    type='mention',
                    content=f"{commenter.username} mentioned you in ticket {ticket.display_id}: {comment.content[:100]}...",
                    reference_id=comment.ticket_id
                )

    def get_ticket_comments(self, ticket_id):
        return [
            comment for comment in self.comments.values()
            if comment.ticket_id == ticket_id
        ] 