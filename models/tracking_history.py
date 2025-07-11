import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


class TrackingHistory(Base):
    """Model to store tracking history/cache to avoid repeated scraping"""
    __tablename__ = 'tracking_history'

    id = Column(Integer, primary_key=True)
    tracking_number = Column(String(100), nullable=False, index=True)
    carrier = Column(String(50))
    status = Column(String(100))
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Store the full tracking events JSON
    tracking_data = Column(Text)
    
    # Link to ticket (optional)
    ticket_id = Column(Integer, ForeignKey('tickets.id'), nullable=True)
    ticket = relationship('Ticket', back_populates='tracking_histories')
    
    # Tracking type (primary, secondary, return, etc.)
    tracking_type = Column(String(20), default='primary')
    
    def __init__(self, tracking_number, tracking_data=None, carrier=None, status=None, ticket_id=None, tracking_type='primary'):
        self.tracking_number = tracking_number
        self.tracking_data = json.dumps(tracking_data) if tracking_data else None
        self.carrier = carrier
        self.status = status
        self.ticket_id = ticket_id
        self.tracking_type = tracking_type
        self.last_updated = datetime.utcnow()
    
    @property
    def events(self):
        """Get the tracking events from the tracking data"""
        if not self.tracking_data:
            return []
        try:
            return json.loads(self.tracking_data)
        except:
            return []
    
    def update(self, tracking_data, status=None, carrier=None):
        """Update the tracking history with new data"""
        self.tracking_data = json.dumps(tracking_data) if tracking_data else self.tracking_data
        self.status = status or self.status
        self.carrier = carrier or self.carrier
        self.last_updated = datetime.utcnow()
        
    def is_stale(self, ttl_hours=24):
        """Check if the tracking data is stale (older than ttl_hours)"""
        if not self.last_updated:
            return True
        
        # Calculate staleness based on UTC time
        current_time = datetime.utcnow()
        time_diff = current_time - self.last_updated
        
        # Debug logging
        logger.info("Checking staleness for tracking {self.tracking_number}:")
        logger.info("- Current time: {current_time}")
        logger.info("- Last updated: {self.last_updated}")
        logger.info("- Time diff (hours): {time_diff.total_seconds() / 3600}")
        logger.info("- TTL hours: {ttl_hours}")
        logger.info("- Is stale: {time_diff.total_seconds() > (ttl_hours * 3600)}")
        
        return time_diff.total_seconds() > (ttl_hours * 3600) 