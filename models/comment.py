from datetime import datetime
import re
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


class Comment(Base):
    __tablename__ = 'comments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(String(2000), nullable=False)
    ticket_id = Column(Integer, ForeignKey('tickets.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    ticket = relationship('Ticket', back_populates='comments')
    user = relationship('User', backref='comments')

    def __init__(self, ticket_id=None, user_id=None, content=None, **kwargs):
        super().__init__(**kwargs)
        if ticket_id is not None:
            self.ticket_id = int(ticket_id)
        if user_id is not None:
            self.user_id = int(user_id)
        if content is not None:
            self.content = content

    @property
    def mentions(self):
        """Extract @mentions from comment content (both users and groups)"""
        # Check if content contains HTML mentions or plain text mentions
        if "<span class=\"mention\">" in self.content:
            # Extract usernames from HTML mentions
            pattern = r'<span class="mention">@([^<]+)</span>'
            mentions = re.findall(pattern, self.content)
            return mentions
        else:
            # Extract plain text mentions - updated pattern to handle usernames with dots, @ symbols, etc.
            # This pattern captures usernames that can contain letters, numbers, dots, @ symbols, and hyphens
            mention_pattern = r'@([a-zA-Z0-9._@-]+)'
            mentions = re.findall(mention_pattern, self.content)
            return mentions
    
    @property
    def user_mentions(self):
        """Extract @mentions that are usernames from comment content"""
        return [mention for mention in self.mentions if self._is_user_mention(mention)]
    
    @property
    def group_mentions(self):
        """Extract @mentions that are group names from comment content"""
        return [mention for mention in self.mentions if self._is_group_mention(mention)]
    
    def _is_user_mention(self, mention):
        """Check if a mention is a username by querying the database"""
        try:
            from models.user import User
            from database import SessionLocal
            
            db_session = SessionLocal()
            try:
                user = db_session.query(User).filter(User.username == mention).first()
                return user is not None
            finally:
                db_session.close()
        except Exception as e:
            logger.error(f"Error checking user mention '{mention}': {e}")
            return False
    
    def _is_group_mention(self, mention):
        """Check if a mention is a group name by querying the database"""
        try:
            from models.group import Group
            from database import SessionLocal
            
            db_session = SessionLocal()
            try:
                group = db_session.query(Group).filter(Group.name == mention, Group.is_active == True).first()
                return group is not None
            finally:
                db_session.close()
        except Exception as e:
            logger.error(f"Error checking group mention '{mention}': {e}")
            return False

    @property
    def formatted_content(self):
        """Return content with formatted @mentions"""
        # Only format if not already formatted
        if "<span class=\"mention\">" not in self.content:
            # Use the same pattern as mentions property
            mention_pattern = r'@([a-zA-Z0-9._@-]+)'
            formatted = re.sub(
                mention_pattern,
                lambda m: f'<span class="mention">@{m.group(1)}</span>',
                self.content
            )
            return formatted
        return self.content 