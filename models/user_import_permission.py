"""
User Import Permission Model
Controls which import types a SUPERVISOR/COUNTRY_ADMIN can access
Empty permissions = NO access (must explicitly grant each import type)
"""
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base


class UserImportPermission(Base):
    """Controls which import types a user can access"""
    __tablename__ = 'user_import_permissions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    import_type = Column(String(50), nullable=False)  # 'inventory', 'customers', 'csv_import', 'asset_return', '1stbase', 'retool'

    # Relationships
    user = relationship('User', foreign_keys=[user_id], back_populates='import_permissions')

    # Valid import types
    VALID_TYPES = [
        'inventory',      # Import Inventory/Assets
        'customers',      # Import Customers
        'csv_import',     # Import (Firstbase Checkout Tickets)
        'asset_checkout', # Import Asset Checkout Tickets
        'asset_return',   # Import Asset Return Tickets
        '1stbase',        # Import Firstbase Asset Returns Tickets
        # 'retool'        # Import from Retool (HIDDEN - integrated into csv_import)
    ]

    # Import type display info
    TYPE_INFO = {
        'inventory': {
            'name': 'Import Inventory/Assets',
            'description': 'Bulk import assets from CSV/Excel files',
            'icon': 'fas fa-boxes',
            'color': 'purple',
            'route': 'inventory.import_inventory'
        },
        'customers': {
            'name': 'Import Customers',
            'description': 'Bulk import customer users from CSV',
            'icon': 'fas fa-users',
            'color': 'blue',
            'route': 'inventory.import_customers'
        },
        'csv_import': {
            'name': 'Import (Firstbase Asset Checkout Tickets)',
            'description': 'Import Firstbase asset checkout tickets from CSV',
            'icon': 'fas fa-file-csv',
            'color': 'green',
            'route': 'admin.csv_import'
        },
        'asset_checkout': {
            'name': 'Import Asset Checkout Tickets',
            'description': 'Import asset checkout tickets from CSV',
            'icon': 'fas fa-file-upload',
            'color': 'blue',
            'route': 'admin.asset_checkout_import'
        },
        'asset_return': {
            'name': 'Import Asset Return Tickets',
            'description': 'Import asset return tickets from CSV',
            'icon': 'fas fa-undo',
            'color': 'orange',
            'route': 'tickets.bulk_import_asset_return'
        },
        '1stbase': {
            'name': 'Import Firstbase Asset Returns Tickets',
            'description': 'Import Firstbase asset return orders as tickets',
            'icon': 'fas fa-database',
            'color': 'indigo',
            'route': 'tickets.bulk_import_1stbase'
        },
        'retool': {
            'name': 'Import from Retool',
            'description': 'Import data directly from Retool',
            'icon': 'fas fa-tools',
            'color': 'teal',
            'route': 'tickets.import_from_retool'
        }
    }

    @classmethod
    def get_user_allowed_types(cls, db_session, user_id):
        """Get list of import types a user is allowed to access"""
        perms = db_session.query(cls.import_type).filter(
            cls.user_id == user_id
        ).all()
        return [p[0] for p in perms]

    @classmethod
    def user_can_access(cls, db_session, user_id, import_type):
        """Check if user can access a specific import type"""
        return db_session.query(cls).filter(
            cls.user_id == user_id,
            cls.import_type == import_type
        ).first() is not None

    @classmethod
    def set_user_permissions(cls, db_session, user_id, import_types):
        """Set user's import permissions (replaces existing)"""
        # Delete existing permissions
        db_session.query(cls).filter(cls.user_id == user_id).delete()

        # Add new permissions
        for import_type in import_types:
            if import_type in cls.VALID_TYPES:
                perm = cls(user_id=user_id, import_type=import_type)
                db_session.add(perm)

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'import_type': self.import_type,
            'type_info': self.TYPE_INFO.get(self.import_type, {})
        }
