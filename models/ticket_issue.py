from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from models.base import Base


class TicketIssue(Base):
    """Model for tracking issues reported on tickets"""
    __tablename__ = 'ticket_issues'

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'), nullable=False)
    issue_type = Column(String(100), nullable=False)  # e.g., "Wrong Accessories", "Wrong Address"
    description = Column(Text, nullable=False)
    reported_by_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    reported_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Resolution tracking
    is_resolved = Column(Boolean, default=False)
    resolution_notes = Column(Text)
    resolved_by_id = Column(Integer, ForeignKey('users.id'))
    resolved_at = Column(DateTime)

    # Notification tracking
    notified_user_ids = Column(String(500))  # Store comma-separated user IDs who should be notified

    # Relationships
    ticket = relationship('Ticket', backref='issues')
    reported_by = relationship('User', foreign_keys=[reported_by_id], backref='reported_issues')
    resolved_by = relationship('User', foreign_keys=[resolved_by_id], backref='resolved_issues')

    def __repr__(self):
        return f"<TicketIssue(id={self.id}, ticket_id={self.ticket_id}, issue_type='{self.issue_type}', is_resolved={self.is_resolved})>"

    def to_dict(self):
        """Convert issue to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'issue_type': self.issue_type,
            'description': self.description,
            'reported_by_id': self.reported_by_id,
            'reported_by_name': self.reported_by.username if self.reported_by else None,
            'reported_at': self.reported_at.isoformat() if self.reported_at else None,
            'is_resolved': self.is_resolved,
            'resolution_notes': self.resolution_notes,
            'resolved_by_id': self.resolved_by_id,
            'resolved_by_name': self.resolved_by.username if self.resolved_by else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'notified_user_ids': self.notified_user_ids
        }
