from datetime import datetime
from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from models.base import Base


class TicketAssetCheckin(Base):
    """Tracks check-in status for assets associated with Asset Intake tickets"""
    __tablename__ = 'ticket_asset_checkin'

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id', ondelete='CASCADE'), nullable=False)
    asset_id = Column(Integer, ForeignKey('assets.id', ondelete='CASCADE'), nullable=False)
    checked_in = Column(Boolean, default=False)
    checked_in_at = Column(DateTime, nullable=True)
    checked_in_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Unique constraint - each asset can only be checked in once per ticket
    __table_args__ = (
        UniqueConstraint('ticket_id', 'asset_id', name='uq_ticket_asset_checkin'),
    )

    # Relationships
    ticket = relationship('Ticket', back_populates='asset_checkins')
    asset = relationship('Asset', back_populates='checkins')
    checked_in_by = relationship('User', foreign_keys=[checked_in_by_id])

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'asset_id': self.asset_id,
            'checked_in': self.checked_in,
            'checked_in_at': self.checked_in_at.isoformat() if self.checked_in_at else None,
            'checked_in_by_id': self.checked_in_by_id,
            'checked_in_by_name': self.checked_in_by.full_name if self.checked_in_by else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'asset': {
                'id': self.asset.id,
                'serial_num': self.asset.serial_num,
                'asset_tag': self.asset.asset_tag,
                'model': self.asset.model,
                'type': self.asset.type
            } if self.asset else None
        }

    def __repr__(self):
        return f"<TicketAssetCheckin(ticket_id={self.ticket_id}, asset_id={self.asset_id}, checked_in={self.checked_in})>"
