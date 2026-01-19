from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime, func, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
from models.base import Base
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
import logging
# Import enums from the new file
from models.enums import UserType, Country

class User(Base, UserMixin):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(128))
    user_type = Column(Enum(UserType), default=UserType.SUPERVISOR)
    company_id = Column(Integer, ForeignKey('companies.id'))
    assigned_country = Column(String(100), nullable=True)  # Match Asset.country field
    role = Column(String(50), nullable=True, default='user')
    theme_preference = Column(String(20), default='light')  # 'light' or 'dark'
    preferences = Column(JSON, nullable=True)  # Store user preferences like chart settings
    mention_filter_enabled = Column(Boolean, default=False)  # If True, user can only see allowed mentions
    is_deleted = Column(Boolean, default=False)  # Soft delete flag
    deleted_at = Column(DateTime, nullable=True)  # When the user was deleted
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="users")
    tickets_requested = relationship('Ticket', foreign_keys='Ticket.requester_id', back_populates='requester')
    tickets_assigned = relationship('Ticket', foreign_keys='Ticket.assigned_to_id', back_populates='assigned_to')
    uploaded_attachments = relationship('TicketAttachment', back_populates='uploader')
    uploaded_intake_attachments = relationship('IntakeAttachment', back_populates='uploader')
    created_intake_tickets = relationship('IntakeTicket', foreign_keys='IntakeTicket.created_by', back_populates='creator')
    assigned_intake_tickets = relationship('IntakeTicket', foreign_keys='IntakeTicket.assigned_to', back_populates='assignee')
    activities = relationship("Activity", back_populates="user", cascade="all, delete-orphan")
    assigned_assets = relationship("Asset", back_populates="assigned_to")
    asset_changes = relationship("AssetHistory", back_populates="user")
    accessory_changes = relationship("AccessoryHistory", back_populates="user")
    company_permissions = relationship("UserCompanyPermission", back_populates="user", cascade="all, delete-orphan")
    country_permissions = relationship("UserCountryPermission", back_populates="user", cascade="all, delete-orphan")
    queue_notifications = relationship("QueueNotification", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", order_by="Notification.created_at.desc()", cascade="all, delete-orphan")
    created_groups = relationship("Group", back_populates="created_by")
    group_memberships = relationship("GroupMembership", foreign_keys="GroupMembership.user_id", back_populates="user", cascade="all, delete-orphan")
    created_api_keys = relationship("APIKey", back_populates="created_by", cascade="all, delete-orphan")
    mention_permissions = relationship("UserMentionPermission", back_populates="user", cascade="all, delete-orphan")
    queue_permissions = relationship("UserQueuePermission", back_populates="user", cascade="all, delete-orphan")
    visibility_permissions = relationship("UserVisibilityPermission", foreign_keys="UserVisibilityPermission.user_id", back_populates="user", cascade="all, delete-orphan")
    import_permissions = relationship("UserImportPermission", foreign_keys="UserImportPermission.user_id", back_populates="user", cascade="all, delete-orphan")
    service_records = relationship("ServiceRecord", back_populates="performed_by")
    # Temporarily commenting out SavedInvoice relationship to fix import order
    # created_invoices = relationship("SavedInvoice", back_populates="creator", lazy="dynamic")

    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        """Check password hash"""
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        """Return username as full name (model doesn't have first/last name fields)"""
        return self.username

    @property
    def assigned_countries(self):
        """Get list of assigned countries for this user"""
        from sqlalchemy.orm import object_session
        from models.user_country_permission import UserCountryPermission

        # Try to use the session from the object first
        session = object_session(self)
        if session:
            permissions = session.query(UserCountryPermission).filter_by(user_id=self.id).all()
            return [perm.country for perm in permissions]

        # Fallback: create a new session
        from database import engine
        from sqlalchemy.orm import Session
        session = Session(engine)
        try:
            permissions = session.query(UserCountryPermission).filter_by(user_id=self.id).all()
            return [perm.country for perm in permissions]
        finally:
            session.close()

    @staticmethod
    def create(username, password, user_type='user', company=None, fixed_id=None):
        # Convert string user_type to enum if needed
        if isinstance(user_type, str):
            user_type = UserType[user_type.upper()]
            
        if fixed_id is not None:
            user_id = fixed_id
        else:
            import random
            user_id = random.randint(1000, 9999)
        
        return User(
            id=user_id,
            username=username,
            password_hash=password,  # In production, you should hash this
            user_type=user_type,
            company_id=company.id if company else None
        )

    @property
    def is_super_admin(self):
        """Check if user is a super admin"""
        return self.user_type == UserType.SUPER_ADMIN

    @property
    def is_developer(self):
        """Check if user is a developer"""
        return self.user_type == UserType.DEVELOPER

    @property
    def is_admin(self):
        """Check if user is an admin"""
        return self.user_type in [UserType.SUPER_ADMIN, UserType.DEVELOPER, UserType.COUNTRY_ADMIN]

    @property
    def is_country_admin(self):
        return self.user_type == UserType.COUNTRY_ADMIN

    @property
    def is_supervisor(self):
        """Check if user is a supervisor"""
        return self.user_type == UserType.SUPERVISOR

    @property
    def is_client(self):
        """Check if user is a client"""
        return self.user_type == UserType.CLIENT

    def can_access_company(self, company_id):
        """Check if user has access to a specific company"""
        # Super admins and developers can access all companies
        if self.is_super_admin or self.is_developer:
            return True
            
        # Check user's company permissions
        for perm in self.company_permissions:
            if perm.company_id == company_id and perm.can_view:
                return True
                
        return False

    def can_access_queue(self, queue_id):
        """Check if user has access to a specific queue based on user-level permissions"""
        from sqlalchemy.orm import Session
        from database import engine
        from models.user_queue_permission import UserQueuePermission

        # Super admins and developers can access all queues
        if self.is_super_admin or self.is_developer:
            return True

        session = Session(engine)
        try:
            # Check if there are specific permissions for this user and queue
            permission = session.query(UserQueuePermission).filter_by(
                user_id=self.id, queue_id=queue_id).first()

            # If a permission record exists, check the can_view flag
            if permission:
                return permission.can_view

            # If no specific permission exists, deny access by default
            return False
        except Exception as e:
            logging.error(f"Error checking queue access: {str(e)}")
            return False
        finally:
            session.close()

    def can_create_in_queue(self, queue_id):
        """Check if user has permission to create tickets in a specific queue"""
        from sqlalchemy.orm import Session
        from database import engine
        from models.user_queue_permission import UserQueuePermission
        from models.queue import Queue

        # Super admins and developers can create tickets in all queues
        if self.is_super_admin or self.is_developer:
            return True

        session = Session(engine)
        try:
            # Check if there are specific permissions for this user and queue
            permission = session.query(UserQueuePermission).filter_by(
                user_id=self.id, queue_id=queue_id).first()

            # If a permission record exists, check the can_create flag
            if permission:
                return permission.can_create

            # If no specific permission exists, deny access by default
            return False
        except Exception as e:
            logging.error(f"Error checking queue create permission: {str(e)}")
            return False
        finally:
            session.close()

    def can_edit_company_assets(self, company_id):
        """Check if user has edit permissions for a company's assets"""
        # Super admins and developers can edit all companies
        if self.is_super_admin or self.is_developer:
            return True
            
        # Check user's company permissions
        for perm in self.company_permissions:
            if perm.company_id == company_id and perm.can_edit:
                return True
                
        return False

    def can_access_documents(self):
        """Check if user has permission to access documents"""
        try:
            return self.permissions.can_access_documents
        except Exception as e:
            logging.error(f"Error checking document access: {str(e)}")
            return False

    def can_create_commercial_invoices(self):
        """Check if user has permission to create commercial invoices"""
        try:
            return self.permissions.can_create_commercial_invoices
        except Exception as e:
            logging.error(f"Error checking commercial invoice permission: {str(e)}")
            return False

    def can_create_packing_lists(self):
        """Check if user has permission to create packing lists"""
        try:
            return self.permissions.can_create_packing_lists
        except Exception as e:
            logging.error(f"Error checking packing list permission: {str(e)}")
            return False

    def get_accessible_companies(self):
        """Get list of companies the user has access to"""
        from sqlalchemy.orm import Session
        from database import engine
        from models.company import Company

        session = Session(engine)
        try:
            # Super admins and developers can access all companies
            if self.is_super_admin or self.is_developer:
                return session.query(Company).all()
                
            # Get companies where user has view permission
            companies = []
            for perm in self.company_permissions:
                if perm.can_view:
                    companies.append(perm.company)
            return companies
        finally:
            session.close()

    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'user_type': self.user_type.value if self.user_type else None,
            'company_id': self.company_id,
            'company': self.company.name if self.company else None,
            'assigned_country': self.assigned_country if self.assigned_country else None,
            'role': self.role or 'user',  # Return default role if None
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'accessible_companies': [{'id': p.company_id, 'name': p.company.name} for p in self.company_permissions if p.can_view]
        }

    def update_last_login(self):
        """Update the last login timestamp"""
        self.last_login = datetime.utcnow()
        
    @property
    def permissions(self):
        """Get user permissions based on user_type from the database"""
        from sqlalchemy.orm import Session
        from models.permission import Permission
        from database import engine
        
        # Log for debugging
        logging.info(f"Getting permissions for user {self.id} ({self.username}) of type {self.user_type}")
        
        # Create a new session
        session = Session(engine)
        try:
            # Get permission record for this user's type
            permission = session.query(Permission).filter_by(user_type=self.user_type).first()
            
            if not permission:
                # Create default permissions if none exist for this user type
                logging.info(f"No permissions found for {self.user_type}, creating defaults")
                default_permissions = Permission.get_default_permissions(self.user_type)
                permission = Permission(user_type=self.user_type, **default_permissions)
                session.add(permission)
                session.commit()
                logging.info(f"Created default permissions: can_edit_assets = {permission.can_edit_assets}")
            else:
                logging.info(f"Found existing permissions: can_edit_assets = {permission.can_edit_assets}")
            
            return permission
        except Exception as e:
            logging.error(f"Error getting permissions: {str(e)}")
            raise
        finally:
            session.close()

    @property
    def active_groups(self):
        """Get all active groups this user belongs to"""
        return [membership.group for membership in self.group_memberships 
                if membership.is_active and membership.group.is_active]
    
    def is_in_group(self, group_name):
        """Check if user is in a specific group"""
        return any(membership.group.name == group_name and membership.is_active 
                  for membership in self.group_memberships if membership.group.is_active)
    
    def get_group_names(self):
        """Get list of group names this user belongs to"""
        return [group.name for group in self.active_groups]