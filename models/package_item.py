from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from models.base import Base

class PackageItem(Base):
    """Model for tracking assets and accessories associated with specific packages"""
    __tablename__ = 'package_items'

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'), nullable=False)
    package_number = Column(Integer, nullable=False)  # 1-5 for the package number
    
    # Either asset_id OR accessory_id will be set, not both
    asset_id = Column(Integer, ForeignKey('assets.id'), nullable=True)
    accessory_id = Column(Integer, ForeignKey('accessories.id'), nullable=True)
    
    # Additional metadata
    quantity = Column(Integer, default=1)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    ticket = relationship('Ticket', backref='package_items')
    asset = relationship('Asset', foreign_keys=[asset_id])
    accessory = relationship('Accessory', foreign_keys=[accessory_id])

    def __repr__(self):
        item_type = "Asset" if self.asset_id else "Accessory"
        item_id = self.asset_id if self.asset_id else self.accessory_id
        return f"<PackageItem(ticket={self.ticket_id}, package={self.package_number}, {item_type}={item_id})>"

    @property
    def item_name(self):
        """Get the name of the associated item"""
        if self.asset:
            return self.asset.name
        elif self.accessory:
            return self.accessory.name
        return "Unknown Item"

    @property
    def item_type(self):
        """Get the type of item (Asset or Accessory)"""
        return "Asset" if self.asset_id else "Accessory"

    @property
    def item_details(self):
        """Get additional details about the item"""
        if self.asset:
            return {
                'id': self.asset.id,
                'name': self.asset.name,
                'asset_tag': getattr(self.asset, 'asset_tag', None),
                'serial_num': getattr(self.asset, 'serial_num', None),
                'model': getattr(self.asset, 'model', None),
                'status': getattr(self.asset, 'status', None)
            }
        elif self.accessory:
            return {
                'id': self.accessory.id,
                'name': self.accessory.name,
                'category': getattr(self.accessory, 'category', None),
                'model': getattr(self.accessory, 'model', None),
                'stock_quantity': getattr(self.accessory, 'stock_quantity', None)
            }
        return {} 