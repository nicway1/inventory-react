from datetime import datetime
import json
import hashlib
import secrets
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base

class APIKey(Base):
    __tablename__ = 'api_keys'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    key_hash = Column(String(255), nullable=False, unique=True)
    permissions = Column(Text)  # JSON string of permissions
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    last_used_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_by_id = Column(Integer, ForeignKey('users.id'))
    
    # Usage tracking
    request_count = Column(Integer, default=0)
    last_request_ip = Column(String(45))
    
    # Relationships
    created_by = relationship('User', back_populates='created_api_keys')
    usage_logs = relationship('APIUsage', back_populates='api_key')
    
    def __init__(self, name, permissions=None, expires_at=None, created_by_id=None):
        self.name = name
        self.permissions = json.dumps(permissions or [])
        self.expires_at = expires_at
        self.created_by_id = created_by_id
        
        # Generate a secure API key
        raw_key = secrets.token_urlsafe(32)
        self.key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        self._raw_key = raw_key  # Store temporarily for return to user
    
    def get_permissions(self):
        """Get permissions as a list"""
        if self.permissions:
            return json.loads(self.permissions)
        return []
    
    def set_permissions(self, permissions):
        """Set permissions from a list"""
        self.permissions = json.dumps(permissions)
    
    def has_permission(self, permission):
        """Check if the API key has a specific permission"""
        perms = self.get_permissions()
        
        # Check for exact match
        if permission in perms:
            return True
            
        # Check for wildcard permissions
        for perm in perms:
            if perm.endswith(':*'):
                prefix = perm[:-2]
                if permission.startswith(prefix + ':'):
                    return True
        
        return False
    
    def is_expired(self):
        """Check if the API key is expired"""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False
    
    def is_valid(self):
        """Check if the API key is valid (active and not expired)"""
        return self.is_active and not self.is_expired()
    
    def update_usage(self, request_ip=None):
        """Update usage statistics"""
        self.request_count += 1
        self.last_used_at = datetime.utcnow()
        if request_ip:
            self.last_request_ip = request_ip
    
    def to_dict(self, include_key=False):
        """Convert to dictionary for JSON serialization"""
        data = {
            'id': self.id,
            'name': self.name,
            'permissions': self.get_permissions(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'is_active': self.is_active,
            'request_count': self.request_count,
            'last_request_ip': self.last_request_ip,
            'created_by_id': self.created_by_id
        }
        
        if include_key and hasattr(self, '_raw_key'):
            data['key'] = self._raw_key
            
        return data
    
    @staticmethod
    def hash_key(raw_key):
        """Hash a raw API key for storage/comparison"""
        return hashlib.sha256(raw_key.encode()).hexdigest()
    
    def __repr__(self):
        return f'<APIKey {self.name}>'