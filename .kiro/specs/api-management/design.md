# API Management System Design

## Production Environment

**Live Application**: https://inventory.truelog.com.sg/
**API Base URL**: https://inventory.truelog.com.sg/api/v1/
**Admin Panel**: https://inventory.truelog.com.sg/admin/api-management

## Overview

The API Management System will provide comprehensive API access control, documentation, and monitoring capabilities to support iOS app integration. The system will be built as a modular component that integrates with the existing Flask application architecture.

## Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   iOS App       │    │   Web Admin     │    │   API Docs      │
│                 │    │   Interface     │    │   Interface     │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          │ API Requests         │ Management           │ Documentation
          │                      │                      │
          v                      v                      v
┌─────────────────────────────────────────────────────────────────┐
│                    API Gateway Layer                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ Auth        │  │ Rate        │  │ Logging     │            │
│  │ Middleware  │  │ Limiting    │  │ Middleware  │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
          │
          v
┌─────────────────────────────────────────────────────────────────┐
│                    Core Application                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ Ticket      │  │ User        │  │ Inventory   │            │
│  │ Management  │  │ Management  │  │ Management  │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
          │
          v
┌─────────────────────────────────────────────────────────────────┐
│                    Data Layer                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ SQLite      │  │ API Keys    │  │ Usage       │            │
│  │ Database    │  │ Storage     │  │ Analytics   │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

### Component Architecture

The system will consist of several key components:

1. **API Key Management Service**: Handles creation, validation, and lifecycle management of API keys
2. **Authentication Middleware**: Validates API keys and enforces permissions on each request
3. **Documentation Generator**: Automatically generates and serves API documentation
4. **Usage Analytics Service**: Tracks and analyzes API usage patterns
5. **Admin Interface**: Web-based management interface for administrators

## Components and Interfaces

### 1. API Key Management Service

**Location**: `utils/api_key_manager.py`

**Key Classes**:
- `APIKeyManager`: Main service class for key operations
- `APIKey`: Data model for API keys
- `Permission`: Data model for permission management

**Key Methods**:
```python
class APIKeyManager:
    def generate_key(self, name: str, permissions: List[str], expires_at: datetime = None) -> APIKey
    def validate_key(self, key: str) -> Tuple[bool, APIKey]
    def revoke_key(self, key_id: int) -> bool
    def list_keys(self) -> List[APIKey]
    def update_permissions(self, key_id: int, permissions: List[str]) -> bool
```

### 2. Authentication Middleware

**Location**: `utils/api_auth.py`

**Key Functions**:
```python
def require_api_key(permissions: List[str] = None):
    """Decorator for protecting API endpoints"""
    
def validate_api_request(request) -> Tuple[bool, str, APIKey]:
    """Validates incoming API requests"""
    
def check_rate_limit(api_key: APIKey) -> bool:
    """Enforces rate limiting per API key"""
```

### 3. API Routes

**Location**: `routes/api.py`

**Endpoint Structure**:
```
https://inventory.truelog.com.sg/api/v1/
├── auth/
│   ├── POST /login          # User authentication
│   └── POST /refresh        # Token refresh
├── tickets/
│   ├── GET /tickets         # List tickets
│   ├── POST /tickets        # Create ticket
│   ├── GET /tickets/{id}    # Get ticket details
│   ├── PUT /tickets/{id}    # Update ticket
│   └── DELETE /tickets/{id} # Delete ticket
├── users/
│   ├── GET /users           # List users
│   └── GET /users/{id}      # Get user details
├── inventory/
│   ├── GET /inventory       # List inventory items
│   └── GET /inventory/{id}  # Get item details
└── sync/
    ├── GET /sync/tickets    # Incremental ticket sync
    └── POST /sync/conflicts # Resolve sync conflicts
```

### 4. Admin Interface

**Location**: `routes/admin.py` (extended), `templates/admin/api_management.html`

**Admin Pages**:
- API Key Management Dashboard
- Usage Analytics Dashboard
- API Documentation Viewer
- Permission Configuration

### 5. Documentation System

**Location**: `utils/api_docs.py`, `templates/api/docs.html`

**Features**:
- Auto-generated OpenAPI/Swagger documentation
- Interactive API testing interface
- Code examples for iOS integration
- Authentication guides

## Data Models

### APIKey Model

**Location**: `models/api_key.py`

```python
class APIKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    key_hash = db.Column(db.String(255), nullable=False, unique=True)
    permissions = db.Column(db.Text)  # JSON string of permissions
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    last_used_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Usage tracking
    request_count = db.Column(db.Integer, default=0)
    last_request_ip = db.Column(db.String(45))
```

### APIUsage Model

**Location**: `models/api_usage.py`

```python
class APIUsage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    api_key_id = db.Column(db.Integer, db.ForeignKey('api_key.id'))
    endpoint = db.Column(db.String(255), nullable=False)
    method = db.Column(db.String(10), nullable=False)
    status_code = db.Column(db.Integer, nullable=False)
    response_time_ms = db.Column(db.Integer)
    request_ip = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    error_message = db.Column(db.Text)
```

### Permission System

**Predefined Permission Groups**:
```python
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
    ]
}
```

## Error Handling

### API Error Responses

**Standard Error Format**:
```json
{
    "error": {
        "code": "INVALID_API_KEY",
        "message": "The provided API key is invalid or expired",
        "details": {
            "timestamp": "2024-01-15T10:30:00Z",
            "request_id": "req_123456789"
        }
    }
}
```

**Error Codes**:
- `INVALID_API_KEY`: API key is invalid, expired, or revoked
- `INSUFFICIENT_PERMISSIONS`: API key lacks required permissions
- `RATE_LIMIT_EXCEEDED`: Too many requests from this API key
- `VALIDATION_ERROR`: Request data validation failed
- `RESOURCE_NOT_FOUND`: Requested resource doesn't exist
- `INTERNAL_ERROR`: Server-side error occurred

### Error Handling Strategy

1. **Authentication Errors**: Return 401 with clear error message
2. **Authorization Errors**: Return 403 with permission details
3. **Validation Errors**: Return 400 with field-specific error details
4. **Rate Limiting**: Return 429 with retry-after header
5. **Server Errors**: Return 500 with generic message, log details

## Testing Strategy

### Unit Tests

**Test Coverage Areas**:
- API key generation and validation
- Permission checking logic
- Rate limiting functionality
- Usage tracking accuracy
- Error handling scenarios

**Test Files**:
- `tests/test_api_key_manager.py`
- `tests/test_api_auth.py`
- `tests/test_api_routes.py`
- `tests/test_api_permissions.py`

### Integration Tests

**Test Scenarios**:
- End-to-end API request flow
- Admin interface functionality
- Documentation generation
- Analytics data collection
- Mobile app simulation tests

### Performance Tests

**Load Testing**:
- API endpoint response times under load
- Rate limiting effectiveness
- Database performance with usage logging
- Memory usage with concurrent requests

## Security Considerations

### API Key Security

1. **Key Generation**: Use cryptographically secure random generation
2. **Key Storage**: Store only hashed versions in database
3. **Key Transmission**: Always use HTTPS for key exchange
4. **Key Rotation**: Support key rotation without service interruption

### Request Security

1. **Input Validation**: Validate all input parameters and request bodies
2. **Output Sanitization**: Sanitize all response data
3. **SQL Injection Prevention**: Use parameterized queries
4. **XSS Prevention**: Escape output in documentation interface

### Monitoring and Alerting

1. **Suspicious Activity Detection**: Monitor for unusual usage patterns
2. **Failed Authentication Tracking**: Log and alert on repeated failures
3. **Rate Limit Violations**: Track and investigate limit violations
4. **Data Access Auditing**: Log all data access for compliance

## Performance Optimization

### Caching Strategy

1. **API Key Validation**: Cache valid keys in memory for faster lookup
2. **Permission Checks**: Cache permission matrices
3. **Documentation**: Cache generated documentation
4. **Usage Analytics**: Use background processing for analytics updates

### Database Optimization

1. **Indexing**: Create indexes on frequently queried fields
2. **Partitioning**: Partition usage logs by date for better performance
3. **Archiving**: Archive old usage data to maintain performance
4. **Connection Pooling**: Use connection pooling for database access

### Response Optimization

1. **Pagination**: Implement pagination for large result sets
2. **Field Selection**: Allow clients to specify required fields
3. **Compression**: Enable gzip compression for responses
4. **CDN Integration**: Use CDN for static documentation assets

## Deployment Considerations

### Environment Configuration

**Environment Variables**:
```
API_KEY_ENCRYPTION_SECRET=<secret_key>
API_RATE_LIMIT_DEFAULT=1000
API_RATE_LIMIT_WINDOW=3600
API_DOCS_ENABLED=true
API_ANALYTICS_RETENTION_DAYS=90
```

### Database Migration

**Migration Scripts**:
- Create API key tables
- Create usage tracking tables
- Add indexes for performance
- Set up initial admin API key

### Monitoring Setup

**Metrics to Track**:
- API request volume and response times
- Error rates by endpoint
- API key usage patterns
- System resource utilization

**Alerting Rules**:
- High error rates (>5% in 5 minutes)
- Unusual traffic patterns
- API key security violations
- System performance degradation