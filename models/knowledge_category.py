from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base
from datetime import datetime

class KnowledgeCategory(Base):
    __tablename__ = 'knowledge_categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    parent_id = Column(Integer, ForeignKey('knowledge_categories.id'))
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    articles = relationship("KnowledgeArticle", back_populates="category")
    parent = relationship("KnowledgeCategory", remote_side=[id])
    children = relationship("KnowledgeCategory", overlaps="parent")
    
    def __repr__(self):
        return f'<KnowledgeCategory {self.name}>'
    
    def get_article_count(self):
        """Get count of published articles in this category"""
        from models.knowledge_article import ArticleStatus
        return len([a for a in self.articles if a.status == ArticleStatus.PUBLISHED])
    
    def get_full_path(self):
        """Get full category path (e.g., 'IT > Hardware > Setup')"""
        if self.parent:
            return f"{self.parent.get_full_path()} > {self.name}"
        return self.name
    
    def get_all_children(self):
        """Get all descendant categories recursively"""
        children = list(self.children)
        for child in self.children:
            children.extend(child.get_all_children())
        return children