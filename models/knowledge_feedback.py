from sqlalchemy import Column, Integer, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base
from datetime import datetime

class KnowledgeFeedback(Base):
    __tablename__ = 'knowledge_feedback'
    
    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey('knowledge_articles.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    rating = Column(Integer)  # 1-5 scale
    comment = Column(Text)
    is_helpful = Column(Boolean)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    article = relationship("KnowledgeArticle", back_populates="feedback")
    user = relationship("User")
    
    def __repr__(self):
        return f'<KnowledgeFeedback for article {self.article_id} by user {self.user_id}>'
    
    def validate_rating(self):
        """Validate that rating is between 1 and 5"""
        if self.rating is not None and (self.rating < 1 or self.rating > 5):
            raise ValueError("Rating must be between 1 and 5")