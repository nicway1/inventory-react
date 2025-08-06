from sqlalchemy import Column, Integer, String, DateTime, Table, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base
from datetime import datetime

# Association table for many-to-many relationship between articles and tags
article_tags = Table('article_tags', Base.metadata,
    Column('article_id', Integer, ForeignKey('knowledge_articles.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('knowledge_tags.id'), primary_key=True)
)

class KnowledgeTag(Base):
    __tablename__ = 'knowledge_tags'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    articles = relationship("KnowledgeArticle", secondary=article_tags, back_populates="tags")
    
    def __repr__(self):
        return f'<KnowledgeTag {self.name}>'
    
    def get_article_count(self):
        """Get count of published articles with this tag"""
        from models.knowledge_article import ArticleStatus
        return len([a for a in self.articles if a.status == ArticleStatus.PUBLISHED])
    
    @classmethod
    def get_popular_tags(cls, limit=10):
        """Get most popular tags by article count"""
        # This would need to be implemented with proper database queries
        # For now, return empty list - will be implemented in the routes
        return []