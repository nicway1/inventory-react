from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import enum

Base = declarative_base()

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
    
    # Relationships
    location = relationship("Location", back_populates="assets")
    company = relationship("Company", back_populates="assets")
    tickets = relationship("Ticket", back_populates="asset")

class Accessory(Base):
    __tablename__ = 'accessories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50))
    status = Column(String(50), default='Available')
    total_quantity = Column(Integer, default=0)
    available_quantity = Column(Integer, default=0)
    customer = Column(String(100))  # For checked out accessories
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class Location(Base):
    __tablename__ = 'locations'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    country = Column(String(100))
    address = Column(String(200))
    
    # Relationships
    assets = relationship("Asset", back_populates="location")

class Company(Base):
    __tablename__ = 'companies'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    contact_name = Column(String(100))
    contact_email = Column(String(100))
    
    # Relationships
    assets = relationship("Asset", back_populates="company")
    users = relationship("User", back_populates="company", lazy='dynamic')  # Use string reference and lazy loading

class Ticket(Base):
    __tablename__ = 'tickets'
    
    id = Column(Integer, primary_key=True)
    subject = Column(String(200), nullable=False)
    description = Column(String(1000))
    status = Column(String(50), default='open')
    asset_id = Column(Integer, ForeignKey('assets.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    asset = relationship("Asset", back_populates="tickets") 