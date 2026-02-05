"""
Import Session Model
Tracks all import operations performed in the system
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base


class ImportSession(Base):
    """Tracks import operations (acts as 'ticket' for imports)"""
    __tablename__ = 'import_sessions'

    id = Column(Integer, primary_key=True)
    display_id = Column(String(20), unique=True)  # IMP-0001 format
    import_type = Column(String(50), nullable=False)  # 'inventory', 'customers', 'csv_import', 'asset_return', '1stbase', 'retool'
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(20), default='pending')  # 'pending', 'processing', 'completed', 'failed'
    total_rows = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    file_name = Column(String(255), nullable=True)
    import_data = Column(Text, nullable=True)  # JSON of imported records (for detail view)
    error_details = Column(Text, nullable=True)  # JSON of errors
    notes = Column(Text, nullable=True)

    # Relationships
    user = relationship('User', backref='import_sessions')

    # Import type constants
    TYPE_INVENTORY = 'inventory'
    TYPE_CUSTOMERS = 'customers'
    TYPE_CSV_IMPORT = 'csv_import'
    TYPE_ASSET_CHECKOUT = 'asset_checkout'
    TYPE_ASSET_RETURN = 'asset_return'
    TYPE_1STBASE = '1stbase'
    TYPE_RETOOL = 'retool'

    # Import type display names
    TYPE_NAMES = {
        'inventory': 'Import Inventory/Assets',
        'customers': 'Import Customers',
        'csv_import': 'Import (Firstbase Checkout)',
        'asset_checkout': 'Import Asset Checkout Tickets',
        'asset_return': 'Import Asset Return Tickets',
        '1stbase': 'Import Firstbase Asset Returns Tickets',
        'retool': 'Import from Retool'
    }

    # Import type icons (Font Awesome)
    TYPE_ICONS = {
        'inventory': 'fas fa-boxes',
        'customers': 'fas fa-users',
        'csv_import': 'fas fa-file-csv',
        'asset_checkout': 'fas fa-file-upload',
        'asset_return': 'fas fa-undo',
        '1stbase': 'fas fa-database',
        'retool': 'fas fa-tools'
    }

    # Import type colors
    TYPE_COLORS = {
        'inventory': 'purple',
        'customers': 'blue',
        'csv_import': 'green',
        'asset_checkout': 'blue',
        'asset_return': 'orange',
        '1stbase': 'indigo',
        'retool': 'teal'
    }

    @classmethod
    def generate_display_id(cls, db_session):
        """Generate next display ID in IMP-XXXX format"""
        last_session = db_session.query(cls).order_by(cls.id.desc()).first()
        if last_session and last_session.display_id:
            try:
                last_num = int(last_session.display_id.split('-')[1])
                return f"IMP-{last_num + 1:04d}"
            except (ValueError, IndexError):
                pass
        return "IMP-0001"

    @classmethod
    def create(cls, db_session, import_type, user_id, file_name=None, notes=None):
        """Create a new import session"""
        session = cls(
            display_id=cls.generate_display_id(db_session),
            import_type=import_type,
            user_id=user_id,
            file_name=file_name,
            notes=notes,
            status='processing',
            started_at=datetime.utcnow()
        )
        db_session.add(session)
        db_session.flush()  # Get the ID without committing
        return session

    def complete(self, success_count, fail_count, import_data=None, error_details=None):
        """Mark import session as completed"""
        self.status = 'completed' if fail_count == 0 else ('failed' if success_count == 0 else 'completed')
        self.completed_at = datetime.utcnow()
        self.success_count = success_count
        self.fail_count = fail_count
        self.total_rows = success_count + fail_count
        if import_data:
            self.import_data = import_data
        if error_details:
            self.error_details = error_details

    def fail(self, error_details=None):
        """Mark import session as failed"""
        self.status = 'failed'
        self.completed_at = datetime.utcnow()
        if error_details:
            self.error_details = error_details

    @property
    def type_name(self):
        """Get display name for import type"""
        return self.TYPE_NAMES.get(self.import_type, self.import_type)

    @property
    def type_icon(self):
        """Get icon for import type"""
        return self.TYPE_ICONS.get(self.import_type, 'fas fa-file-import')

    @property
    def type_color(self):
        """Get color for import type"""
        return self.TYPE_COLORS.get(self.import_type, 'gray')

    @property
    def duration(self):
        """Get duration of import in seconds"""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'display_id': self.display_id,
            'import_type': self.import_type,
            'type_name': self.type_name,
            'type_icon': self.type_icon,
            'type_color': self.type_color,
            'user_id': self.user_id,
            'user_name': self.user.username if self.user else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'status': self.status,
            'total_rows': self.total_rows,
            'success_count': self.success_count,
            'fail_count': self.fail_count,
            'file_name': self.file_name,
            'notes': self.notes,
            'duration': self.duration
        }
