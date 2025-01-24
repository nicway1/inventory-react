from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import enum

Base = declarative_base()

class AssetStatus(enum.Enum):
    IN_STOCK = "IN STOCK"
    SHIPPED = "SHIPPED"
    DEPLOYED = "DEPLOYED"
    REPAIR = "REPAIR"
    ARCHIVED = "ARCHIVED"

class Asset(Base):
    __tablename__ = 'assets'
    
    id = Column(Integer, primary_key=True)
    asset_tag = Column(String(50), unique=True, nullable=False)
    serial = Column(String(50), unique=True)
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
    
    # Relationships
    location = relationship("Location", back_populates="assets")
    company = relationship("Company", back_populates="assets")
    tickets = relationship("Ticket", back_populates="asset")

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
    users = relationship("User", back_populates="company")

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