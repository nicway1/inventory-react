from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from models.base import Base

class AssetHistory(Base):
    __tablename__ = 'asset_history'
    
    id = Column(Integer, primary_key=True)
    asset_id = Column(Integer, ForeignKey('assets.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    action = Column(String(50), nullable=False)  # e.g., 'update', 'status_change'
    changes = Column(JSON)  # Store the changes made: {'field': {'old': value, 'new': value}}
    notes = Column(String(1000))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    asset = relationship("Asset", back_populates="history")
    user = relationship("User", back_populates="asset_changes")
    
    @staticmethod
    def create_history(asset_id, user_id, action, changes, notes=None):
        return AssetHistory(
            asset_id=asset_id,
            user_id=user_id,
            action=action,
            changes=changes,
            notes=notes
        ) 