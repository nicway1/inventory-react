from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from models.base import Base

class Queue(Base):
    __tablename__ = 'queues'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    tickets = relationship("Ticket", back_populates="queue", lazy="dynamic")

    @staticmethod
    def create(name, description=None):
        import random
        queue_id = random.randint(1, 10000)
        return Queue(queue_id, name, description) 