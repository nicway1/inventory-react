from sqlalchemy import Column, Integer, ForeignKey, DateTime, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from models.base import Base
from datetime import datetime

class GroupMembership(Base):
    """Model for group membership relationships"""
    __tablename__ = 'group_memberships'
    
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('groups.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    added_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    added_at = Column(DateTime, default=datetime.utcnow)
    removed_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Ensure unique active membership per user per group
    __table_args__ = (
        UniqueConstraint('group_id', 'user_id', name='uq_group_user_membership'),
    )
    
    # Relationships
    group = relationship("Group", back_populates="memberships")
    user = relationship("User", foreign_keys=[user_id], back_populates="group_memberships")
    added_by = relationship("User", foreign_keys=[added_by_id])
    
    def to_dict(self):
        """Convert membership to dictionary"""
        return {
            'id': self.id,
            'group_id': self.group_id,
            'group_name': self.group.name if self.group else None,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'user_email': self.user.email if self.user else None,
            'added_by_id': self.added_by_id,
            'added_by': self.added_by.username if self.added_by else None,
            'added_at': self.added_at.isoformat() if self.added_at else None,
            'removed_at': self.removed_at.isoformat() if self.removed_at else None,
            'is_active': self.is_active
        }
    
    def __repr__(self):
        status = "active" if self.is_active else "inactive"
        return f'<GroupMembership {self.user.username if self.user else "Unknown"} in {self.group.name if self.group else "Unknown"} ({status})>'