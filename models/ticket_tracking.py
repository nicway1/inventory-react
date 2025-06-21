from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from models.base import Base

class TicketTracking(Base):
    """Model for multiple tracking numbers per ticket with asset/accessory assignments"""
    __tablename__ = 'ticket_tracking'

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'), nullable=False)
    tracking_number = Column(String(100), nullable=False)
    carrier = Column(String(50), default='claw')
    status = Column(String(100), default='Pending')
    tracking_type = Column(String(20), default='outbound')  # outbound, return, etc.
    sequence_number = Column(Integer, default=1)  # Tracking 1, 2, 3, etc.
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    ticket = relationship('Ticket', back_populates='tracking_numbers')
    item_assignments = relationship('TrackingItemAssignment', back_populates='tracking', cascade='all, delete-orphan')

    def get_assigned_assets(self):
        """Get all assets assigned to this tracking number"""
        return [assignment.asset for assignment in self.item_assignments if assignment.asset]

    def get_assigned_accessories(self):
        """Get all accessories assigned to this tracking number"""
        return [assignment.accessory for assignment in self.item_assignments if assignment.accessory]

    def __repr__(self):
        return f"<TicketTracking(id={self.id}, tracking='{self.tracking_number}', status='{self.status}')>"


class TrackingItemAssignment(Base):
    """Model for assigning assets/accessories to tracking numbers"""
    __tablename__ = 'tracking_item_assignments'

    id = Column(Integer, primary_key=True)
    tracking_id = Column(Integer, ForeignKey('ticket_tracking.id'), nullable=False)
    asset_id = Column(Integer, ForeignKey('assets.id'), nullable=True)
    accessory_id = Column(Integer, ForeignKey('ticket_accessories.id'), nullable=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    assigned_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    # Relationships
    tracking = relationship('TicketTracking', back_populates='item_assignments')
    asset = relationship('Asset')
    accessory = relationship('TicketAccessory')
    assigned_by = relationship('User')

    def __repr__(self):
        item_type = 'Asset' if self.asset_id else 'Accessory'
        item_id = self.asset_id or self.accessory_id
        return f"<TrackingItemAssignment(tracking_id={self.tracking_id}, {item_type}={item_id})>" 