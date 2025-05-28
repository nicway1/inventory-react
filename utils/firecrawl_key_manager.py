import logging
from database import SessionLocal
from models.firecrawl_key import FirecrawlKey
from datetime import datetime

logger = logging.getLogger(__name__)

class FirecrawlKeyManager:
    """Manages Firecrawl API keys with automatic rotation"""
    
    def __init__(self):
        self.current_key = None
        self._session = None
    
    def get_session(self):
        """Get database session"""
        if not self._session:
            self._session = SessionLocal()
        return self._session
    
    def close_session(self):
        """Close database session"""
        if self._session:
            self._session.close()
            self._session = None
    
    def get_current_key(self):
        """Get the current active API key"""
        session = self.get_session()
        try:
            # Try to get cached current key
            if self.current_key and not self.current_key.is_exhausted:
                return self.current_key.api_key
            
            # Get primary key from database
            primary_key = FirecrawlKey.get_active_key(session)
            
            if primary_key and not primary_key.is_exhausted:
                self.current_key = primary_key
                return primary_key.api_key
            
            # If no primary or primary is exhausted, rotate
            return self.rotate_key()
        
        except Exception as e:
            logger.error(f"Error getting current key: {str(e)}")
            return None
    
    def rotate_key(self):
        """Rotate to the next available key"""
        session = self.get_session()
        try:
            logger.info("Rotating Firecrawl API key...")
            
            # Rotate to next available key
            next_key = FirecrawlKey.rotate_primary_key(session)
            
            if next_key:
                self.current_key = next_key
                logger.info(f"Rotated to key: {next_key.name} (Usage: {next_key.usage_count}/{next_key.limit_count})")
                return next_key.api_key
            else:
                logger.warning("No available Firecrawl API keys found!")
                return None
        
        except Exception as e:
            logger.error(f"Error rotating key: {str(e)}")
            session.rollback()
            return None
    
    def record_usage(self, success=True):
        """Record usage of the current key"""
        if not self.current_key:
            return
        
        session = self.get_session()
        try:
            # Increment usage
            self.current_key.increment_usage()
            session.commit()
            
            logger.debug(f"Recorded usage for key {self.current_key.name}: {self.current_key.usage_count}/{self.current_key.limit_count}")
            
            # Check if key is exhausted and rotate if needed
            if self.current_key.is_exhausted:
                logger.warning(f"Key {self.current_key.name} exhausted. Rotating...")
                self.rotate_key()
        
        except Exception as e:
            logger.error(f"Error recording usage: {str(e)}")
            session.rollback()
    
    def add_key(self, name, api_key, limit=500, notes=None):
        """Add a new API key"""
        session = self.get_session()
        try:
            # Check if key already exists
            existing = session.query(FirecrawlKey).filter_by(api_key=api_key).first()
            if existing:
                raise ValueError("API key already exists")
            
            # Create new key
            new_key = FirecrawlKey(
                name=name,
                api_key=api_key,
                limit_count=limit,
                notes=notes,
                is_active=True
            )
            
            # If this is the first key, make it primary
            primary_exists = session.query(FirecrawlKey).filter_by(is_primary=True).first()
            if not primary_exists:
                new_key.is_primary = True
            
            session.add(new_key)
            session.commit()
            
            logger.info(f"Added new Firecrawl API key: {name}")
            return new_key
        
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding key: {str(e)}")
            raise
    
    def get_all_keys(self):
        """Get all API keys with their status"""
        session = self.get_session()
        try:
            return session.query(FirecrawlKey).order_by(FirecrawlKey.created_at.asc()).all()
        except Exception as e:
            logger.error(f"Error getting all keys: {str(e)}")
            return []
    
    def get_key_stats(self):
        """Get statistics about all keys"""
        session = self.get_session()
        try:
            all_keys = session.query(FirecrawlKey).all()
            
            stats = {
                'total_keys': len(all_keys),
                'active_keys': len([k for k in all_keys if k.is_active and not k.is_exhausted]),
                'exhausted_keys': len([k for k in all_keys if k.is_exhausted]),
                'total_usage': sum(k.usage_count for k in all_keys),
                'total_limit': sum(k.limit_count for k in all_keys),
                'current_key': self.current_key.name if self.current_key else None
            }
            
            return stats
        except Exception as e:
            logger.error(f"Error getting key stats: {str(e)}")
            return {}
    
    def delete_key(self, key_id):
        """Delete an API key"""
        session = self.get_session()
        try:
            key = session.query(FirecrawlKey).get(key_id)
            if not key:
                raise ValueError("Key not found")
            
            # If deleting primary key, rotate first
            if key.is_primary:
                self.rotate_key()
            
            session.delete(key)
            session.commit()
            
            logger.info(f"Deleted Firecrawl API key: {key.name}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting key: {str(e)}")
            raise
    
    def reset_key_usage(self, key_id):
        """Reset usage count for a key"""
        session = self.get_session()
        try:
            key = session.query(FirecrawlKey).get(key_id)
            if not key:
                raise ValueError("Key not found")
            
            key.usage_count = 0
            key.is_active = True
            session.commit()
            
            logger.info(f"Reset usage for key: {key.name}")
            return key
        except Exception as e:
            session.rollback()
            logger.error(f"Error resetting key usage: {str(e)}")
            raise

# Global instance
firecrawl_key_manager = FirecrawlKeyManager() 