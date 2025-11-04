from sqlalchemy import Column, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from models.base import Base

class CompanyQueuePermission(Base):
    __tablename__ = 'company_queue_permissions'

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey('companies.id', ondelete='CASCADE'), nullable=False)
    queue_id = Column(Integer, ForeignKey('queues.id', ondelete='CASCADE'), nullable=False)
    can_view = Column(Boolean, default=True)
    can_create = Column(Boolean, default=False)

    # Relationships
    company = relationship('Company', back_populates='queue_permissions')
    queue = relationship('Queue', back_populates='company_permissions')
    
    def to_dict(self):
        """Convert permission to dictionary"""
        return {
            'id': self.id,
            'company_id': self.company_id,
            'queue_id': self.queue_id,
            'can_view': self.can_view,
            'can_create': self.can_create
        } 