"""
API Authentication and Authorization Middleware

This module provides decorators and utilities for:
- API key authentication
- Permission-based authorization
- Rate limiting
- Request logging
"""

import time
from functools import wraps
from typing import List, Optional, Tuple, Dict, Any
from flask import request, jsonify, g
from datetime import datetime, timedelta
from collections import defaultdict

from utils.api_key_manager import APIKeyManager
from models.api_key import APIKey

# Rate limiting storage (in production, use Redis or similar)
rate_limit_storage = defaultdict(list)

class APIError(Exception):
    """Custom exception for API errors"""
    def __init__(self, message: str, status_code: int = 400, error_code: str = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)

def create_error_response(error_code: str, message: str, status_code: int = 400, details: Dict = None) -> Tuple[Dict, int]:
    """
    Create a standardized error response
    
    Args:
        error_code: Unique error code
        message: Human-readable error message
        status_code: HTTP status code
        details: Additional error details
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    response = {
        "error": {
            "code": error_code,
            "message": message,
            "details": {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "request_id": getattr(g, 'request_id', 'unknown')
            }
        }
    }
    
    if details:
        response["error"]["details"].update(details)
    
    return response, status_code

def extract_api_key(request) -> Optional[str]:
    """
    Extract API key from request headers
    
    Args:
        request: Flask request object
        
    Returns:
        API key string or None if not found
    """
    # Check Authorization header (Bearer token)
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]  # Remove 'Bearer ' prefix
    
    # Check X-API-Key header
    api_key = request.headers.get('X-API-Key')
    if api_key:
        return api_key
    
    # Check query parameter (less secure, but sometimes needed)
    api_key = request.args.get('api_key')
    if api_key:
        return api_key
    
    return None

def validate_api_request(request) -> Tuple[bool, Optional[APIKey], str]:
    """
    Validate an incoming API request
    
    Args:
        request: Flask request object
        
    Returns:
        Tuple of (is_valid, api_key_object, error_message)
    """
    try:
        # Extract API key
        api_key = extract_api_key(request)
        if not api_key:
            return False, None, "API key is required"
        
        # Validate the key
        is_valid, api_key_obj, message = APIKeyManager.validate_key(api_key)
        
        return is_valid, api_key_obj, message
        
    except Exception as e:
        return False, None, f"Error validating request: {str(e)}"

def check_rate_limit(api_key: APIKey, limit: int = 1000, window: int = 3600) -> Tuple[bool, Dict]:
    """
    Check if API key has exceeded rate limit
    
    Args:
        api_key: APIKey object
        limit: Maximum requests per window
        window: Time window in seconds
        
    Returns:
        Tuple of (is_allowed, rate_limit_info)
    """
    try:
        now = time.time()
        key_id = str(api_key.id)
        
        # Clean old entries
        rate_limit_storage[key_id] = [
            timestamp for timestamp in rate_limit_storage[key_id]
            if now - timestamp < window
        ]
        
        current_count = len(rate_limit_storage[key_id])
        
        rate_limit_info = {
            'limit': limit,
            'remaining': max(0, limit - current_count),
            'reset': int(now + window),
            'window': window
        }
        
        if current_count >= limit:
            return False, rate_limit_info
        
        # Add current request
        rate_limit_storage[key_id].append(now)
        rate_limit_info['remaining'] -= 1
        
        return True, rate_limit_info
        
    except Exception as e:
        print(f"Error checking rate limit: {e}")
        # Allow request if rate limiting fails
        return True, {'limit': limit, 'remaining': limit, 'reset': int(time.time() + window)}

def require_api_key(permissions: List[str] = None, rate_limit: int = 1000, rate_window: int = 3600):
    """
    Decorator to require API key authentication and authorization
    
    Args:
        permissions: List of required permissions
        rate_limit: Maximum requests per window (default: 1000)
        rate_window: Rate limit window in seconds (default: 3600 = 1 hour)
        
    Returns:
        Decorated function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            
            try:
                # Generate request ID for tracking
                g.request_id = f"req_{int(time.time() * 1000)}"
                
                # Validate API key
                is_valid, api_key, error_message = validate_api_request(request)
                
                if not is_valid:
                    error_code = "INVALID_API_KEY" if not api_key else "API_KEY_DISABLED"
                    response, status_code = create_error_response(
                        error_code, error_message, 401
                    )
                    
                    # Log failed authentication
                    if api_key:
                        APIKeyManager.log_usage(
                            api_key.id,
                            request.endpoint or request.path,
                            request.method,
                            401,
                            int((time.time() - start_time) * 1000),
                            request.remote_addr,
                            request.headers.get('User-Agent'),
                            error_message
                        )
                    
                    return jsonify(response), status_code
                
                # Check permissions
                if permissions:
                    missing_permissions = []
                    for permission in permissions:
                        if not api_key.has_permission(permission):
                            missing_permissions.append(permission)
                    
                    if missing_permissions:
                        response, status_code = create_error_response(
                            "INSUFFICIENT_PERMISSIONS",
                            f"Missing required permissions: {', '.join(missing_permissions)}",
                            403,
                            {"required_permissions": permissions, "missing_permissions": missing_permissions}
                        )
                        
                        # Log authorization failure
                        APIKeyManager.log_usage(
                            api_key.id,
                            request.endpoint or request.path,
                            request.method,
                            403,
                            int((time.time() - start_time) * 1000),
                            request.remote_addr,
                            request.headers.get('User-Agent'),
                            f"Missing permissions: {', '.join(missing_permissions)}"
                        )
                        
                        return jsonify(response), status_code
                
                # Check rate limit
                is_allowed, rate_info = check_rate_limit(api_key, rate_limit, rate_window)
                
                if not is_allowed:
                    response, status_code = create_error_response(
                        "RATE_LIMIT_EXCEEDED",
                        f"Rate limit exceeded. Maximum {rate_limit} requests per {rate_window} seconds.",
                        429,
                        rate_info
                    )
                    
                    # Log rate limit violation
                    APIKeyManager.log_usage(
                        api_key.id,
                        request.endpoint or request.path,
                        request.method,
                        429,
                        int((time.time() - start_time) * 1000),
                        request.remote_addr,
                        request.headers.get('User-Agent'),
                        "Rate limit exceeded"
                    )
                    
                    # Add rate limit headers
                    response_obj = jsonify(response)
                    response_obj.headers['X-RateLimit-Limit'] = str(rate_info['limit'])
                    response_obj.headers['X-RateLimit-Remaining'] = str(rate_info['remaining'])
                    response_obj.headers['X-RateLimit-Reset'] = str(rate_info['reset'])
                    response_obj.headers['Retry-After'] = str(rate_info['window'])
                    
                    return response_obj, status_code
                
                # Store API key in Flask's g object for use in the route
                g.api_key = api_key
                g.rate_limit_info = rate_info
                
                # Call the original function
                result = f(*args, **kwargs)
                
                # Log successful request
                response_time = int((time.time() - start_time) * 1000)
                status_code = 200  # Default, may be overridden by the response
                
                # Try to extract status code from response
                if isinstance(result, tuple) and len(result) >= 2:
                    status_code = result[1]
                elif hasattr(result, 'status_code'):
                    status_code = result.status_code
                
                APIKeyManager.log_usage(
                    api_key.id,
                    request.endpoint or request.path,
                    request.method,
                    status_code,
                    response_time,
                    request.remote_addr,
                    request.headers.get('User-Agent')
                )
                
                # Add rate limit headers to successful responses
                if isinstance(result, tuple):
                    response_obj, status = result
                    if hasattr(response_obj, 'headers'):
                        response_obj.headers['X-RateLimit-Limit'] = str(rate_info['limit'])
                        response_obj.headers['X-RateLimit-Remaining'] = str(rate_info['remaining'])
                        response_obj.headers['X-RateLimit-Reset'] = str(rate_info['reset'])
                    return response_obj, status
                else:
                    if hasattr(result, 'headers'):
                        result.headers['X-RateLimit-Limit'] = str(rate_info['limit'])
                        result.headers['X-RateLimit-Remaining'] = str(rate_info['remaining'])
                        result.headers['X-RateLimit-Reset'] = str(rate_info['reset'])
                    return result
                
            except Exception as e:
                # Log internal error
                response_time = int((time.time() - start_time) * 1000)
                
                if hasattr(g, 'api_key') and g.api_key:
                    APIKeyManager.log_usage(
                        g.api_key.id,
                        request.endpoint or request.path,
                        request.method,
                        500,
                        response_time,
                        request.remote_addr,
                        request.headers.get('User-Agent'),
                        str(e)
                    )
                
                response, status_code = create_error_response(
                    "INTERNAL_ERROR",
                    "An internal error occurred",
                    500
                )
                
                return jsonify(response), status_code
        
        return decorated_function
    return decorator

def require_permissions(permissions: List[str]):
    """
    Decorator to check specific permissions (assumes API key is already validated)
    
    Args:
        permissions: List of required permissions
        
    Returns:
        Decorated function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'api_key') or not g.api_key:
                response, status_code = create_error_response(
                    "AUTHENTICATION_REQUIRED",
                    "API key authentication required",
                    401
                )
                return jsonify(response), status_code
            
            missing_permissions = []
            for permission in permissions:
                if not g.api_key.has_permission(permission):
                    missing_permissions.append(permission)
            
            if missing_permissions:
                response, status_code = create_error_response(
                    "INSUFFICIENT_PERMISSIONS",
                    f"Missing required permissions: {', '.join(missing_permissions)}",
                    403,
                    {"required_permissions": permissions, "missing_permissions": missing_permissions}
                )
                return jsonify(response), status_code
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def get_current_api_key() -> Optional[APIKey]:
    """
    Get the current API key from Flask's g object
    
    Returns:
        APIKey object or None if not authenticated
    """
    return getattr(g, 'api_key', None)

def get_rate_limit_info() -> Dict:
    """
    Get current rate limit information
    
    Returns:
        Dictionary with rate limit info
    """
    return getattr(g, 'rate_limit_info', {})

def create_success_response(data: Any, message: str = None, meta: Dict = None) -> Dict:
    """
    Create a standardized success response
    
    Args:
        data: Response data
        message: Optional success message
        meta: Optional metadata
        
    Returns:
        Response dictionary
    """
    response = {
        "success": True,
        "data": data
    }
    
    if message:
        response["message"] = message
    
    if meta:
        response["meta"] = meta
    
    return response