from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base

class AccessoryAlias(Base):
    __tablename__ = 'accessory_aliases'

    id = Column(Integer, primary_key=True)
    accessory_id = Column(Integer, ForeignKey('accessories.id'), nullable=False)
    alias_name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    accessory = relationship("Accessory", back_populates="aliases")

    def to_dict(self):
        return {
            'id': self.id,
            'accessory_id': self.accessory_id,
            'alias_name': self.alias_name,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
