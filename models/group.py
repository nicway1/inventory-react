from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from models.base import Base
from datetime import datetime

class Group(Base):
    """Model for user groups that can be mentioned"""
    __tablename__ = 'groups'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    created_by = relationship("User", back_populates="created_groups")
    memberships = relationship("GroupMembership", back_populates="group", cascade="all, delete-orphan")
    
    @property
    def members(self):
        """Get all active members of this group"""
        return [membership.user for membership in self.memberships if membership.is_active]
    
    @property
    def member_count(self):
        """Get count of active members"""
        return len([m for m in self.memberships if m.is_active])
    
    def add_member(self, user_id, added_by_id=None):
        """Add a user to this group"""
        from models.group_membership import GroupMembership
        
        # Check if membership already exists
        existing = next((m for m in self.memberships if m.user_id == user_id), None)
        if existing:
            if not existing.is_active:
                existing.is_active = True
                existing.added_at = datetime.utcnow()
                existing.added_by_id = added_by_id
            return existing
        
        # Create new membership
        membership = GroupMembership(
            group_id=self.id,
            user_id=user_id,
            added_by_id=added_by_id or self.created_by_id
        )
        self.memberships.append(membership)
        return membership
    
    def remove_member(self, user_id):
        """Remove a user from this group"""
        membership = next((m for m in self.memberships if m.user_id == user_id and m.is_active), None)
        if membership:
            membership.is_active = False
            membership.removed_at = datetime.utcnow()
            return True
        return False
    
    def has_member(self, user_id):
        """Check if user is an active member of this group"""
        return any(m.user_id == user_id and m.is_active for m in self.memberships)
    
    def to_dict(self):
        """Convert group to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_by_id': self.created_by_id,
            'created_by': self.created_by.username if self.created_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'member_count': self.member_count,
            'members': [{'id': m.user_id, 'username': m.user.username, 'email': m.user.email} 
                       for m in self.memberships if m.is_active]
        }
    
    def __repr__(self):
        return f'<Group {self.name} ({self.member_count} members)>'