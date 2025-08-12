"""
API Key Management Service

This module provides functionality for managing API keys including:
- Key generation and validation
- Permission management
- Usage tracking
- Security features
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict, Any
from database import SessionLocal
from models.api_key import APIKey
from models.api_usage import APIUsage

# Predefined permission groups
PERMISSION_GROUPS = {
    'read_only': [
        'tickets:read',
        'users:read',
        'inventory:read'
    ],
    'tickets_full': [
        'tickets:read',
        'tickets:write',
        'tickets:delete'
    ],
    'full_access': [
        'tickets:*',
        'users:*',
        'inventory:*',
        'admin:*'
    ],
    'mobile_app': [
        'tickets:read',
        'tickets:write',
        'users:read',
        'inventory:read',
        'sync:*'
    ],
    'analytics_only': [
        'analytics:read',
        'usage:read'
    ]
}

class APIKeyManager:
    """Service class for managing API keys"""
    
    @staticmethod
    def generate_key(name: str, permissions: List[str] = None, 
                    expires_at: datetime = None, created_by_id: int = None) -> Tuple[bool, str, APIKey]:
        """
        Generate a new API key
        
        Args:
            name: Human-readable name for the key
            permissions: List of permissions to grant
            expires_at: Optional expiration date
            created_by_id: ID of the user creating the key
            
        Returns:
            Tuple of (success, message, api_key)
        """
        try:
            # Validate input
            if not name or len(name.strip()) == 0:
                return False, "API key name is required", None
            
            if len(name) > 100:
                return False, "API key name must be 100 characters or less", None
            
            # Check if name already exists
            session = SessionLocal()
            try:
                existing = session.query(APIKey).filter_by(name=name.strip()).first()
                if existing:
                    return False, "An API key with this name already exists", None
            finally:
                session.close()
            
            # Set default permissions if none provided
            if permissions is None:
                permissions = PERMISSION_GROUPS['read_only']
            
            # Validate permissions
            valid_permissions = APIKeyManager._validate_permissions(permissions)
            if not valid_permissions:
                return False, "Invalid permissions provided", None
            
            # Create the API key
            api_key = APIKey(
                name=name.strip(),
                permissions=permissions,
                expires_at=expires_at,
                created_by_id=created_by_id
            )
            
            # Save to database
            session = SessionLocal()
            try:
                session.add(api_key)
                session.commit()
                session.refresh(api_key)
            finally:
                session.close()
            
            return True, "API key created successfully", api_key
            
        except Exception as e:
            return False, f"Error creating API key: {str(e)}", None
    
    @staticmethod
    def validate_key(key: str) -> Tuple[bool, Optional[APIKey], str]:
        """
        Validate an API key
        
        Args:
            key: The raw API key to validate
            
        Returns:
            Tuple of (is_valid, api_key_object, message)
        """
        try:
            if not key:
                return False, None, "API key is required"
            
            # Hash the provided key
            key_hash = APIKey.hash_key(key)
            
            # Find the API key in database
            session = SessionLocal()
            try:
                api_key = session.query(APIKey).filter_by(key_hash=key_hash).first()
            finally:
                session.close()
            
            if not api_key:
                return False, None, "Invalid API key"
            
            if not api_key.is_valid():
                if not api_key.is_active:
                    return False, api_key, "API key is disabled"
                elif api_key.is_expired():
                    return False, api_key, "API key has expired"
                else:
                    return False, api_key, "API key is not valid"
            
            return True, api_key, "API key is valid"
            
        except Exception as e:
            return False, None, f"Error validating API key: {str(e)}"
    
    @staticmethod
    def revoke_key(key_id: int) -> Tuple[bool, str]:
        """
        Revoke (disable) an API key
        
        Args:
            key_id: ID of the API key to revoke
            
        Returns:
            Tuple of (success, message)
        """
        session = SessionLocal()
        try:
            api_key = session.query(APIKey).get(key_id)
            if not api_key:
                return False, "API key not found"
            
            api_key.is_active = False
            session.commit()
            
            return True, "API key revoked successfully"
            
        except Exception as e:
            session.rollback()
            return False, f"Error revoking API key: {str(e)}"
        finally:
            session.close()
    
    @staticmethod
    def activate_key(key_id: int) -> Tuple[bool, str]:
        """
        Activate a previously revoked API key
        
        Args:
            key_id: ID of the API key to activate
            
        Returns:
            Tuple of (success, message)
        """
        session = SessionLocal()
        try:
            api_key = session.query(APIKey).get(key_id)
            if not api_key:
                return False, "API key not found"
            
            if api_key.is_expired():
                return False, "Cannot activate expired API key"
            
            api_key.is_active = True
            session.commit()
            
            return True, "API key activated successfully"
            
        except Exception as e:
            session.rollback()
            return False, f"Error activating API key: {str(e)}"
        finally:
            session.close()
    
    @staticmethod
    def list_keys(include_inactive: bool = False) -> List[APIKey]:
        """
        List all API keys
        
        Args:
            include_inactive: Whether to include inactive keys
            
        Returns:
            List of APIKey objects
        """
        session = SessionLocal()
        try:
            query = session.query(APIKey)
            
            if not include_inactive:
                query = query.filter_by(is_active=True)
            
            return query.order_by(APIKey.created_at.desc()).all()
            
        except Exception as e:
            print(f"Error listing API keys: {e}")
            return []
        finally:
            session.close()
    
    @staticmethod
    def update_permissions(key_id: int, permissions: List[str]) -> Tuple[bool, str]:
        """
        Update permissions for an API key
        
        Args:
            key_id: ID of the API key to update
            permissions: New list of permissions
            
        Returns:
            Tuple of (success, message)
        """
        session = SessionLocal()
        try:
            api_key = session.query(APIKey).get(key_id)
            if not api_key:
                return False, "API key not found"
            
            # Validate permissions
            if not APIKeyManager._validate_permissions(permissions):
                return False, "Invalid permissions provided"
            
            api_key.set_permissions(permissions)
            session.commit()
            
            return True, "Permissions updated successfully"
            
        except Exception as e:
            session.rollback()
            return False, f"Error updating permissions: {str(e)}"
        finally:
            session.close()
    
    @staticmethod
    def log_usage(api_key_id: int, endpoint: str, method: str, status_code: int,
                  response_time_ms: int = None, request_ip: str = None, 
                  user_agent: str = None, error_message: str = None) -> bool:
        """
        Log API usage
        
        Args:
            api_key_id: ID of the API key used
            endpoint: The endpoint that was called
            method: HTTP method used
            status_code: HTTP response status code
            response_time_ms: Response time in milliseconds
            request_ip: IP address of the request
            user_agent: User agent string
            error_message: Error message if any
            
        Returns:
            True if logged successfully, False otherwise
        """
        try:
            usage = APIUsage(
                api_key_id=api_key_id,
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                response_time_ms=response_time_ms,
                request_ip=request_ip,
                user_agent=user_agent,
                error_message=error_message
            )
            
            session = SessionLocal()
            try:
                session.add(usage)
                
                # Update API key usage stats
                api_key = session.query(APIKey).get(api_key_id)
                if api_key:
                    api_key.update_usage(request_ip)
                
                session.commit()
                return True
                
            except Exception as e:
                session.rollback()
                print(f"Error logging API usage: {e}")
                return False
            finally:
                session.close()
        except Exception as e:
            print(f"Error creating usage log: {e}")
            return False
    
    @staticmethod
    def get_usage_stats(api_key_id: int = None, days: int = 30) -> Dict[str, Any]:
        """
        Get usage statistics
        
        Args:
            api_key_id: Optional API key ID to filter by
            days: Number of days to look back
            
        Returns:
            Dictionary with usage statistics
        """
        try:
            return APIUsage.get_usage_stats(api_key_id, days)
        except Exception as e:
            print(f"Error getting usage stats: {e}")
            return {
                'total_requests': 0,
                'avg_response_time': 0,
                'error_count': 0,
                'error_rate': 0
            }
    
    @staticmethod
    def get_daily_usage(api_key_id: int = None, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get daily usage statistics
        
        Args:
            api_key_id: Optional API key ID to filter by
            days: Number of days to look back
            
        Returns:
            List of daily usage statistics
        """
        try:
            return APIUsage.get_daily_usage(api_key_id, days)
        except Exception as e:
            print(f"Error getting daily usage: {e}")
            return []
    
    @staticmethod
    def cleanup_expired_keys() -> int:
        """
        Cleanup expired API keys by marking them as inactive
        
        Returns:
            Number of keys that were deactivated
        """
        session = SessionLocal()
        try:
            expired_keys = session.query(APIKey).filter(
                APIKey.expires_at < datetime.utcnow(),
                APIKey.is_active == True
            ).all()
            
            count = 0
            for key in expired_keys:
                key.is_active = False
                count += 1
            
            if count > 0:
                session.commit()
            
            return count
            
        except Exception as e:
            session.rollback()
            print(f"Error cleaning up expired keys: {e}")
            return 0
        finally:
            session.close()
    
    @staticmethod
    def _validate_permissions(permissions: List[str]) -> bool:
        """
        Validate a list of permissions
        
        Args:
            permissions: List of permission strings to validate
            
        Returns:
            True if all permissions are valid, False otherwise
        """
        if not isinstance(permissions, list):
            return False
        
        # Define valid permission patterns
        valid_patterns = [
            'tickets:read', 'tickets:write', 'tickets:delete', 'tickets:*',
            'users:read', 'users:write', 'users:delete', 'users:*',
            'inventory:read', 'inventory:write', 'inventory:delete', 'inventory:*',
            'admin:read', 'admin:write', 'admin:*',
            'sync:read', 'sync:write', 'sync:*',
            'analytics:read', 'analytics:*',
            'usage:read', 'usage:*'
        ]
        
        for permission in permissions:
            if not isinstance(permission, str):
                return False
            if permission not in valid_patterns:
                return False
        
        return True
    
    @staticmethod
    def get_permission_groups() -> Dict[str, List[str]]:
        """
        Get all predefined permission groups
        
        Returns:
            Dictionary of permission groups
        """
        return PERMISSION_GROUPS.copy()
    
    @staticmethod
    def extend_expiration(key_id: int, days: int = 30) -> Tuple[bool, str]:
        """
        Extend the expiration date of an API key
        
        Args:
            key_id: ID of the API key
            days: Number of days to extend
            
        Returns:
            Tuple of (success, message)
        """
        session = SessionLocal()
        try:
            api_key = session.query(APIKey).get(key_id)
            if not api_key:
                return False, "API key not found"
            
            if api_key.expires_at:
                # Extend from current expiration date
                api_key.expires_at = api_key.expires_at + timedelta(days=days)
            else:
                # Set expiration from now
                api_key.expires_at = datetime.utcnow() + timedelta(days=days)
            
            session.commit()
            
            return True, f"API key expiration extended by {days} days"
            
        except Exception as e:
            session.rollback()
            return False, f"Error extending expiration: {str(e)}"
        finally:
            session.close()