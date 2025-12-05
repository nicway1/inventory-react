from sqlalchemy import Column, Integer, String, DateTime, Boolean
from datetime import datetime
from models.base import Base


class CustomIssueType(Base):
    """Model for storing custom issue types created by users"""
    __tablename__ = 'custom_issue_types'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=1)  # Track how often it's used

    def __repr__(self):
        return f"<CustomIssueType(id={self.id}, name='{self.name}')>"

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'is_active': self.is_active,
            'usage_count': self.usage_count
        }
