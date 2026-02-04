from sqlalchemy import Column, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from models.base import Base

class UserQueuePermission(Base):
    """Per-user queue permissions (separate from company-level permissions)"""
    __tablename__ = 'user_queue_permissions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    queue_id = Column(Integer, ForeignKey('queues.id', ondelete='CASCADE'), nullable=False)
    can_view = Column(Boolean, default=True)
    can_create = Column(Boolean, default=False)

    # Relationships
    user = relationship('User', back_populates='queue_permissions')
    queue = relationship('Queue', back_populates='user_permissions')

    def to_dict(self):
        """Convert permission to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'queue_id': self.queue_id,
            'can_view': self.can_view,
            'can_create': self.can_create
        }
