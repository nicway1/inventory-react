from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from database import Base

class Accessory(Base):
    __tablename__ = 'accessories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)  # e.g. "Logitech Pebble Keys 2 K380s Keyboard"
    category = Column(String(50), nullable=False)  # e.g. "Keyboard", "Mouse", "Power Adapter"
    total_quantity = Column(Integer, default=0)  # Total number of this accessory
    available_quantity = Column(Integer, default=0)  # Number currently available
    status = Column(String(50), default='Available')  # Available or Checked Out
    assigned_to = Column(String(100))  # User who checked out the accessory
    checkout_date = Column(DateTime)
    return_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'total_quantity': self.total_quantity,
            'available_quantity': self.available_quantity,
            'status': self.status,
            'assigned_to': self.assigned_to,
            'checkout_date': self.checkout_date.isoformat() if self.checkout_date else None,
            'return_date': self.return_date.isoformat() if self.return_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def checkout(self, assigned_to):
        """Checkout this accessory to a user"""
        if self.available_quantity > 0:
            self.available_quantity -= 1
            self.assigned_to = assigned_to
            self.checkout_date = datetime.utcnow()
            self.status = 'Checked Out'
            return True
        return False

    def checkin(self):
        """Return this accessory to inventory"""
        if self.total_quantity > self.available_quantity:
            self.available_quantity += 1
            self.assigned_to = None
            self.return_date = datetime.utcnow()
            self.status = 'Available'
            return True
        return False 