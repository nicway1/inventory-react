"""
User Category Permission Model
Controls which ticket categories a SUPERVISOR/COUNTRY_ADMIN can create
Empty permissions = NO access (must explicitly grant each category)
"""
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base


class UserCategoryPermission(Base):
    """Controls which ticket categories a user can create"""
    __tablename__ = 'user_category_permissions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    category_key = Column(String(100), nullable=False)  # Category enum key (e.g., 'ASSET_REPAIR', 'ASSET_CHECKOUT_CLAW')

    # Relationships
    user = relationship('User', foreign_keys=[user_id], back_populates='category_permissions')

    @classmethod
    def get_user_allowed_categories(cls, db_session, user_id):
        """Get list of category keys a user is allowed to create"""
        perms = db_session.query(cls.category_key).filter(
            cls.user_id == user_id
        ).all()
        return [p[0] for p in perms]

    @classmethod
    def user_can_create_category(cls, db_session, user_id, category_key):
        """Check if user can create tickets in a specific category"""
        return db_session.query(cls).filter(
            cls.user_id == user_id,
            cls.category_key == category_key
        ).first() is not None

    @classmethod
    def set_user_permissions(cls, db_session, user_id, category_keys):
        """Set user's category permissions (replaces existing)"""
        # Delete existing permissions
        db_session.query(cls).filter(cls.user_id == user_id).delete()

        # Add new permissions
        for category_key in category_keys:
            if category_key:  # Skip empty values
                perm = cls(user_id=user_id, category_key=category_key)
                db_session.add(perm)

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'category_key': self.category_key
        }
