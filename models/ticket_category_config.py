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


class CategoryDisplayConfig(Base):
    """Model for managing display settings of both predefined and custom ticket categories"""
    __tablename__ = 'category_display_configs'

    id = Column(Integer, primary_key=True)
    category_key = Column(String(100), nullable=False, unique=True)  # e.g., 'PIN_REQUEST' or 'custom_category_name'
    display_name = Column(String(200), nullable=False)  # User-defined display name
    is_enabled = Column(Boolean, default=True)  # Whether category appears in dropdown
    is_predefined = Column(Boolean, default=False)  # True for enum categories, False for custom
    sort_order = Column(Integer, default=0)  # For ordering in dropdown
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<CategoryDisplayConfig(category_key='{self.category_key}', display_name='{self.display_name}', enabled={self.is_enabled})>"

    @staticmethod
    def get_predefined_categories():
        """Get all predefined categories from the TicketCategory enum"""
        from models.ticket import TicketCategory
        return [
            {
                'key': category.name,
                'default_display_name': category.value,
                'is_predefined': True
            }
            for category in TicketCategory
        ]

    @staticmethod
    def initialize_predefined_categories():
        """Initialize display configs for all predefined categories if they don't exist"""
        from database import SessionLocal
        from models.ticket import TicketCategory
        
        db = SessionLocal()
        try:
            for category in TicketCategory:
                existing = db.query(CategoryDisplayConfig).filter_by(category_key=category.name).first()
                if not existing:
                    config = CategoryDisplayConfig(
                        category_key=category.name,
                        display_name=category.value,
                        is_enabled=True,
                        is_predefined=True,
                        sort_order=list(TicketCategory).index(category)
                    )
                    db.add(config)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error initializing predefined categories: {str(e)}")
        finally:
            db.close()

    @staticmethod
    def get_enabled_categories():
        """Get all enabled categories for display in dropdowns"""
        from database import SessionLocal
        
        db = SessionLocal()
        try:
            configs = db.query(CategoryDisplayConfig).filter_by(is_enabled=True).order_by(CategoryDisplayConfig.sort_order).all()
            return [
                {
                    'key': config.category_key,
                    'display_name': config.display_name,
                    'is_predefined': config.is_predefined
                }
                for config in configs
            ]
        finally:
            db.close()

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'category_key': self.category_key,
            'display_name': self.display_name,
            'is_enabled': self.is_enabled,
            'is_predefined': self.is_predefined,
            'sort_order': self.sort_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 