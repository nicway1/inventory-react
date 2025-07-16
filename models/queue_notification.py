from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base
from datetime import datetime

class QueueNotification(Base):
    """Model for queue notification subscriptions"""
    __tablename__ = 'queue_notifications'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    queue_id = Column(Integer, ForeignKey('queues.id'), nullable=False)
    notify_on_create = Column(Boolean, default=True, nullable=False)  # Notify when ticket is created in queue
    notify_on_move = Column(Boolean, default=True, nullable=False)    # Notify when ticket is moved to queue
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="queue_notifications")
    queue = relationship("Queue", back_populates="notifications")
    
    def __repr__(self):
        return f'<QueueNotification {self.user.username if self.user else "Unknown"} -> {self.queue.name if self.queue else "Unknown"}>'