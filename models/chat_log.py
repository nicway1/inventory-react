"""
ChatLog model for storing chatbot conversation data
Used for training and improving the chatbot
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base


class ChatLog(Base):
    __tablename__ = 'chat_logs'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    session_id = Column(String(100), nullable=True)  # For grouping conversations

    # The user's query
    query = Column(Text, nullable=False)

    # The chatbot's response
    response = Column(Text, nullable=True)
    response_type = Column(String(50), nullable=True)  # greeting, answer, fallback, action_confirm, error

    # Matched question from knowledge base (if any)
    matched_question = Column(String(500), nullable=True)

    # Match score/confidence (if applicable)
    match_score = Column(Integer, nullable=True)

    # Was the response helpful? (for future feedback feature)
    was_helpful = Column(Boolean, nullable=True)
    feedback = Column(Text, nullable=True)

    # Action taken (if any)
    action_type = Column(String(50), nullable=True)  # update_ticket_status, assign_ticket, etc.
    action_executed = Column(Boolean, default=False)

    # Metadata
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="chat_logs")

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else None,
            'session_id': self.session_id,
            'query': self.query,
            'response': self.response,
            'response_type': self.response_type,
            'matched_question': self.matched_question,
            'match_score': self.match_score,
            'was_helpful': self.was_helpful,
            'feedback': self.feedback,
            'action_type': self.action_type,
            'action_executed': self.action_executed,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
