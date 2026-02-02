"""
TrackingRefreshLog model for storing bulk tracking refresh history.
"""

from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
import datetime


class TrackingRefreshLog(Base):
    """Model to track bulk tracking refresh operations"""
    __tablename__ = 'tracking_refresh_logs'

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    created_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_by_name = Column(String(100))

    # Summary stats
    total_tickets = Column(Integer, default=0)
    tickets_updated = Column(Integer, default=0)
    tickets_auto_closed = Column(Integer, default=0)
    tickets_failed = Column(Integer, default=0)
    total_packages_updated = Column(Integer, default=0)
    total_packages_failed = Column(Integer, default=0)

    # Timing
    duration_seconds = Column(Integer, nullable=True)

    # Detailed results stored as JSON
    details = Column(JSON, nullable=True)

    def __repr__(self):
        return f'<TrackingRefreshLog {self.id}: {self.tickets_updated}/{self.total_tickets} updated>'
