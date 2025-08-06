from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from models.base import Base
from datetime import datetime
import os

class KnowledgeAttachment(Base):
    __tablename__ = 'knowledge_attachments'
    
    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey('knowledge_articles.id'), nullable=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(BigInteger)  # Size in bytes
    mime_type = Column(String(100))
    uploaded_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    article = relationship("KnowledgeArticle", back_populates="attachments")
    uploader = relationship("User")
    
    def __repr__(self):
        return f'<KnowledgeAttachment {self.original_filename}>'
    
    def get_file_size_formatted(self):
        """Get human-readable file size"""
        if not self.file_size:
            return "Unknown"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.file_size < 1024.0:
                return f"{self.file_size:.1f} {unit}"
            self.file_size /= 1024.0
        return f"{self.file_size:.1f} TB"
    
    def is_image(self):
        """Check if attachment is an image"""
        if not self.mime_type:
            return False
        return self.mime_type.startswith('image/')
    
    def get_file_extension(self):
        """Get file extension from original filename"""
        return os.path.splitext(self.original_filename)[1].lower()