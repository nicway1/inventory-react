from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from models.base import Base


class QueueFolder(Base):
    """Folder to group queues together (iOS home screen style)"""
    __tablename__ = 'queue_folders'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    color = Column(String(20), default='blue')  # Folder color theme
    icon = Column(String(50), default='folder')  # Icon name
    display_order = Column(Integer, default=0)  # Sort order in grid
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    queues = relationship("Queue", back_populates="folder")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
            'icon': self.icon,
            'display_order': self.display_order,
            'queues': [q.to_dict() for q in self.queues] if self.queues else [],
            'queue_count': len(self.queues) if self.queues else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
