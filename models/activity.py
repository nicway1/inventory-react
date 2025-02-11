from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from models.base import Base

class Activity(Base):
    __tablename__ = 'activities'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    type = Column(String(50), nullable=False)  # e.g., 'mention', 'ticket_assigned', etc.
    content = Column(String(500), nullable=False)
    reference_id = Column(Integer)  # e.g., ticket_id
    created_at = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)
    
    # Relationship with user
    user = relationship("User", back_populates="activities")

    @staticmethod
    def create(user_id, type, content, reference_id):
        return Activity(
            user_id=user_id,
            type=type,
            content=content,
            reference_id=reference_id
        ) 