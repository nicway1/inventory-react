from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from models.base import Base

class AccessoryHistory(Base):
    """Model for accessory history"""
    __tablename__ = 'accessory_history'
    
    id = Column(Integer, primary_key=True)
    accessory_id = Column(Integer, ForeignKey('accessories.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    action = Column(String(100), nullable=False)
    changes = Column(JSON)
    notes = Column(String(1000))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    accessory = relationship("Accessory", back_populates="history")
    user = relationship("User", back_populates="accessory_changes")
    
    @staticmethod
    def create_history(accessory_id, user_id, action, changes, notes=None):
        """Create a new history entry"""
        return AccessoryHistory(
            accessory_id=accessory_id,
            user_id=user_id,
            action=action,
            changes=changes,
            notes=notes
        ) 