from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base

class Accessory(Base):
    __tablename__ = 'accessories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)  # Item Name
    category = Column(String(50), nullable=False)  # Category
    manufacturer = Column(String(100))  # Manufacturer
    model_no = Column(String(100))  # Model No
    total_quantity = Column(Integer, default=0)  # Quantity
    available_quantity = Column(Integer, default=0)  # Available quantity from total
    status = Column(String(50), default='Available')  # Status
    notes = Column(String(1000))  # Notes
    assigned_to = Column(String(100))  # User who checked out the accessory
    checkout_date = Column(DateTime)
    return_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationship with tickets using string reference
    tickets = relationship("Ticket", back_populates="accessory", lazy="dynamic")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'manufacturer': self.manufacturer,
            'model_no': self.model_no,
            'total_quantity': self.total_quantity,
            'available_quantity': self.available_quantity,
            'status': self.status,
            'notes': self.notes,
            'assigned_to': self.assigned_to,
            'checkout_date': self.checkout_date.isoformat() if self.checkout_date else None,
            'return_date': self.return_date.isoformat() if self.return_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def checkout(self, assigned_to):
        """Check out this accessory to a user"""
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