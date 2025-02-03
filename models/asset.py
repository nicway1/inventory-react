from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, JSON, Float
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from models.base import Base

class AssetStatus(enum.Enum):
    IN_STOCK = "IN STOCK"
    READY_TO_DEPLOY = "Ready to Deploy"
    SHIPPED = "SHIPPED"
    DEPLOYED = "DEPLOYED"
    REPAIR = "REPAIR"
    ARCHIVED = "ARCHIVED"

class Asset(Base):
    __tablename__ = 'assets'
    
    id = Column(Integer, primary_key=True)
    asset_tag = Column(String(50), unique=True, nullable=False)
    serial_num = Column(String(50), unique=True)
    name = Column(String(100))
    model = Column(String(100))
    manufacturer = Column(String(100))
    category = Column(String(50))
    status = Column(Enum(AssetStatus), default=AssetStatus.IN_STOCK)
    cost_price = Column(Float)  # New column for cost price
    location_id = Column(Integer, ForeignKey('locations.id'))
    company_id = Column(Integer, ForeignKey('companies.id'))
    specifications = Column(JSON)  # Store specs as JSON
    notes = Column(String(1000))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Additional fields used in inventory routes
    hardware_type = Column(String(100))
    inventory = Column(String(50))  # For inventory status
    customer = Column(String(100))  # For storing customer name
    country = Column(String(100))
    
    # Additional fields from import
    receiving_date = Column(DateTime)
    keyboard = Column(String(100))
    po = Column(String(100))
    erased = Column(String(50))
    condition = Column(String(100))
    diag = Column(String(1000))
    cpu_type = Column(String(100))
    cpu_cores = Column(String(50))
    gpu_cores = Column(String(50))
    memory = Column(String(100))
    harddrive = Column(String(100))
    charger = Column(String(100))
    
    # Relationships with string references
    location = relationship("Location", back_populates="assets")
    company = relationship("Company", back_populates="assets")
    tickets = relationship("Ticket", back_populates="asset", lazy="dynamic")
    sales = relationship("Sale", back_populates="product", lazy="dynamic") 