from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from models.base import Base

class Platform(enum.Enum):
    CAROUSELL = "Carousell"
    XHS = "XHS"
    OTHERS = "Others"

class Sale(Base):
    __tablename__ = 'sales'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('assets.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)
    platform = Column(Enum(Platform), nullable=False)
    selling_price = Column(Float, nullable=False)
    customer_name = Column(String(100), nullable=False)
    sale_date = Column(DateTime, default=datetime.utcnow)
    notes = Column(String(1000))
    profit = Column(Float)  # Will be calculated on save
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    product = relationship("Asset", back_populates="sales", lazy="joined")
    user = relationship("User", back_populates="sales", lazy="joined", primaryjoin="Sale.user_id == User.id")
    company = relationship("Company", back_populates="sales", lazy="joined")

    def calculate_profit(self):
        """Calculate profit based on selling price and product cost"""
        if self.product and self.product.cost_price:
            self.profit = self.selling_price - self.product.cost_price
        else:
            self.profit = 0 