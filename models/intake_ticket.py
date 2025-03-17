from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from models.base import Base
import enum

class IntakeStatus(enum.Enum):
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"

class IntakeTicket(Base):
    __tablename__ = 'intake_tickets'

    id = Column(Integer, primary_key=True)
    ticket_number = Column(String(50), unique=True, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(Enum(IntakeStatus), default=IntakeStatus.PENDING)
    created_by = Column(Integer, ForeignKey('users.id'))
    assigned_to = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_intake_tickets")
    assignee = relationship("User", foreign_keys=[assigned_to], back_populates="assigned_intake_tickets")
    assets = relationship("Asset", back_populates="intake_ticket")
    attachments = relationship("IntakeAttachment", back_populates="ticket", cascade="all, delete-orphan")

    def __init__(self, title, description, created_by, assigned_to=None):
        self.ticket_number = f"INTK-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        self.title = title
        self.description = description
        self.created_by = created_by
        self.assigned_to = assigned_to

class IntakeAttachment(Base):
    __tablename__ = 'intake_attachments'

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('intake_tickets.id'))
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_type = Column(String(50))
    uploaded_by = Column(Integer, ForeignKey('users.id'))
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    uploader = relationship("User", back_populates="uploaded_intake_attachments")
    ticket = relationship("IntakeTicket", back_populates="attachments")

    def __init__(self, filename, file_path, file_type, uploaded_by, ticket_id):
        self.filename = filename
        self.file_path = file_path
        self.file_type = file_type
        self.uploaded_by = uploaded_by
        self.ticket_id = ticket_id 