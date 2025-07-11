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
        logger.info("[DEBUG] Comment.__init__ for ID {id}: Raw content: '{content}'")
        # Store the raw content in _raw_content for the property to use
        self._raw_content = content
        # Also set the column value directly (used by SQLAlchemy)
        self.content = content  # This sets the column value
        self.created_at = created_at or datetime.now()
        self.mentions = self._parse_mentions(content)
        logger.info("[DEBUG] Comment.__init__ for ID {id}: Found mentions: {self.mentions}")
        self.attachments = []

    @property
    def content(self):
        """Return content with formatted @mentions"""
        try:
            # Check if this is a database-loaded instance without _raw_content
            if not hasattr(self, '_raw_content'):
                # Return the column value directly if _raw_content isn't available
                return self.__dict__.get('content', '')
            
            # Otherwise use the formatting logic for JSON-loaded comments
            formatted = self._format_mentions(self._raw_content)
            logger.info("[DEBUG] Comment.content property for ID {self.id}: Raw: '{self._raw_content}' → Formatted: '{formatted}'")
            return formatted
        except Exception as e:
            logger.info("[ERROR] Error in content property for comment {self.id}: {e}")
            # Return the raw content value or an empty string as fallback
            return self.__dict__.get('content', '')
            
    @content.setter
    def content(self, value):
        """Set the content column value"""
        self.__dict__['content'] = value

    @staticmethod
    def create(ticket_id, user_id, content):
        import random
        comment_id = random.randint(1000, 9999)
        logger.info("[DEBUG] Comment.create: ID {comment_id}, content before processing: '{content}'")
        
        # Check if content already contains mention spans
        if "<span class=\"mention\">" in content:
            logger.info("[DEBUG] Comment.create: Content already has mention spans, extracting usernames")
            # Extract just the usernames from mentions
            pattern = r'<span class="mention">@([^<]+)</span>'
            usernames = re.findall(pattern, content)
            logger.info("[DEBUG] Comment.create: Found usernames in spans: {usernames}")
            
            # Rebuild the content with just plain @mentions
            content = re.sub(pattern, lambda m: f"@{m.group(1)}", content)
            logger.info("[DEBUG] Comment.create: Content after removing spans: '{content}'")
        
        return Comment(comment_id, ticket_id, user_id, content)

    def _parse_mentions(self, content):
        """Extract @mentions from comment content"""
        logger.info("[DEBUG] Comment._parse_mentions for ID {self.id}: Content: '{content}'")
        
        # Check if content contains HTML mentions or plain text mentions
        if "<span class=\"mention\">" in content:
            logger.info("[DEBUG] Comment._parse_mentions: Content has HTML mentions")
            # Extract usernames from HTML mentions
            pattern = r'<span class="mention">@([^<]+)</span>'
            mentions = re.findall(pattern, content)
            logger.info("[DEBUG] Comment._parse_mentions: Extracted mentions from HTML: {mentions}")
            return mentions
        else:
            logger.info("[DEBUG] Comment._parse_mentions: Content has plain text mentions")
            # Extract plain text mentions
            mention_pattern = r'@(\w+)'
            mentions = re.findall(mention_pattern, content)
            logger.info("[DEBUG] Comment._parse_mentions: Extracted plain text mentions: {mentions}")
            return mentions

    def _format_mentions(self, content):
        """Format @mentions with HTML"""
        logger.info("[DEBUG] Comment._format_mentions for ID {self.id}: Content before formatting: '{content}'")
        
        # Only format if not already formatted
        if "<span class=\"mention\">" not in content:
            logger.info("[DEBUG] Comment._format_mentions: Content needs formatting")
            mention_pattern = r'@(\w+)'
            formatted = re.sub(
                mention_pattern,
                lambda m: f'<span class="mention">@{m.group(1)}</span>',
                content
            )
            logger.info("[DEBUG] Comment._format_mentions: Content after formatting: '{formatted}'")
            return formatted
        
        logger.info("[DEBUG] Comment._format_mentions: Content already formatted, returning as is")
        return content 