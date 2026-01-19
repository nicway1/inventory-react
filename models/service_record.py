from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from models.base import Base

class ServiceRecord(Base):
    """Model for recording services performed on assets"""
    __tablename__ = 'service_records'

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'), nullable=False)
    asset_id = Column(Integer, ForeignKey('assets.id'), nullable=True)

    # Service details
    service_type = Column(String(100), nullable=False)  # e.g., "OS Reinstall", "Screen Replacement"
    description = Column(Text, nullable=True)  # Additional details about the service

    # Who and when
    performed_by_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    performed_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    ticket = relationship("Ticket", back_populates="service_records")
    asset = relationship("Asset", back_populates="service_records")
    performed_by = relationship("User", back_populates="service_records")

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
            'performed_by_id': self.performed_by_id,
            'performed_by_name': self.performed_by.name if self.performed_by else None,
            'performed_at': self.performed_at.isoformat() if self.performed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'asset_tag': self.asset.asset_tag if self.asset else None
        }