"""
Queue Holiday Model
Stores holidays per queue for working days calculation
Different queues may serve different countries with different holidays
"""
from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from models.base import Base


class QueueHoliday(Base):
    __tablename__ = 'queue_holidays'

    id = Column(Integer, primary_key=True)
    queue_id = Column(Integer, ForeignKey('queues.id', ondelete='CASCADE'), nullable=False)
    holiday_date = Column(Date, nullable=False)
    name = Column(String(200), nullable=False)  # e.g., "Chinese New Year"
    country = Column(String(100))  # e.g., "Singapore", "USA"
    is_recurring = Column(Boolean, default=False)  # True for annual holidays
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by_id = Column(Integer, ForeignKey('users.id'))

    # Relationships
    queue = relationship("Queue", back_populates="holidays")
    created_by = relationship("User", foreign_keys=[created_by_id])

    # Unique constraint: no duplicate dates per queue
    __table_args__ = (
        UniqueConstraint('queue_id', 'holiday_date', name='uq_queue_holiday_date'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'queue_id': self.queue_id,
            'queue_name': self.queue.name if self.queue else None,
            'holiday_date': self.holiday_date.isoformat() if self.holiday_date else None,
            'name': self.name,
            'country': self.country,
            'is_recurring': self.is_recurring,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
