from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from models.base import Base


class CustomTicketStatus(Base):
    """Model for custom ticket statuses"""
    __tablename__ = 'custom_ticket_statuses'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(100), nullable=False)
    color = Column(String(20), default='gray')  # Tailwind color name: blue, green, yellow, red, purple, gray
    is_active = Column(Boolean, default=True)
    is_system = Column(Boolean, default=False)  # System statuses cannot be deleted
    auto_return_to_stock = Column(Boolean, default=False)  # Automatically return assets/accessories to stock
    sort_order = Column(Integer, default=0)  # For ordering in dropdowns
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'color': self.color,
            'is_active': self.is_active,
            'is_system': self.is_system,
            'auto_return_to_stock': self.auto_return_to_stock,
            'sort_order': self.sort_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
