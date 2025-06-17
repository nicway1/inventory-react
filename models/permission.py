from sqlalchemy import Column, Integer, String, Boolean, Enum
from sqlalchemy.orm import relationship
from models.base import Base
from models.enums import UserType

class Permission(Base):
    __tablename__ = 'permissions'
    
    id = Column(Integer, primary_key=True)
    user_type = Column(Enum(UserType), nullable=False, unique=True)
    
    # Asset Permissions
    can_view_assets = Column(Boolean, default=True)
    can_edit_assets = Column(Boolean, default=False)
    can_delete_assets = Column(Boolean, default=False)
    can_create_assets = Column(Boolean, default=False)
    
    # Country-specific Asset Permissions
    can_view_country_assets = Column(Boolean, default=True)
    can_edit_country_assets = Column(Boolean, default=False)
    can_delete_country_assets = Column(Boolean, default=False)
    can_create_country_assets = Column(Boolean, default=False)
    
    # Accessory Permissions
    can_view_accessories = Column(Boolean, default=True)
    can_edit_accessories = Column(Boolean, default=False)
    can_delete_accessories = Column(Boolean, default=False)
    can_create_accessories = Column(Boolean, default=False)
    
    # Company Permissions
    can_view_companies = Column(Boolean, default=True)
    can_edit_companies = Column(Boolean, default=False)
    can_delete_companies = Column(Boolean, default=False)
    can_create_companies = Column(Boolean, default=False)
    
    # User Permissions
    can_view_users = Column(Boolean, default=True)
    can_edit_users = Column(Boolean, default=False)
    can_delete_users = Column(Boolean, default=False)
    can_create_users = Column(Boolean, default=False)
    
    # Ticket Permissions
    can_view_tickets = Column(Boolean, default=True)
    can_edit_tickets = Column(Boolean, default=False)
    can_delete_tickets = Column(Boolean, default=False)
    can_delete_own_tickets = Column(Boolean, default=False)
    can_create_tickets = Column(Boolean, default=True)
    
    # Report Permissions
    can_view_reports = Column(Boolean, default=True)
    can_generate_reports = Column(Boolean, default=False)
    
    # Import/Export Permissions
    can_import_data = Column(Boolean, default=False)
    can_export_data = Column(Boolean, default=True)
    
    # Document Permissions
    can_access_documents = Column(Boolean, default=True)
    can_create_commercial_invoices = Column(Boolean, default=True)
    can_create_packing_lists = Column(Boolean, default=True)

    @classmethod
    def permission_fields(cls):
        """Get all permission field names"""
        return [
            column.name for column in cls.__table__.columns 
            if column.name.startswith('can_')
        ]

    @staticmethod
    def get_default_permissions(user_type):
        """Get default permissions for a user type"""
        if user_type == UserType.SUPER_ADMIN:
            return {
                'can_view_assets': True,
                'can_edit_assets': True,
                'can_delete_assets': True,
                'can_create_assets': True,
                'can_view_country_assets': True,
                'can_edit_country_assets': True,
                'can_delete_country_assets': True,
                'can_create_country_assets': True,
                'can_view_accessories': True,
                'can_edit_accessories': True,
                'can_delete_accessories': True,
                'can_create_accessories': True,
                'can_view_companies': True,
                'can_edit_companies': True,
                'can_delete_companies': True,
                'can_create_companies': True,
                'can_view_users': True,
                'can_edit_users': True,
                'can_delete_users': True,
                'can_create_users': True,
                'can_view_tickets': True,
                'can_edit_tickets': True,
                'can_delete_tickets': True,
                'can_delete_own_tickets': True,
                'can_create_tickets': True,
                'can_view_reports': True,
                'can_generate_reports': True,
                'can_import_data': True,
                'can_export_data': True,
                'can_access_documents': True,
                'can_create_commercial_invoices': True,
                'can_create_packing_lists': True
            }
        elif user_type == UserType.COUNTRY_ADMIN:
            return {
                'can_view_assets': True,
                'can_edit_assets': False,
                'can_delete_assets': False,
                'can_create_assets': False,
                'can_view_country_assets': True,
                'can_edit_country_assets': True,
                'can_delete_country_assets': True,
                'can_create_country_assets': True,
                'can_view_accessories': True,
                'can_edit_accessories': True,
                'can_delete_accessories': False,
                'can_create_accessories': True,
                'can_view_companies': True,
                'can_edit_companies': False,
                'can_delete_companies': False,
                'can_create_companies': False,
                'can_view_users': True,
                'can_edit_users': False,
                'can_delete_users': False,
                'can_create_users': False,
                'can_view_tickets': True,
                'can_edit_tickets': True,
                'can_delete_tickets': False,
                'can_delete_own_tickets': True,
                'can_create_tickets': True,
                'can_view_reports': True,
                'can_generate_reports': True,
                'can_import_data': True,
                'can_export_data': True,
                'can_access_documents': True,
                'can_create_commercial_invoices': True,
                'can_create_packing_lists': True
            }
        elif user_type == UserType.CLIENT:
            return {
                'can_view_assets': True,
                'can_edit_assets': False,
                'can_delete_assets': False,
                'can_create_assets': False,
                'can_view_country_assets': False,
                'can_edit_country_assets': False,
                'can_delete_country_assets': False,
                'can_create_country_assets': False,
                'can_view_accessories': False,
                'can_edit_accessories': False,
                'can_delete_accessories': False,
                'can_create_accessories': False,
                'can_view_companies': False,
                'can_edit_companies': False,
                'can_delete_companies': False,
                'can_create_companies': False,
                'can_view_users': False,
                'can_edit_users': False,
                'can_delete_users': False,
                'can_create_users': False,
                'can_view_tickets': True,
                'can_edit_tickets': False,
                'can_delete_tickets': False,
                'can_delete_own_tickets': False,
                'can_create_tickets': True,
                'can_view_reports': False,
                'can_generate_reports': False,
                'can_import_data': False,
                'can_export_data': False,
                'can_access_documents': False,
                'can_create_commercial_invoices': False,
                'can_create_packing_lists': False
            }
        else:  # Supervisor
            return {
                'can_view_assets': True,
                'can_edit_assets': True,
                'can_delete_assets': False,
                'can_create_assets': False,
                'can_view_country_assets': True,
                'can_edit_country_assets': True,
                'can_delete_country_assets': False,
                'can_create_country_assets': False,
                'can_view_accessories': True,
                'can_edit_accessories': False,
                'can_delete_accessories': False,
                'can_create_accessories': False,
                'can_view_companies': True,
                'can_edit_companies': False,
                'can_delete_companies': False,
                'can_create_companies': False,
                'can_view_users': True,
                'can_edit_users': False,
                'can_delete_users': False,
                'can_create_users': False,
                'can_view_tickets': True,
                'can_edit_tickets': True,
                'can_delete_tickets': False,
                'can_delete_own_tickets': True,
                'can_create_tickets': True,
                'can_view_reports': True,
                'can_generate_reports': False,
                'can_import_data': False,
                'can_export_data': True,
                'can_access_documents': True,
                'can_create_commercial_invoices': True,
                'can_create_packing_lists': True
            } 