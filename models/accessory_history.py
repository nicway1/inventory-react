from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from models.base import Base

class AccessoryHistory(Base):
    __tablename__ = 'accessory_history'
    
    id = Column(Integer, primary_key=True)
    accessory_id = Column(Integer, ForeignKey('accessories.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    action = Column(String(50), nullable=False)  # e.g., 'update', 'delete'
    changes = Column(JSON)  # Store the changes made: {'field': {'old': value, 'new': value}}
    notes = Column(String(1000))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    accessory = relationship("Accessory", back_populates="history")
    user = relationship("User", back_populates="accessory_changes")
    
    @staticmethod
    def create_history(accessory_id, user_id, action, changes, notes=None):
        return AccessoryHistory(
            accessory_id=accessory_id,
            user_id=user_id,
            action=action,
            changes=changes,
            notes=notes
        ) 