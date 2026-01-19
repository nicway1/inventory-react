from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from models.base import Base

class ServiceRecord(Base):
    """Model for recording and requesting services on assets"""
    __tablename__ = 'service_records'

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'), nullable=False)
    asset_id = Column(Integer, ForeignKey('assets.id'), nullable=True)

    # Service details
    service_type = Column(String(100), nullable=False)  # e.g., "OS Reinstall", "Screen Replacement"
    description = Column(Text, nullable=True)  # Additional details about the service
    status = Column(String(50), default='Requested')  # Requested, In Progress, Completed

    # Who requested and when
    requested_by_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Who completed and when (for completed services)
    completed_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Legacy field - keeping for backwards compatibility
    performed_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    performed_at = Column(DateTime, nullable=True)

    # Relationships
    ticket = relationship("Ticket", back_populates="service_records")
    asset = relationship("Asset", back_populates="service_records")
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    completed_by = relationship("User", foreign_keys=[completed_by_id])
    performed_by = relationship("User", foreign_keys=[performed_by_id])

    # Status options
    STATUS_OPTIONS = ['Requested', 'In Progress', 'Completed']

    # Common service types for reference
    SERVICE_TYPES = [
        "OS Reinstall",
        "Hardware Repair",
        "Screen Replacement",
        "Battery Replacement",
        "Keyboard Replacement",
        "Data Backup",
        "Data Wipe",
        "Software Installation",
        "Firmware Update",
        "Diagnostic Test",
        "Cleaning",
        "Other"
    ]

    def to_dict(self):
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'asset_id': self.asset_id,
            'service_type': self.service_type,
            'description': self.description,
            'status': self.status or 'Requested',
            'requested_by_id': self.requested_by_id,
            'requested_by_name': self.requested_by.username if self.requested_by else None,
            'completed_by_id': self.completed_by_id,
            'completed_by_name': self.completed_by.username if self.completed_by else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'asset_tag': self.asset.asset_tag if self.asset else None,
            # Legacy fields for backwards compatibility
            'performed_by_id': self.performed_by_id or self.requested_by_id,
            'performed_by_name': (self.performed_by.username if self.performed_by else None) or (self.requested_by.username if self.requested_by else None),
            'performed_at': (self.performed_at.isoformat() if self.performed_at else None) or (self.created_at.isoformat() if self.created_at else None)
        }
