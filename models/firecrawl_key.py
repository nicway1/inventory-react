from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from sqlalchemy.sql import func
from models.base import Base

class FirecrawlKey(Base):
    __tablename__ = 'firecrawl_keys'
    
    id = Column(Integer, primary_key=True)
    api_key = Column(String(255), unique=True, nullable=False)
    name = Column(String(255))
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, nullable=True)
    usage_count = Column(Integer, default=0)
    limit_count = Column(Integer, default=500)  # Token limit per key
    is_primary = Column(Boolean, default=False)  # Mark the current active key
    last_used = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<FirecrawlKey {self.name}>"
    
    @property
    def is_exhausted(self):
        """Check if this key has reached its usage limit"""
        return self.usage_count >= self.limit_count
    
    @property
    def usage_percentage(self):
        """Get usage as percentage"""
        if self.limit_count == 0:
            return 100
        return (self.usage_count / self.limit_count) * 100
    
    @property
    def remaining_tokens(self):
        """Get remaining tokens for this key"""
        return max(0, self.limit_count - self.usage_count)
    
    def increment_usage(self):
        """Increment usage count and update last_used timestamp"""
        self.usage_count += 1
        self.last_used = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        # Deactivate if exhausted
        if self.is_exhausted:
            self.is_active = False
    
    @classmethod
    def get_active_key(cls, session):
        """Get the current primary active key"""
        return session.query(cls).filter_by(is_primary=True, is_active=True).first()
    
    @classmethod
    def get_next_available_key(cls, session):
        """Get the next available key that's not exhausted"""
        return session.query(cls).filter_by(is_active=True).filter(
            cls.usage_count < cls.limit_count
        ).order_by(cls.usage_count.asc()).first()
    
    @classmethod
    def rotate_primary_key(cls, session):
        """Rotate to the next available key"""
        # Clear current primary
        current_primary = cls.get_active_key(session)
        if current_primary:
            current_primary.is_primary = False
        
        # Find next available key
        next_key = cls.get_next_available_key(session)
        if next_key:
            next_key.is_primary = True
            session.commit()
            return next_key
        
        return None 