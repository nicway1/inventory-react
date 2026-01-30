"""
SLA Configuration Model
Stores SLA rules per queue per ticket category
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy import Enum as SQLEnum
from datetime import datetime
from models.base import Base
from models.ticket import TicketCategory


class SLAConfig(Base):
    __tablename__ = 'sla_configs'

    id = Column(Integer, primary_key=True)
    queue_id = Column(Integer, ForeignKey('queues.id', ondelete='CASCADE'), nullable=False)
    ticket_category = Column(SQLEnum(TicketCategory), nullable=False)
    working_days = Column(Integer, nullable=False, default=3)  # SLA in working days
    description = Column(String(500))  # Optional description
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    created_by_id = Column(Integer, ForeignKey('users.id'))

    # Relationships
    queue = relationship("Queue", back_populates="sla_configs")
    created_by = relationship("User", foreign_keys=[created_by_id])

    # Unique constraint: one SLA config per queue + category combination
    __table_args__ = (
        UniqueConstraint('queue_id', 'ticket_category', name='uq_queue_category_sla'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'queue_id': self.queue_id,
            'queue_name': self.queue.name if self.queue else None,
            'ticket_category': self.ticket_category.value if self.ticket_category else None,
            'ticket_category_key': self.ticket_category.name if self.ticket_category else None,
            'working_days': self.working_days,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
