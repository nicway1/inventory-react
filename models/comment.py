from datetime import datetime
import re
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from utils.db_manager import Base

class Comment(Base):
    __tablename__ = 'comments'

    id = Column(Integer, primary_key=True)
    content = Column(String(2000), nullable=False)
    ticket_id = Column(Integer, ForeignKey('tickets.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    ticket = relationship('Ticket', back_populates='comments')
    user = relationship('User', backref='comments')

    def __init__(self, id, ticket_id, user_id, content, created_at=None):
        self.id = id
        self.ticket_id = ticket_id
        self.user_id = user_id
        self._raw_content = content
        self.created_at = created_at or datetime.now()
        self.mentions = self._parse_mentions(content)
        self.attachments = []

    @property
    def content(self):
        """Return content with formatted @mentions"""
        return self._format_mentions(self._raw_content)

    @staticmethod
    def create(ticket_id, user_id, content):
        import random
        comment_id = random.randint(1000, 9999)
        return Comment(comment_id, ticket_id, user_id, content)

    def _parse_mentions(self, content):
        """Extract @mentions from comment content"""
        mention_pattern = r'@(\w+)'
        return re.findall(mention_pattern, content)

    def _format_mentions(self, content):
        """Format @mentions with HTML"""
        mention_pattern = r'@(\w+)'
        return re.sub(
            mention_pattern,
            lambda m: f'<span class="mention">@{m.group(1)}</span>',
            content
        ) 