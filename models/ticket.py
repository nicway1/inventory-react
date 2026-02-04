from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from models.base import Base

# Import models after class definition to avoid circular imports
from models.comment import Comment
from models.ticket_attachment import TicketAttachment

class TicketStatus(enum.Enum):
    NEW = "New"
    IN_PROGRESS = "In Progress"
    PROCESSING = "Processing"
    ON_HOLD = "On Hold"
    RESOLVED = "Resolved"
    RESOLVED_DELIVERED = "Resolved (All Package Delivered)"

class TicketPriority(enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

class TicketCategory(enum.Enum):
    PIN_REQUEST = "PIN Request"
    ASSET_REPAIR = "Asset Repair"
    BULK_DELIVERY_QUOTATION = "Bulk Delivery Quotation"
    REPAIR_QUOTE = "Repair Quote"
    ITAD_QUOTE = "ITAD Quote"
    ASSET_CHECKOUT = "Asset Checkout"
    ASSET_CHECKOUT1 = "Asset Checkout1"
    ASSET_CHECKOUT_SINGPOST = "Asset Checkout (SingPost)"
    ASSET_CHECKOUT_DHL = "Asset Checkout (DHL)"
    ASSET_CHECKOUT_UPS = "Asset Checkout (UPS)"
    ASSET_CHECKOUT_BLUEDART = "Asset Checkout (BlueDart)"
    ASSET_CHECKOUT_DTDC = "Asset Checkout (DTDC)"
    ASSET_CHECKOUT_AUTO = "Asset Checkout (Auto)"
    ASSET_CHECKOUT_CLAW = "Asset Checkout (claw)"
    ASSET_RETURN_CLAW = "Asset Return (claw)"
    ASSET_INTAKE = "Asset Intake"
    INTERNAL_TRANSFER = "Internal Transfer"

class RMAStatus(enum.Enum):
    PENDING_APPROVAL = "Pending Approval"
    APPROVED = "Approved"
    ITEM_SHIPPED = "Item Shipped"
    ITEM_RECEIVED = "Item Received"
    REPLACEMENT_SHIPPED = "Replacement Shipped"
    COMPLETED = "Completed"
    DENIED = "Denied"

class RepairStatus(enum.Enum):
    PENDING_ASSESSMENT = "Pending Assessment"
    PENDING_QUOTE = "Pending Quote"
    QUOTE_PROVIDED = "Quote Provided"
    REPAIR_APPROVED = "Repair Approved"
    REPAIR_IN_PROGRESS = "Repair in Progress"
    REPAIR_COMPLETED = "Repair Completed"
    PENDING_DISPOSAL = "Pending Disposal"
    DISPOSAL_APPROVED = "Disposal Approved"
    DISPOSAL_COMPLETED = "Disposal Completed"

class Ticket(Base):
    __tablename__ = 'tickets'

    id = Column(Integer, primary_key=True)
    subject = Column(String(200), nullable=False)
    description = Column(String(2000))
    requester_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    status = Column(SQLEnum(TicketStatus), default=TicketStatus.NEW)
    custom_status = Column(String(100), nullable=True)  # For custom ticket statuses
    priority = Column(SQLEnum(TicketPriority), default=TicketPriority.MEDIUM)
    category = Column(SQLEnum(TicketCategory))
    asset_id = Column(Integer, ForeignKey('assets.id'))
    assigned_to_id = Column(Integer, ForeignKey('users.id'))
    queue_id = Column(Integer, ForeignKey('queues.id'))
    accessory_id = Column(Integer, ForeignKey('accessories.id'))
    rma_status = Column(SQLEnum(RMAStatus))
    repair_status = Column(SQLEnum(RepairStatus))
    country = Column(String(100))
    damage_description = Column(String(1000))
    apple_diagnostics = Column(String(100))
    image_path = Column(String(500))
    return_description = Column(String(1000))  # Dedicated field for Asset Return descriptions
    return_tracking = Column(String(100))
    return_carrier = Column(String(50), default='singpost')  # Carrier for return shipment
    return_tracking_status = Column(String(100), default='Pending')  # Status for return tracking
    replacement_tracking = Column(String(100))
    warranty_number = Column(String(100))
    serial_number = Column(String(100))
    shipping_address = Column(String(500))
    shipping_tracking = Column(String(100))
    shipping_carrier = Column(String(50), default='singpost')  # Default to SingPost carrier
    customer_id = Column(Integer, ForeignKey('customer_users.id'))

    # Internal Transfer fields
    offboarding_customer_id = Column(Integer, ForeignKey('customer_users.id'), nullable=True)
    onboarding_customer_id = Column(Integer, ForeignKey('customer_users.id'), nullable=True)
    offboarding_details = Column(Text, nullable=True)  # Device details for offboarding
    offboarding_address = Column(String(500), nullable=True)
    onboarding_address = Column(String(500), nullable=True)

    firstbaseorderid = Column(String(100), nullable=True)  # Store order ID for duplicate prevention
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Add tracking status fields
    shipping_status = Column(String(100), default='Pending')
    return_status = Column(String(100), default='Pending')
    replacement_status = Column(String(100), default='Pending')
    
    # Multiple tracking fields for Asset Checkout (claw) - up to 5 packages
    shipping_tracking_2 = Column(String(100), nullable=True)
    shipping_carrier_2 = Column(String(50), nullable=True)
    shipping_status_2 = Column(String(100), nullable=True, default='Pending')
    
    shipping_tracking_3 = Column(String(100), nullable=True)
    shipping_carrier_3 = Column(String(50), nullable=True)
    shipping_status_3 = Column(String(100), nullable=True, default='Pending')
    
    shipping_tracking_4 = Column(String(100), nullable=True)
    shipping_carrier_4 = Column(String(50), nullable=True)
    shipping_status_4 = Column(String(100), nullable=True, default='Pending')
    
    shipping_tracking_5 = Column(String(100), nullable=True)
    shipping_carrier_5 = Column(String(50), nullable=True)
    shipping_status_5 = Column(String(100), nullable=True, default='Pending')
    
    # Asset Intake specific fields
    packing_list_path = Column(String(500))
    asset_csv_path = Column(String(500))
    notes = Column(String(2000))

    # Case Progress fields
    item_packed = Column(Boolean, default=False)
    item_packed_at = Column(DateTime, nullable=True)
    shipping_tracking_created_at = Column(DateTime, nullable=True)
    
    # Non-DB fields for tracking history
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.shipping_history = []  # Initialize shipping history as empty list
        
    def __getattr__(self, name):
        """Handle attributes that might not be initialized"""
        if name == 'shipping_history':
            return []
        raise AttributeError(f"'Ticket' object has no attribute '{name}'")

    # Relationships
    requester = relationship('User', foreign_keys=[requester_id], back_populates='tickets_requested')
    assigned_to = relationship('User', foreign_keys=[assigned_to_id], back_populates='tickets_assigned')
    comments = relationship('Comment', back_populates='ticket', cascade='all, delete-orphan')
    asset = relationship('Asset', foreign_keys=[asset_id], back_populates='tickets')
    assets = relationship('Asset', secondary='ticket_assets', back_populates='tickets')
    queue = relationship("Queue", back_populates="tickets")
    accessory = relationship("Accessory", back_populates="tickets")
    customer = relationship('CustomerUser', foreign_keys=[customer_id], back_populates='tickets')
    offboarding_customer = relationship('CustomerUser', foreign_keys=[offboarding_customer_id])
    onboarding_customer = relationship('CustomerUser', foreign_keys=[onboarding_customer_id])
    attachments = relationship('TicketAttachment', back_populates='ticket', cascade='all, delete-orphan')
    tracking_histories = relationship('TrackingHistory', back_populates='ticket', cascade='all, delete-orphan')
    accessories = relationship('TicketAccessory', back_populates='ticket', cascade='all, delete-orphan')
    asset_checkins = relationship('TicketAssetCheckin', back_populates='ticket', cascade='all, delete-orphan')
    service_records = relationship('ServiceRecord', back_populates='ticket', cascade='all, delete-orphan')
    # Remove non-existent relationships
    # shipments, rma_pickups, and rma_replacements are not defined in the model

    @property
    def display_id(self):
        """Return a formatted ticket ID (e.g., 'TICK-1001')"""
        return f'TICK-{self.id:04d}'

    @property
    def is_rma(self):
        """Check if this is an RMA ticket"""
        return self.category == TicketCategory.RMA_REQUEST

    @staticmethod
    def create(subject, description, requester_id, asset_id=None, category=None, priority='Medium'):
        """Create a new ticket with a random ID"""
        import random
        ticket_id = random.randint(1000, 9999)
        return Ticket(
            id=ticket_id,
            subject=subject,
            description=description,
            requester_id=requester_id,
            asset_id=asset_id,
            category=category,
            priority=priority
        )

    def update_rma_status(self, new_status):
        """Update RMA status"""
        if isinstance(new_status, RMAStatus):
            self.rma_status = new_status
            self.updated_at = datetime.utcnow()

    def change_status(self, new_status):
        """Change ticket status"""
        if isinstance(new_status, TicketStatus):
            self.status = new_status
            self.updated_at = datetime.utcnow()

    def assign_case_owner(self, user_id):
        """Assign ticket to a user"""
        self.assigned_to_id = user_id
        self.updated_at = datetime.utcnow()

    def get_category_display_name(self):
        """Get the display name for the ticket category (hides 'claw' designation)"""
        if self.category:
            # Remove (claw) from display name for cleaner UI
            return self.category.value.replace(' (claw)', '')
        else:
            # For custom categories, extract from description
            if self.description and self.description.startswith('[CUSTOM CATEGORY:'):
                try:
                    # Extract category name from [CUSTOM CATEGORY: category_name]
                    start = self.description.find('[CUSTOM CATEGORY:') + len('[CUSTOM CATEGORY:')
                    end = self.description.find(']', start)
                    if end > start:
                        category_name = self.description[start:end].strip()
                        
                        # Try to get display name from database
                        from database import SessionLocal
                        from models.ticket_category_config import TicketCategoryConfig
                        db = SessionLocal()
                        try:
                            config = db.query(TicketCategoryConfig).filter_by(name=category_name).first()
                            if config:
                                return config.display_name
                            else:
                                return category_name.replace('_', ' ').title()
                        finally:
                            db.close()
                except:
                    pass
            return 'Custom'

    def has_custom_section(self, section_name):
        """Check if this custom category ticket has a specific section enabled"""
        if self.category:
            # For standard enum categories, return False - they handle sections differently
            return False
        
        # For custom categories, check the configuration
        if self.description and self.description.startswith('[CUSTOM CATEGORY:'):
            try:
                # Extract category name from [CUSTOM CATEGORY: category_name]
                start = self.description.find('[CUSTOM CATEGORY:') + len('[CUSTOM CATEGORY:')
                end = self.description.find(']', start)
                if end > start:
                    category_name = self.description[start:end].strip()
                    
                    # Check if this section is enabled for this category
                    from database import SessionLocal
                    from models.ticket_category_config import TicketCategoryConfig
                    db = SessionLocal()
                    try:
                        config = db.query(TicketCategoryConfig).filter_by(name=category_name).first()
                        if config:
                            return config.has_section(section_name)
                        return False
                    finally:
                        db.close()
            except:
                pass
        return False

    def get_all_packages(self):
        """Get all packages with their tracking information for Asset Checkout (claw) tickets"""
        packages = []
        
        # Package 1 (main tracking) - only show if it has a tracking number
        if self.shipping_tracking:
            packages.append({
                'package_number': 1,
                'tracking_number': self.shipping_tracking,
                'carrier': self.shipping_carrier,
                'status': self.shipping_status or 'Pending'
            })
        
        # Package 2 - only show if it has a tracking number
        if self.shipping_tracking_2:
            packages.append({
                'package_number': 2,
                'tracking_number': self.shipping_tracking_2,
                'carrier': self.shipping_carrier_2,
                'status': self.shipping_status_2 or 'Pending'
            })
        
        # Package 3 - only show if it has a tracking number
        if self.shipping_tracking_3:
            packages.append({
                'package_number': 3,
                'tracking_number': self.shipping_tracking_3,
                'carrier': self.shipping_carrier_3,
                'status': self.shipping_status_3 or 'Pending'
            })
        
        # Package 4 - only show if it has a tracking number
        if self.shipping_tracking_4:
            packages.append({
                'package_number': 4,
                'tracking_number': self.shipping_tracking_4,
                'carrier': self.shipping_carrier_4,
                'status': self.shipping_status_4 or 'Pending'
            })
        
        # Package 5 - only show if it has a tracking number
        if self.shipping_tracking_5:
            packages.append({
                'package_number': 5,
                'tracking_number': self.shipping_tracking_5,
                'carrier': self.shipping_carrier_5,
                'status': self.shipping_status_5 or 'Pending'
            })
        
        return packages

    def get_package_items(self, package_number, db_session=None):
        """Get all items (assets and accessories) associated with a specific package"""
        from models.package_item import PackageItem
        from database import SessionLocal
        
        managed_session = db_session is None
        db = db_session or SessionLocal()
        try:
            items = db.query(PackageItem).filter_by(
                ticket_id=self.id,
                package_number=package_number
            ).order_by(PackageItem.created_at.asc()).all()
            
            return [{
                'id': item.id,
                'item_type': item.item_type,
                'item_name': item.item_name,
                'item_details': item.item_details,
                'quantity': item.quantity,
                'notes': item.notes,
                'asset_id': item.asset_id,
                'accessory_id': item.accessory_id
            } for item in items]
        finally:
            if managed_session:
                db.close()

    def add_package_item(self, package_number, asset_id=None, accessory_id=None, quantity=1, notes=None, db_session=None):
        """Add an asset or accessory to a specific package"""
        from models.package_item import PackageItem
        from database import SessionLocal
        
        if not asset_id and not accessory_id:
            raise ValueError("Either asset_id or accessory_id must be provided")
        
        if asset_id and accessory_id:
            raise ValueError("Cannot specify both asset_id and accessory_id")
        
        managed_session = db_session is None
        db = db_session or SessionLocal()
        try:
            # Check if this item is already associated with this package
            existing = db.query(PackageItem).filter_by(
                ticket_id=self.id,
                package_number=package_number,
                asset_id=asset_id,
                accessory_id=accessory_id
            ).first()
            
            if existing:
                # Update quantity if item already exists
                existing.quantity += quantity
                existing.notes = notes if notes else existing.notes
                existing.updated_at = datetime.utcnow()
                if managed_session:
                    db.commit()
                else:
                    db.flush()
                return existing
            else:
                # Create new package item association
                package_item = PackageItem(
                    ticket_id=self.id,
                    package_number=package_number,
                    asset_id=asset_id,
                    accessory_id=accessory_id,
                    quantity=quantity,
                    notes=notes
                )
                db.add(package_item)
                if managed_session:
                    db.commit()
                else:
                    db.flush()
                return package_item
        finally:
            if managed_session:
                db.close()

    def remove_package_item(self, package_item_id):
        """Remove an item from a package"""
        from models.package_item import PackageItem
        from database import SessionLocal
        
        db = SessionLocal()
        try:
            item = db.query(PackageItem).filter_by(
                id=package_item_id,
                ticket_id=self.id
            ).first()
            
            if item:
                db.delete(item)
                db.commit()
                return True
            return False
        finally:
            db.close()

    def get_next_available_package_number(self):
        """Get the next available package number (1-5) for adding new tracking"""
        if not self.shipping_tracking:
            return 1
        elif not self.shipping_tracking_2:
            return 2
        elif not self.shipping_tracking_3:
            return 3
        elif not self.shipping_tracking_4:
            return 4
        elif not self.shipping_tracking_5:
            return 5
        else:
            return None  # All 5 packages are used

    def get_checkin_progress(self, db_session=None):
        """Get check-in progress for Asset Intake tickets

        Returns:
            dict: {total, checked_in, pending, progress_percent}
        """
        from database import SessionLocal
        from models.ticket_asset_checkin import TicketAssetCheckin

        managed_session = db_session is None
        db = db_session or SessionLocal()
        try:
            # Get all assets associated with this ticket
            total_assets = len(self.assets) if self.assets else 0

            if total_assets == 0:
                return {
                    'total': 0,
                    'checked_in': 0,
                    'pending': 0,
                    'progress_percent': 0
                }

            # Count checked-in assets
            checked_in_count = db.query(TicketAssetCheckin).filter(
                TicketAssetCheckin.ticket_id == self.id,
                TicketAssetCheckin.checked_in == True
            ).count()

            pending = total_assets - checked_in_count
            progress_percent = int((checked_in_count / total_assets) * 100) if total_assets > 0 else 0

            return {
                'total': total_assets,
                'checked_in': checked_in_count,
                'pending': pending,
                'progress_percent': progress_percent
            }
        finally:
            if managed_session:
                db.close()

    def get_intake_step(self, db_session=None):
        """Get current intake step for Asset Intake tickets

        Step 1: Case Created (ticket exists)
        Step 2: Assets Added (has assets assigned)
        Step 3: All Checked In (all assets checked in, case can be closed)

        Returns:
            int: 1, 2, or 3
        """
        total_assets = len(self.assets) if self.assets else 0

        if total_assets == 0:
            return 1  # Step 1: Case Created, no assets yet

        progress = self.get_checkin_progress(db_session)

        if progress['pending'] == 0 and progress['total'] > 0:
            return 3  # Step 3: All assets checked in

        return 2  # Step 2: Assets added, check-in in progress

    def get_intake_steps_detail(self, db_session=None):
        """Get detailed intake steps with completion status

        Returns:
            list: [{'number': 1, 'label': 'Case Created', 'completed': True}, ...]
        """
        current_step = self.get_intake_step(db_session)
        progress = self.get_checkin_progress(db_session)

        steps = [
            {
                'number': 1,
                'label': 'Case Created',
                'completed': True  # Always completed if ticket exists
            },
            {
                'number': 2,
                'label': 'Assets Added',
                'completed': progress['total'] > 0
            },
            {
                'number': 3,
                'label': 'All Checked In',
                'completed': progress['total'] > 0 and progress['pending'] == 0
            }
        ]

        return {
            'current_step': current_step,
            'steps': steps,
            'progress': progress
        }

class TicketAccessory(Base):
    """Model for accessories received with Asset Return (Claw) tickets"""
    __tablename__ = 'ticket_accessories'

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'), nullable=False)
    name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)  # e.g., Keyboard, Mouse, Cable, Adapter, etc.
    quantity = Column(Integer, default=1)
    condition = Column(String(50), default='Good')  # e.g., Good, Fair, Poor
    notes = Column(Text)
    original_accessory_id = Column(Integer, ForeignKey('accessories.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    ticket = relationship('Ticket', back_populates='accessories')
    original_accessory = relationship('Accessory', foreign_keys=[original_accessory_id])

    def __repr__(self):
        return f"<TicketAccessory(id={self.id}, name='{self.name}', category='{self.category}')>" 
