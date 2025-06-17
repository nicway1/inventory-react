from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime, func
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
    assigned_country = Column(Enum(Country), nullable=True)
    role = Column(String(50), nullable=True, default='user')
    theme_preference = Column(String(20), default='light')  # 'light' or 'dark'
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
    activities = relationship("Activity", back_populates="user")
    assigned_assets = relationship("Asset", back_populates="assigned_to")
    asset_changes = relationship("AssetHistory", back_populates="user")
    accessory_changes = relationship("AccessoryHistory", back_populates="user")
    company_permissions = relationship("UserCompanyPermission", back_populates="user")
    # Temporarily commenting out SavedInvoice relationship to fix import order
    # created_invoices = relationship("SavedInvoice", back_populates="creator", lazy="dynamic")

    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        """Check password hash"""
        return check_password_hash(self.password_hash, password)

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
    def is_admin(self):
        """Check if user is an admin"""
        return self.user_type in [UserType.SUPER_ADMIN, UserType.COUNTRY_ADMIN]

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
        # Super admins can access all companies
        if self.is_super_admin:
            return True
            
        # Check user's company permissions
        for perm in self.company_permissions:
            if perm.company_id == company_id and perm.can_view:
                return True
                
        return False

    def can_access_queue(self, queue_id):
        """Check if user has access to a specific queue based on company permissions"""
        from sqlalchemy.orm import Session
        from database import engine
        from models.company_queue_permission import CompanyQueuePermission
        
        # Super admins can access all queues
        if self.is_super_admin:
            return True
        
        session = Session(engine)
        try:
            # If user is not associated with a company, they can't access any queue
            if not self.company_id:
                return False
                
            # Check if there are specific permissions for this company and queue
            permission = session.query(CompanyQueuePermission).filter_by(
                company_id=self.company_id, queue_id=queue_id).first()
                
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
        from models.company_queue_permission import CompanyQueuePermission
        
        # Super admins can create tickets in all queues
        if self.is_super_admin:
            return True
        
        session = Session(engine)
        try:
            # If user is not associated with a company, they can't create tickets
            if not self.company_id:
                return False
                
            # Check if there are specific permissions for this company and queue
            permission = session.query(CompanyQueuePermission).filter_by(
                company_id=self.company_id, queue_id=queue_id).first()
                
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
        # Super admins can edit all companies
        if self.is_super_admin:
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
            # Super admins can access all companies
            if self.is_super_admin:
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
            'assigned_country': self.assigned_country.value if self.assigned_country else None,
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