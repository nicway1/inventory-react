"""
Model for storing device specifications submitted via the spec collector script
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from datetime import datetime
from models.base import Base


class DeviceSpec(Base):
    __tablename__ = 'device_specs'

    id = Column(Integer, primary_key=True)

    # Device Identification
    serial_number = Column(String(100), index=True)
    hardware_uuid = Column(String(100))

    # Model Information
    model_name = Column(String(200))
    model_id = Column(String(100))

    # Processor
    cpu = Column(String(200))
    cpu_cores = Column(String(50))

    # Graphics
    gpu = Column(String(200))
    gpu_cores = Column(String(50))

    # Memory
    ram_gb = Column(String(20))
    memory_type = Column(String(50))

    # Storage
    storage_gb = Column(String(20))
    storage_type = Column(String(20))
    free_space = Column(String(20))

    # Operating System
    os_name = Column(String(50))
    os_version = Column(String(50))
    os_build = Column(String(50))

    # Battery
    battery_cycles = Column(String(20))
    battery_health = Column(String(20))

    # Network
    wifi_mac = Column(String(50))
    ethernet_mac = Column(String(50))

    # Metadata
    submitted_at = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(50))
    processed = Column(Boolean, default=False)
    processed_at = Column(DateTime)
    asset_id = Column(Integer, nullable=True)  # Link to created asset
    notes = Column(Text)

    def to_dict(self):
        return {
            'id': self.id,
            'serial_number': self.serial_number,
            'hardware_uuid': self.hardware_uuid,
            'model_name': self.model_name,
            'model_id': self.model_id,
            'cpu': self.cpu,
            'cpu_cores': self.cpu_cores,
            'gpu': self.gpu,
            'gpu_cores': self.gpu_cores,
            'ram_gb': self.ram_gb,
            'memory_type': self.memory_type,
            'storage_gb': self.storage_gb,
            'storage_type': self.storage_type,
            'free_space': self.free_space,
            'os_name': self.os_name,
            'os_version': self.os_version,
            'os_build': self.os_build,
            'battery_cycles': self.battery_cycles,
            'battery_health': self.battery_health,
            'wifi_mac': self.wifi_mac,
            'ethernet_mac': self.ethernet_mac,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'ip_address': self.ip_address,
            'processed': self.processed,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'asset_id': self.asset_id
        }
