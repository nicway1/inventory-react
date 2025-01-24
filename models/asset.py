from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from database import Base

class Asset(Base):
    __tablename__ = 'assets'

    id = Column(Integer, primary_key=True)
    product = Column(String(100))
    asset_tag = Column(String(50), unique=True)
    receiving_date = Column(DateTime)
    keyboard = Column(String(50))
    serial_num = Column(String(50))
    po = Column(String(50))
    model = Column(String(100))
    erased = Column(Boolean)
    customer = Column(String(100))
    condition = Column(String(50))
    diag = Column(String(500))
    hardware_type = Column(String(50))
    cpu_type = Column(String(50))
    cpu_cores = Column(Integer)
    gpu_cores = Column(Integer)
    memory = Column(String(50))
    harddrive = Column(String(50))
    charger = Column(String(50))
    inventory = Column(String(50))
    country = Column(String(50))
    status = Column(String(50), default='Ready to Deploy')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'product': self.product,
            'asset_tag': self.asset_tag,
            'receiving_date': self.receiving_date.isoformat() if self.receiving_date else None,
            'keyboard': self.keyboard,
            'serial_num': self.serial_num,
            'po': self.po,
            'model': self.model,
            'erased': self.erased,
            'customer': self.customer,
            'condition': self.condition,
            'diag': self.diag,
            'hardware_type': self.hardware_type,
            'cpu_type': self.cpu_type,
            'cpu_cores': self.cpu_cores,
            'gpu_cores': self.gpu_cores,
            'memory': self.memory,
            'harddrive': self.harddrive,
            'charger': self.charger,
            'inventory': self.inventory,
            'country': self.country,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 