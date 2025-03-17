from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from utils.db_manager import Base

class TicketAttachment(Base):
    __tablename__ = 'ticket_attachments'

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_type = Column(String(100))
    uploaded_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    ticket = relationship('Ticket', back_populates='attachments')
    uploader = relationship('User', back_populates='uploaded_attachments') 