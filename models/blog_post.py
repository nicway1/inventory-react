from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from models.base import Base
from datetime import datetime
import enum


class BlogPostStatus(enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class BlogPost(Base):
    __tablename__ = 'blog_posts'

    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    slug = Column(String(500), nullable=False, unique=True, index=True)
    content = Column(Text, nullable=False)
    excerpt = Column(Text)  # Short summary for blog listing
    featured_image = Column(String(500))  # URL or path to featured image
    author_id = Column(Integer, ForeignKey('users.id'))
    status = Column(Enum(BlogPostStatus), default=BlogPostStatus.DRAFT)
    meta_title = Column(String(255))  # SEO title
    meta_description = Column(Text)  # SEO description
    view_count = Column(Integer, default=0)
    published_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Store original WordPress post ID for import tracking
    wp_post_id = Column(Integer, unique=True, nullable=True)

    # Relationships
    author = relationship("User", backref="blog_posts")

    def __repr__(self):
        return f'<BlogPost {self.title}>'

    def increment_view_count(self):
        """Increment the view count for this post"""
        self.view_count += 1

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'content': self.content,
            'excerpt': self.excerpt,
            'featured_image': self.featured_image,
            'author': self.author.username if self.author else None,
            'status': self.status.value if self.status else None,
            'meta_title': self.meta_title,
            'meta_description': self.meta_description,
            'view_count': self.view_count,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_list_dict(self):
        """Shorter dictionary for list views"""
        return {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'excerpt': self.excerpt,
            'featured_image': self.featured_image,
            'author': self.author.username if self.author else None,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'view_count': self.view_count,
        }
