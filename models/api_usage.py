from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from models.base import Base

class APIUsage(Base):
    __tablename__ = 'api_usage'
    
    id = Column(Integer, primary_key=True)
    api_key_id = Column(Integer, ForeignKey('api_keys.id'), nullable=False)
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Integer)
    request_ip = Column(String(45))
    user_agent = Column(String(255))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    error_message = Column(Text)
    
    # Relationships
    api_key = relationship('APIKey', back_populates='usage_logs')
    
    def __init__(self, api_key_id, endpoint, method, status_code, 
                 response_time_ms=None, request_ip=None, user_agent=None, error_message=None):
        self.api_key_id = api_key_id
        self.endpoint = endpoint
        self.method = method
        self.status_code = status_code
        self.response_time_ms = response_time_ms
        self.request_ip = request_ip
        self.user_agent = user_agent
        self.error_message = error_message
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'api_key_id': self.api_key_id,
            'endpoint': self.endpoint,
            'method': self.method,
            'status_code': self.status_code,
            'response_time_ms': self.response_time_ms,
            'request_ip': self.request_ip,
            'user_agent': self.user_agent,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'error_message': self.error_message
        }
    
    @staticmethod
    def get_usage_stats(api_key_id=None, days=30):
        """Get usage statistics for an API key or all keys"""
        from datetime import timedelta
        from database import SessionLocal
        
        session = SessionLocal()
        try:
            query = session.query(
                func.count(APIUsage.id).label('total_requests'),
                func.avg(APIUsage.response_time_ms).label('avg_response_time'),
                func.count(APIUsage.id).filter(APIUsage.status_code >= 400).label('error_count')
            )
            
            if api_key_id:
                query = query.filter(APIUsage.api_key_id == api_key_id)
            
            # Filter by date range
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            query = query.filter(APIUsage.timestamp >= cutoff_date)
            
            result = query.first()
            
            return {
                'total_requests': result.total_requests or 0,
                'avg_response_time': float(result.avg_response_time) if result.avg_response_time else 0,
                'error_count': result.error_count or 0,
                'error_rate': (result.error_count / result.total_requests * 100) if result.total_requests else 0
            }
        finally:
            session.close()
    
    @staticmethod
    def get_daily_usage(api_key_id=None, days=30):
        """Get daily usage statistics"""
        from datetime import timedelta
        from database import SessionLocal
        
        session = SessionLocal()
        try:
            query = session.query(
                func.date(APIUsage.timestamp).label('date'),
                func.count(APIUsage.id).label('request_count'),
                func.count(APIUsage.id).filter(APIUsage.status_code >= 400).label('error_count')
            )
            
            if api_key_id:
                query = query.filter(APIUsage.api_key_id == api_key_id)
            
            # Filter by date range
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            query = query.filter(APIUsage.timestamp >= cutoff_date)
            
            query = query.group_by(func.date(APIUsage.timestamp))
            query = query.order_by(func.date(APIUsage.timestamp))
            
            results = query.all()
            
            return [{
                'date': result.date.isoformat(),
                'request_count': result.request_count,
                'error_count': result.error_count,
                'error_rate': (result.error_count / result.request_count * 100) if result.request_count else 0
            } for result in results]
        finally:
            session.close()
    
    def __repr__(self):
        return f'<APIUsage {self.method} {self.endpoint} - {self.status_code}>'