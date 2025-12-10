from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship, backref
from datetime import datetime
from .base import Base

class AuditSession(Base):
    __tablename__ = 'audit_sessions'
    
    id = Column(String(50), primary_key=True)  # audit_<timestamp>
    country = Column(String(100), nullable=False)
    total_assets = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow)
    started_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    is_active = Column(Boolean, default=True)
    completed_at = Column(DateTime, nullable=True)
    
    # JSON fields stored as text
    scanned_assets = Column(Text, default='[]')  # JSON array of scanned asset data
    missing_assets = Column(Text, default='[]')  # JSON array of missing assets
    unexpected_assets = Column(Text, default='[]')  # JSON array of unexpected assets
    audit_inventory = Column(Text, default='[]')  # JSON array of all assets to audit
    
    # Relationships
    user = relationship("User", backref=backref("audit_sessions", cascade="all, delete-orphan"))
    
    def __repr__(self):
        return f'<AuditSession {self.id} for {self.country}>'