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
        """Extract @mentions from comment content"""
        # Check if content contains HTML mentions or plain text mentions
        if "<span class=\"mention\">" in self.content:
            # Extract usernames from HTML mentions
            pattern = r'<span class="mention">@([^<]+)</span>'
            mentions = re.findall(pattern, self.content)
            return mentions
        else:
            # Extract plain text mentions
            mention_pattern = r'@(\w+)'
            mentions = re.findall(mention_pattern, self.content)
            return mentions

    @property
    def formatted_content(self):
        """Return content with formatted @mentions"""
        # Only format if not already formatted
        if "<span class=\"mention\">" not in self.content:
            mention_pattern = r'@(\w+)'
            formatted = re.sub(
                mention_pattern,
                lambda m: f'<span class="mention">@{m.group(1)}</span>',
                self.content
            )
            return formatted
        return self.content 