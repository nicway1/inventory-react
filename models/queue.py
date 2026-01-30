from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from models.base import Base


class Queue(Base):
    __tablename__ = 'queues'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    folder_id = Column(Integer, ForeignKey('queue_folders.id', ondelete='SET NULL'), nullable=True)
    display_order = Column(Integer, default=0)  # Sort order in grid
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    tickets = relationship("Ticket", back_populates="queue")
    company_permissions = relationship("CompanyQueuePermission", back_populates="queue")
    user_permissions = relationship("UserQueuePermission", back_populates="queue")
    notifications = relationship("QueueNotification", back_populates="queue")
    folder = relationship("QueueFolder", back_populates="queues")
    sla_configs = relationship("SLAConfig", back_populates="queue", cascade="all, delete-orphan")
    holidays = relationship("QueueHoliday", back_populates="queue", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'folder_id': self.folder_id,
            'display_order': self.display_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 