from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from models.base import Base

class SavedInvoice(Base):
    __tablename__ = 'saved_invoices'
    
    id = Column(Integer, primary_key=True)
    invoice_number = Column(String(100), unique=True, nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Customer/Delivery Information
    delivery_location = Column(Text)
    importer_name = Column(String(255))
    importer_address = Column(Text)
    importer_phone = Column(String(50))
    importer_mobile = Column(String(50))
    importer_email = Column(String(255))
    end_user = Column(String(255))
    
    # Invoice Details
    shipper_reference = Column(String(255))
    consignee_reference = Column(String(255))
    end_user_reference = Column(String(255))
    payment_terms = Column(String(255))
    incoterms = Column(String(100))
    incoterms_named_place = Column(String(255))
    country_destination = Column(String(100))
    country_end_use = Column(String(100))
    currency = Column(String(10), default='USD')
    
    # Financial Information
    subtotal = Column(Float, default=0.0)
    freight = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    
    # Store items as JSON text for simplicity
    items_json = Column(Text)  # Will store JSON array of items
    
    # Relationships
    # creator = relationship("User", back_populates="created_invoices")
    creator = relationship("User")  # Simplified relationship without back_populates
    
    def to_dict(self):
        """Convert to dictionary for easy JSON serialization"""
        return {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'date': self.date.isoformat() if self.date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
            'delivery_location': self.delivery_location,
            'importer_name': self.importer_name,
            'importer_address': self.importer_address,
            'importer_phone': self.importer_phone,
            'importer_mobile': self.importer_mobile,
            'importer_email': self.importer_email,
            'end_user': self.end_user,
            'shipper_reference': self.shipper_reference,
            'consignee_reference': self.consignee_reference,
            'end_user_reference': self.end_user_reference,
            'payment_terms': self.payment_terms,
            'incoterms': self.incoterms,
            'incoterms_named_place': self.incoterms_named_place,
            'country_destination': self.country_destination,
            'country_end_use': self.country_end_use,
            'currency': self.currency,
            'subtotal': self.subtotal,
            'freight': self.freight,
            'total': self.total,
            'items_json': self.items_json
        } 