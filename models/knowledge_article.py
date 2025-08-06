from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from models.base import Base
from datetime import datetime
import enum

class ArticleStatus(enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class ArticleVisibility(enum.Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"

class KnowledgeArticle(Base):
    __tablename__ = 'knowledge_articles'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text)  # Brief description for search results
    category_id = Column(Integer, ForeignKey('knowledge_categories.id'))
    author_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    visibility = Column(Enum(ArticleVisibility), default=ArticleVisibility.INTERNAL)
    status = Column(Enum(ArticleStatus), default=ArticleStatus.DRAFT)
    view_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    category = relationship("KnowledgeCategory", back_populates="articles")
    author = relationship("User")
    tags = relationship("KnowledgeTag", secondary="article_tags", back_populates="articles")
    feedback = relationship("KnowledgeFeedback", back_populates="article", cascade="all, delete-orphan")
    attachments = relationship("KnowledgeAttachment", back_populates="article", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<KnowledgeArticle {self.title}>'
    
    def increment_view_count(self):
        """Increment the view count for this article"""
        self.view_count += 1
    
    def get_average_rating(self):
        """Calculate average rating from feedback"""
        if not self.feedback:
            return 0
        ratings = [f.rating for f in self.feedback if f.rating is not None]
        return sum(ratings) / len(ratings) if ratings else 0
    
    def get_helpful_count(self):
        """Get count of helpful feedback"""
        return len([f for f in self.feedback if f.is_helpful is True])
    
    def get_not_helpful_count(self):
        """Get count of not helpful feedback"""
        return len([f for f in self.feedback if f.is_helpful is False])