from sqlalchemy import Column, Integer, Date, ForeignKey, DateTime, Boolean, String, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from models.base import Base
import enum


class WorkLocation(enum.Enum):
    WFH = "Work From Home"
    WFO = "Work From Office"


class DeveloperSchedule(Base):
    """Model to track developer working days"""
    __tablename__ = 'developer_schedules'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    work_date = Column(Date, nullable=False)
    is_working = Column(Boolean, default=True)
    work_location = Column(String(10), default='WFO')  # WFH or WFO
    note = Column(String(255), nullable=True)  # Optional note for the day
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="schedules")

    def __repr__(self):
        return f"<DeveloperSchedule {self.user_id} - {self.work_date}>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'work_date': self.work_date.isoformat() if self.work_date else None,
            'is_working': self.is_working,
            'work_location': self.work_location,
            'note': self.note,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
