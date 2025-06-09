from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from datetime import datetime
from models.base import Base
import json


class TicketCategoryConfig(Base):
    """Model for custom ticket category configurations"""
    __tablename__ = 'ticket_category_configs'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Store enabled sections as JSON
    enabled_sections = Column(Text, nullable=False)  # JSON string of enabled section names
    
    # Additional configuration
    is_active = Column(Boolean, default=True)
    created_by_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<TicketCategoryConfig(id={self.id}, name='{self.name}', display_name='{self.display_name}')>"

    @property
    def sections_list(self):
        """Get enabled sections as a list"""
        try:
            return json.loads(self.enabled_sections) if self.enabled_sections else []
        except (json.JSONDecodeError, TypeError):
            return []

    @sections_list.setter
    def sections_list(self, sections):
        """Set enabled sections from a list"""
        self.enabled_sections = json.dumps(sections) if sections else '[]'

    def has_section(self, section_name):
        """Check if a specific section is enabled"""
        return section_name in self.sections_list

    @staticmethod
    def get_available_sections():
        """Get all available ticket sections that can be enabled/disabled"""
        return [
            {
                'id': 'case_information',
                'name': 'Case Information',
                'description': 'Basic ticket information (subject, description, priority)',
                'required': True  # Always required
            },
            {
                'id': 'comments',
                'name': 'Comments',
                'description': 'Comment system for ticket updates',
                'required': True  # Always required
            },
            {
                'id': 'tech_assets',
                'name': 'Tech Assets',
                'description': 'Asset management and tracking'
            },
            {
                'id': 'received_accessories',
                'name': 'Received Accessories',
                'description': 'Track accessories received with returns'
            },
            {
                'id': 'shipping_tracking',
                'name': 'Shipping Tracking',
                'description': 'Outbound shipment tracking'
            },
            {
                'id': 'return_tracking',
                'name': 'Return Tracking',
                'description': 'Inbound/return shipment tracking'
            },
            {
                'id': 'customer_selection',
                'name': 'Customer Selection',
                'description': 'Customer assignment and management'
            },
            {
                'id': 'queue_management',
                'name': 'Queue Management',
                'description': 'Ticket queue assignment'
            },
            {
                'id': 'attachments',
                'name': 'File Attachments',
                'description': 'File upload and attachment management'
            },
            {
                'id': 'diagnostics',
                'name': 'Apple Diagnostics',
                'description': 'Apple diagnostic reports and analysis'
            },
            {
                'id': 'repair_status',
                'name': 'Repair Status',
                'description': 'Repair progress tracking'
            },
            {
                'id': 'warranty_info',
                'name': 'Warranty Information',
                'description': 'Warranty number and status tracking'
            },
            {
                'id': 'damage_assessment',
                'name': 'Damage Assessment',
                'description': 'Damage description and evaluation'
            },
            {
                'id': 'rma_status',
                'name': 'RMA Status',
                'description': 'Return Merchandise Authorization tracking'
            }
        ]

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'enabled_sections': self.sections_list,
            'is_active': self.is_active,
            'created_by_id': self.created_by_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 