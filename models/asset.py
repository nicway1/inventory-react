from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, JSON, Float, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from models.base import Base

class AssetStatus(enum.Enum):
    IN_STOCK = "In Stock"
    READY_TO_DEPLOY = "Ready to Deploy"
    SHIPPED = "Shipped"
    DEPLOYED = "Deployed"
    REPAIR = "Repair"
    ARCHIVED = "Archived"
    DISPOSED = "Disposed"

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
    cost_price = Column(Float)
    location_id = Column(Integer, ForeignKey('locations.id'))
    company_id = Column(Integer, ForeignKey('companies.id'))
    specifications = Column(JSON)
    notes = Column(String(1000))
    tech_notes = Column(String(2000))  # Longer length for detailed technical notes
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    assigned_to_id = Column(Integer, ForeignKey('users.id'))
    customer_id = Column(Integer, ForeignKey('customer_users.id'), nullable=True)
    
    # Additional fields used in inventory routes
    hardware_type = Column(String(100))
    inventory = Column(String(50))
    customer = Column(String(100))
    country = Column(String(100))
    asset_type = Column(String(100))
    
    # Additional fields from import
    receiving_date = Column(DateTime)
    keyboard = Column(String(100))
    po = Column(String(100))
    erased = Column(String(50))
    condition = Column(String(100))
    diag = Column(String(1000))
    cpu_type = Column(String(100))
    cpu_cores = Column(String(100))
    gpu_cores = Column(String(100))
    memory = Column(String(100))
    harddrive = Column(String(100))
    charger = Column(String(100))
    
    # Relationships
    location = relationship("Location", back_populates="assets")
    company = relationship("Company", back_populates="assets")
    tickets = relationship("Ticket", back_populates="asset")
    assigned_to = relationship("User", back_populates="assigned_assets")
    customer_user = relationship("CustomerUser", back_populates="assigned_assets")
    transactions = relationship("AssetTransaction", back_populates="asset", order_by="desc(AssetTransaction.transaction_date)")
    history = relationship("AssetHistory", back_populates="asset", order_by="desc(AssetHistory.created_at)")

    def track_change(self, user_id, action, changes, notes=None):
        """Track changes made to the asset"""
        from models.asset_history import AssetHistory
        history_entry = AssetHistory.create_history(
            asset_id=self.id,
            user_id=user_id,
            action=action,
            changes=changes,
            notes=notes
        )
        return history_entry 