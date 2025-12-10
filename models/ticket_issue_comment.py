from datetime import datetime
import re
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship, backref
from models.base import Base
import logging

logger = logging.getLogger(__name__)


class TicketIssueComment(Base):
    """Model for chatter/comments on ticket issues"""
    __tablename__ = 'ticket_issue_comments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    issue_id = Column(Integer, ForeignKey('ticket_issues.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    issue = relationship('TicketIssue', backref='comments')
    user = relationship('User', backref=backref('issue_comments', cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<TicketIssueComment(id={self.id}, issue_id={self.issue_id}, user_id={self.user_id})>"

    @property
    def mentions(self):
        """Extract @mentions from comment content"""
        if "<span class=\"mention\">" in self.content:
            pattern = r'<span class="mention">@([^<]+)</span>'
            mentions = re.findall(pattern, self.content)
            return mentions
        else:
            mention_pattern = r'@([a-zA-Z0-9._@-]+)'
            mentions = re.findall(mention_pattern, self.content)
            return mentions

    @property
    def formatted_content(self):
        """Return content with formatted @mentions"""
        if "<span class=\"mention\">" not in self.content:
            mention_pattern = r'@([a-zA-Z0-9._@-]+)'
            formatted = re.sub(
                mention_pattern,
                lambda m: f'<span class="mention">@{m.group(1)}</span>',
                self.content
            )
            return formatted
        return self.content

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'issue_id': self.issue_id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'content': self.content,
            'formatted_content': self.formatted_content,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'mentions': self.mentions
        }
