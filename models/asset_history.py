from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from models.base import Base

class AssetHistory(Base):
    """Model for asset history"""
    __tablename__ = 'asset_history'
    
    id = Column(Integer, primary_key=True)
    asset_id = Column(Integer, ForeignKey('assets.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    action = Column(String(100), nullable=False)
    changes = Column(JSON)
    notes = Column(String(1000))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    asset = relationship("Asset", back_populates="history")
    user = relationship("User", back_populates="asset_changes")
    
    @staticmethod
    def create_history(asset_id, user_id, action, changes, notes=None):
        """Create a new history entry"""
        return AssetHistory(
            asset_id=asset_id,
            user_id=user_id,
            action=action,
            changes=changes,
            notes=notes
        ) 