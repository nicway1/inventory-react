# TrueLog API v1 Documentation

Comprehensive documentation for all API v1 endpoints in the TrueLog inventory management system.

**Base URL:** `/api/v1`

**API Version:** 1.0.0

---

## Table of Contents

1. [Authentication](#authentication)
2. [Health Check](#health-check)
3. [Tickets](#tickets)
4. [Comments](#comments)
5. [Users](#users)
6. [Inventory (Assets)](#inventory-assets)
7. [Accessories](#accessories)
8. [Search API](#search-api)
9. [Audit](#audit)
10. [Companies](#companies)
11. [Queues](#queues)
12. [Asset Management](#asset-management)

---

## Authentication

The API supports multiple authentication methods:

1. **JWT Bearer Token** - Primary authentication method
2. **API Key + JWT** - For mobile/iOS app integration (X-API-Key header + Bearer token)

### POST /api/v1/auth/login

Authenticate user and receive JWT token for API access.

**Authentication Required:** No

**Request Body:**
```json
{
  "username": "string",  // or "email"
  "password": "string"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "user_type": "ADMIN",
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_at": "2025-08-12T10:00:00"
  },
  "message": "Login successful"
}
```

**Error Responses:**
- `400` - Validation error (missing fields)
- `401` - Invalid credentials
- `500` - Internal server error

---

### GET /api/v1/auth/verify

Verify JWT token validity and get user information.

**Authentication Required:** Yes (Bearer Token)

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user_id": 1,
    "username": "john_doe",
    "user_type": "ADMIN",
    "expires_at": "2025-08-12T10:00:00",
    "valid": true
  },
  "message": "Token is valid"
}
```

**Error Responses:**
- `401` - Missing token, expired token, or invalid token

---

### POST /api/v1/auth/refresh

Refresh an existing JWT token to extend its validity.

**Authentication Required:** Yes (Bearer Token)

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_at": "2025-08-13T10:00:00",
    "user_id": 1,
    "username": "john_doe"
  },
  "message": "Token refreshed successfully"
}
```

**Notes:**
- Tokens can be refreshed within 7 days of expiration
- Returns a new token with extended validity (24 hours)

**Error Responses:**
- `401` - Missing token, token too old, or invalid token

---

### GET /api/v1/auth/permissions

Get current user's permissions and capabilities.

**Authentication Required:** Yes (Bearer Token)

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user_id": 1,
    "username": "john_doe",
    "user_type": "ADMIN",
    "permissions": [
      "tickets:read",
      "tickets:write",
      "users:read",
      "inventory:read",
      "inventory:write"
    ],
    "capabilities": {
      "can_create_tickets": true,
      "can_edit_tickets": true,
      "can_delete_tickets": true,
      "can_view_all_tickets": true,
      "can_manage_users": true,
      "can_manage_inventory": true,
      "can_access_admin": true,
      "can_view_reports": true,
      "can_manage_settings": true,
      "can_assign_tickets": true,
      "can_close_tickets": true
    },
    "company_id": 5,
    "assigned_country": "Singapore"
  },
  "message": "User permissions retrieved successfully"
}
```

---

### GET /api/v1/auth/profile

Get current user's detailed profile information.

**Authentication Required:** Yes (Bearer Token)

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "user_type": "ADMIN",
    "company_id": 5,
    "company_name": "Acme Corp",
    "assigned_country": "Singapore",
    "role": "Administrator",
    "theme_preference": "light",
    "created_at": "2025-01-15T08:00:00",
    "last_login": "2025-08-11T14:30:00"
  },
  "message": "User profile retrieved successfully"
}
```

---

## Health Check

### GET /api/v1/health

API health check endpoint (no authentication required).

**Authentication Required:** No

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-11T10:00:00",
  "version": "1.0.0"
}
```

---

## Tickets

### GET /api/v1/tickets

List tickets with filtering and pagination.

**Authentication Required:** Yes (API Key with `tickets:read` permission)

**Headers:**
```
X-API-Key: <api_key>
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | integer | 1 | Page number |
| per_page | integer | 50 | Items per page (max: 100) |
| queue_id | integer | - | Filter by queue ID |
| status | string | - | Filter by status |
| priority | string | - | Filter by priority |
| customer_id | integer | - | Filter by customer ID |
| created_after | string | - | Filter by creation date (ISO format) |
| updated_after | string | - | Filter by update date (ISO format) |

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "subject": "Laptop Repair Request",
      "description": "Screen is cracked",
      "status": "OPEN",
      "priority": "HIGH",
      "category": "ASSET_REPAIR",
      "queue_id": 1,
      "queue_name": "Support Queue",
      "customer_id": 10,
      "customer_name": "Jane Smith",
      "customer_email": "jane@example.com",
      "assigned_to_id": 5,
      "assigned_to_name": "John Tech",
      "created_at": "2025-08-10T09:00:00",
      "updated_at": "2025-08-11T14:00:00"
    }
  ],
  "message": "Retrieved 1 tickets",
  "meta": {
    "pagination": {
      "page": 1,
      "per_page": 50,
      "total": 1,
      "has_next": false,
      "has_prev": false
    }
  }
}
```

---

### GET /api/v1/tickets/{id}

Get detailed information about a specific ticket.

**Authentication Required:** Yes (API Key with `tickets:read` permission)

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| id | integer | Ticket ID |

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "subject": "Laptop Repair Request",
    "description": "Screen is cracked",
    "status": "OPEN",
    "priority": "HIGH",
    "category": "ASSET_REPAIR",
    "queue_id": 1,
    "queue_name": "Support Queue",
    "customer_id": 10,
    "customer_name": "Jane Smith",
    "customer_email": "jane@example.com",
    "customer_phone": "+1234567890",
    "assigned_to_id": 5,
    "assigned_to_name": "John Tech",
    "created_at": "2025-08-10T09:00:00",
    "updated_at": "2025-08-11T14:00:00"
  },
  "message": "Retrieved ticket 1"
}
```

**Error Responses:**
- `404` - Ticket not found

---

### POST /api/v1/tickets

Create a new ticket.

**Authentication Required:** Yes (API Key with `tickets:write` permission)

**Request Body:**
```json
{
  "subject": "string (required)",
  "description": "string (required)",
  "queue_id": "integer (required)",
  "customer_id": "integer (optional)",
  "priority_id": "integer (optional)",
  "category_id": "integer (optional)",
  "assigned_to_id": "integer (optional)",
  "shipping_address": "string (optional)"
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "id": 123,
    "subject": "New Support Request",
    "description": "Description of the issue",
    "status": "NEW",
    "queue_id": 1,
    "customer_id": 10,
    "created_at": "2025-08-11T10:00:00"
  },
  "message": "Ticket created successfully"
}
```

---

### PUT /api/v1/tickets/{id}

Update an existing ticket.

**Authentication Required:** Yes (API Key with `tickets:write` permission)

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| id | integer | Ticket ID |

**Request Body:**
```json
{
  "subject": "string (optional)",
  "description": "string (optional)",
  "status": "string (optional)",
  "priority_id": "integer (optional)",
  "category_id": "integer (optional)",
  "assigned_to_id": "integer (optional)",
  "shipping_address": "string (optional)",
  "shipping_tracking": "string (optional)",
  "shipping_carrier": "string (optional)",
  "shipping_status": "string (optional)",
  "return_tracking": "string (optional)",
  "return_status": "string (optional)"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 123,
    "subject": "Updated Subject",
    "description": "Updated description",
    "status": "IN_PROGRESS",
    "updated_at": "2025-08-11T15:00:00"
  },
  "message": "Ticket updated successfully. Updated fields: subject, status"
}
```

---

### GET /api/v1/tickets/categories

Get available ticket categories for mobile app.

**Authentication Required:** No

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "ASSET_REPAIR",
      "name": "Asset Repair",
      "description": "Report device damage and request repair",
      "requires_asset": true,
      "required_fields": ["serial_number", "damage_description", "queue_id"],
      "optional_fields": ["apple_diagnostics", "country", "notes", "priority"]
    },
    {
      "id": "ASSET_CHECKOUT_CLAW",
      "name": "Asset Checkout (claw)",
      "description": "Deploy device to customer",
      "requires_asset": true,
      "required_fields": ["serial_number", "customer_id", "shipping_address", "queue_id"],
      "optional_fields": ["shipping_tracking", "notes", "priority"]
    },
    {
      "id": "ASSET_RETURN_CLAW",
      "name": "Asset Return (claw)",
      "description": "Process device return from customer",
      "requires_asset": false,
      "required_fields": ["customer_id", "return_address", "queue_id"],
      "optional_fields": ["outbound_tracking", "inbound_tracking", "damage_description", "return_description", "notes", "priority"]
    },
    {
      "id": "ASSET_INTAKE",
      "name": "Asset Intake",
      "description": "Receive new assets into inventory",
      "requires_asset": false,
      "required_fields": ["title", "description", "queue_id"],
      "optional_fields": ["notes", "priority"]
    },
    {
      "id": "INTERNAL_TRANSFER",
      "name": "Internal Transfer",
      "description": "Transfer device between customers/locations",
      "requires_asset": false,
      "required_fields": ["offboarding_customer_id", "offboarding_details", "offboarding_address", "onboarding_customer_id", "onboarding_address", "queue_id"],
      "optional_fields": ["transfer_tracking", "notes", "priority"]
    },
    {
      "id": "BULK_DELIVERY_QUOTATION",
      "name": "Bulk Delivery Quote",
      "description": "Request quote for bulk device delivery",
      "requires_asset": false,
      "required_fields": ["subject", "description", "queue_id"],
      "optional_fields": ["notes", "priority"]
    },
    {
      "id": "REPAIR_QUOTE",
      "name": "Repair Quote",
      "description": "Request quote for device repair",
      "requires_asset": false,
      "required_fields": ["subject", "description", "queue_id"],
      "optional_fields": ["serial_number", "notes", "priority"]
    },
    {
      "id": "ITAD_QUOTE",
      "name": "ITAD Quote",
      "description": "IT Asset Disposal quotation",
      "requires_asset": false,
      "required_fields": ["subject", "description", "queue_id"],
      "optional_fields": ["notes", "priority"]
    }
  ],
  "message": "Retrieved ticket categories"
}
```

---

### POST /api/v1/tickets/create

Create a new ticket from mobile app with category-specific validation.

**Authentication Required:** Yes (Bearer Token or API Key + Bearer Token)

**Request Body (varies by category):**

For **ASSET_REPAIR**:
```json
{
  "category": "ASSET_REPAIR",
  "serial_number": "string (required)",
  "damage_description": "string (required)",
  "queue_id": "integer (required)",
  "apple_diagnostics": "string (optional)",
  "country": "string (optional)",
  "priority": "string (optional, default: Medium)",
  "notes": "string (optional)"
}
```

For **ASSET_CHECKOUT_CLAW**:
```json
{
  "category": "ASSET_CHECKOUT_CLAW",
  "serial_number": "string (required)",
  "customer_id": "integer (required)",
  "shipping_address": "string (required)",
  "queue_id": "integer (required)",
  "shipping_tracking": "string (optional)",
  "priority": "string (optional)",
  "notes": "string (optional)"
}
```

For **ASSET_RETURN_CLAW**:
```json
{
  "category": "ASSET_RETURN_CLAW",
  "customer_id": "integer (required)",
  "return_address": "string (required)",
  "queue_id": "integer (required)",
  "outbound_tracking": "string (optional)",
  "inbound_tracking": "string (optional)",
  "damage_description": "string (optional)",
  "return_description": "string (optional)",
  "priority": "string (optional)",
  "notes": "string (optional)"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Ticket created successfully",
  "data": {
    "ticket_id": 123,
    "display_id": "TKT-000123",
    "subject": "Asset Repair - MacBook Pro (C02X123ABCD)",
    "status": "open"
  }
}
```

---

## Comments

### GET /api/v1/tickets/{ticket_id}/comments

Get all comments for a specific ticket.

**Authentication Required:** Yes (API Key with `tickets:read` permission)

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| ticket_id | integer | Ticket ID |

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | integer | 1 | Page number |
| limit | integer | 20 | Comments per page (max: 100) |

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "ticket_id": 123,
      "content": "Working on this issue",
      "author_name": "john_doe",
      "author_id": 5,
      "created_at": "2025-08-11T10:00:00Z",
      "updated_at": "2025-08-11T10:00:00Z"
    }
  ],
  "meta": {
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total": 1,
      "has_next": false,
      "has_prev": false
    }
  },
  "message": "Comments retrieved successfully"
}
```

---

### POST /api/v1/tickets/{ticket_id}/comments

Create a new comment on a specific ticket.

**Authentication Required:** Yes (API Key with `tickets:write` permission)

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| ticket_id | integer | Ticket ID |

**Request Body:**
```json
{
  "content": "string (required)",
  "user_id": "integer (required)"
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "id": 5,
    "ticket_id": 123,
    "content": "Issue has been resolved",
    "author_name": "john_doe",
    "author_id": 5,
    "created_at": "2025-08-11T15:00:00Z",
    "updated_at": "2025-08-11T15:00:00Z"
  },
  "message": "Comment created successfully"
}
```

---

## Users

### GET /api/v1/users

List users with pagination.

**Authentication Required:** Yes (API Key with `users:read` permission)

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | integer | 1 | Page number |
| per_page | integer | 50 | Users per page (max: 100) |

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "john_doe",
      "email": "john@example.com",
      "user_type": "ADMIN",
      "created_at": "2025-01-15T08:00:00"
    }
  ],
  "message": "Retrieved 1 users",
  "meta": {
    "pagination": {
      "page": 1,
      "per_page": 50,
      "total": 1,
      "has_next": false,
      "has_prev": false
    }
  }
}
```

---

### GET /api/v1/users/{id}

Get detailed information about a specific user.

**Authentication Required:** Yes (API Key with `users:read` permission)

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| id | integer | User ID |

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "john_doe",
    "email": "john@example.com",
    "user_type": "ADMIN",
    "is_active": true,
    "created_at": "2025-01-15T08:00:00",
    "last_login": "2025-08-11T14:30:00"
  },
  "message": "Retrieved user 1"
}
```

---

## Inventory (Assets)

### GET /api/v1/inventory

List inventory items with pagination and filtering.

**Authentication Required:** Yes (API Key with `inventory:read` permission OR Dual Auth)

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | integer | 1 | Page number |
| per_page / limit | integer | 50/20 | Items per page (max: 100) |
| search | string | - | Search term |
| status | string | - | Filter by status (available, in_stock, deployed, shipped, repair, archived, disposed) |
| category | string | - | Filter by asset type/category |

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 123,
      "name": "MacBook Pro",
      "asset_tag": "SG-001",
      "serial_number": "C02X123ABCD",
      "model": "A3401",
      "manufacturer": "Apple",
      "status": "available",
      "location_id": 1,
      "image_url": "https://example.com/static/images/products/macbook.png",
      "created_at": "2025-08-11T09:00:00"
    }
  ],
  "message": "Retrieved 1 inventory items",
  "meta": {
    "pagination": {
      "page": 1,
      "per_page": 50,
      "total": 1,
      "has_next": false,
      "has_prev": false
    }
  }
}
```

---

### GET /api/v1/inventory/{id}

Get detailed information about a specific inventory item (asset).

**Authentication Required:** Yes (API Key with `inventory:read` permission OR Dual Auth)

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| id | integer | Asset ID |

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 123,
    "asset_tag": "SG-001",
    "serial_number": "C02X123ABCD",
    "name": "MacBook Pro",
    "model": "A3401",
    "manufacturer": "Apple",
    "category": "APPLE",
    "status": "available",
    "cpu_type": "M3 Pro",
    "cpu_cores": "11",
    "gpu_cores": "14",
    "memory": "36.0 GB",
    "storage": "512.0 GB",
    "asset_type": "Laptop",
    "hardware_type": "MacBook Pro 14\" Apple",
    "condition": "NEW",
    "is_erased": true,
    "has_keyboard": true,
    "has_charger": true,
    "diagnostics_code": "ADP000",
    "current_customer": "Jane Smith",
    "customer": "Acme Corp",
    "country": "Singapore",
    "asset_company": "TrueLog",
    "company_id": 1,
    "location_id": 5,
    "location_name": "Singapore Office",
    "image_url": "https://example.com/static/images/products/macbook.png",
    "description": null,
    "cost_price": 2500.00,
    "notes": null,
    "tech_notes": null,
    "specifications": {},
    "po": "PO-2025-001",
    "receiving_date": "2025-07-15T00:00:00",
    "created_at": "2025-08-11T09:00:00",
    "updated_at": "2025-08-11T09:00:00"
  },
  "message": "Retrieved inventory item 123"
}
```

---

### GET /api/v1/inventory/health

Health check for inventory API.

**Authentication Required:** No

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-12T10:00:00Z",
  "version": "v1",
  "endpoints": [
    "/api/v1/inventory",
    "/api/v1/inventory/{id}",
    "/api/v1/accessories",
    "/api/v1/accessories/{id}"
  ]
}
```

---

## Accessories

### GET /api/v1/accessories

List accessories with pagination and filtering.

**Authentication Required:** Yes (Dual Auth - Mobile JWT or API Key + JWT)

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | integer | 1 | Page number |
| per_page / limit | integer | 50/20 | Items per page (max: 100) |
| search | string | - | Search term |
| category | string | - | Filter by category |
| status | string | - | Filter by status (available, checked_out, unavailable, maintenance, retired) |

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 45,
      "name": "Wireless Mouse",
      "category": "Computer Accessories",
      "manufacturer": "Logitech",
      "model": "MX Master 3",
      "total_quantity": 50,
      "available_quantity": 35,
      "status": "available",
      "country": "Singapore",
      "image_url": "https://example.com/static/images/products/accessories/mouse.png",
      "created_at": "2025-08-11T09:00:00"
    }
  ],
  "message": "Retrieved 1 accessories",
  "meta": {
    "pagination": {
      "page": 1,
      "per_page": 50,
      "total": 1,
      "has_next": false,
      "has_prev": false
    }
  }
}
```

---

### GET /api/v1/accessories/{id}

Get detailed information about a specific accessory.

**Authentication Required:** Yes (Dual Auth)

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| id | integer | Accessory ID |

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 45,
    "name": "Wireless Mouse",
    "category": "Computer Accessories",
    "manufacturer": "Logitech",
    "model": "MX Master 3",
    "total_quantity": 50,
    "available_quantity": 35,
    "checked_out_quantity": 15,
    "status": "available",
    "country": "Singapore",
    "current_customer": null,
    "customer_email": null,
    "is_available": true,
    "checkout_date": null,
    "return_date": null,
    "description": "Wireless ergonomic mouse",
    "notes": "Premium ergonomic mouse",
    "company": "TrueLog",
    "company_id": 1,
    "image_url": "https://example.com/static/images/products/accessories/mouse.png",
    "created_at": "2025-08-11T09:00:00",
    "updated_at": "2025-08-11T09:00:00",
    "item_type": "accessory"
  },
  "message": "Retrieved accessory 45"
}
```

---

## Search API

All search endpoints use the `/api/v1/search` prefix and require Dual Authentication.

### GET /api/v1/search/global

Global search across all entities (assets, accessories, customers, tickets).

**Authentication Required:** Yes (Dual Auth)

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| q | string | (required) | Search term |
| page | integer | 1 | Page number |
| limit | integer | 20 | Results per page (max: 100) |
| types | string | all | Comma-separated list: assets,accessories,customers,tickets |
| include_related | boolean | true | Include related tickets for found assets |

**Response:**
```json
{
  "data": {
    "assets": [...],
    "accessories": [...],
    "customers": [...],
    "tickets": [...],
    "related_tickets": [...]
  },
  "query": "macbook",
  "counts": {
    "assets": 5,
    "accessories": 0,
    "customers": 2,
    "tickets": 8,
    "related_tickets": 1,
    "total": 16
  },
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 16,
    "pages": 1
  },
  "search_types": ["assets", "accessories", "customers", "tickets"]
}
```

---

### GET /api/v1/search/assets

Advanced asset search with filtering.

**Authentication Required:** Yes (Dual Auth)

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| q | string | (required) | Search term |
| status | string | - | Asset status filter |
| category | string | - | Asset type/category filter |
| country | string | - | Country filter |
| manufacturer | string | - | Manufacturer filter |
| condition | string | - | Condition filter |
| assigned | boolean | - | Filter by assignment status |
| page | integer | 1 | Page number |
| limit | integer | 20 | Results per page (max: 100) |
| sort | string | created_at | Sort field (name, created_at, updated_at, receiving_date, asset_tag, serial_num) |
| order | string | desc | Sort order (asc, desc) |

**Response:**
```json
{
  "data": [...],
  "query": "macbook",
  "filters": {
    "status": "available",
    "category": null,
    "country": "Singapore",
    "manufacturer": null,
    "condition": null,
    "assigned": null
  },
  "sorting": {
    "field": "created_at",
    "order": "desc"
  },
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 5,
    "pages": 1
  }
}
```

---

### GET /api/v1/search/accessories

Advanced accessory search with filtering.

**Authentication Required:** Yes (Dual Auth)

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| q | string | (required) | Search term |
| status | string | - | Status filter |
| category | string | - | Category filter |
| country | string | - | Country filter |
| manufacturer | string | - | Manufacturer filter |
| available_only | boolean | false | Only show available items |
| page | integer | 1 | Page number |
| limit | integer | 20 | Results per page (max: 100) |
| sort | string | created_at | Sort field |
| order | string | desc | Sort order |

**Response:**
```json
{
  "data": [...],
  "query": "mouse",
  "filters": {
    "status": null,
    "category": null,
    "country": null,
    "manufacturer": "Logitech",
    "available_only": true
  },
  "sorting": {
    "field": "created_at",
    "order": "desc"
  },
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 3,
    "pages": 1
  }
}
```

---

### GET /api/v1/search/suggestions

Get search suggestions/autocomplete.

**Authentication Required:** Yes (Dual Auth)

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| q | string | (required) | Partial search term (min 2 characters) |
| type | string | assets | Entity type: assets, accessories, customers, tickets |
| limit | integer | 10 | Number of suggestions (max: 20) |

**Response:**
```json
{
  "suggestions": [
    {"text": "MacBook Pro", "type": "asset_name"},
    {"text": "MacBook Air", "type": "asset_name"},
    {"text": "Apple", "type": "asset_manufacturer"}
  ]
}
```

---

### GET /api/v1/search/filters

Get available filter options for search.

**Authentication Required:** Yes (Dual Auth)

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| type | string | assets | Entity type: assets, accessories |

**Response:**
```json
{
  "assets": {
    "statuses": ["ARCHIVED", "DEPLOYED", "DISPOSED", "IN_STOCK", "READY_TO_DEPLOY", "REPAIR", "SHIPPED"],
    "categories": ["Desktop", "Laptop", "Phone", "Tablet"],
    "manufacturers": ["Apple", "Dell", "HP", "Lenovo"],
    "countries": ["Malaysia", "Singapore"],
    "conditions": ["FAIR", "GOOD", "NEW", "POOR"]
  }
}
```

---

### GET /api/v1/search/health

Health check for search API.

**Authentication Required:** No

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-12T10:00:00Z",
  "version": "v1",
  "endpoints": [
    "/api/v1/search/global",
    "/api/v1/search/assets",
    "/api/v1/search/accessories",
    "/api/v1/search/suggestions",
    "/api/v1/search/filters"
  ]
}
```

---

## Audit

Inventory audit endpoints for physical asset verification.

### GET /api/v1/audit/status

Get current audit session status.

**Authentication Required:** Yes (Bearer Token with audit permissions)

**Response (Active Audit):**
```json
{
  "success": true,
  "data": {
    "current_audit": {
      "id": "audit_1691750400",
      "country": "Singapore",
      "total_assets": 150,
      "scanned_count": 75,
      "missing_count": 5,
      "unexpected_count": 2,
      "completion_percentage": 50.0,
      "started_at": "2025-08-11T08:00:00Z",
      "started_by": 1,
      "is_active": true
    }
  },
  "message": "Active audit session retrieved"
}
```

**Response (No Active Audit):**
```json
{
  "success": true,
  "data": {
    "current_audit": null
  },
  "message": "No active audit session"
}
```

---

### GET /api/v1/audit/countries

Get available countries for audit.

**Authentication Required:** Yes (Bearer Token with audit permissions)

**Response:**
```json
{
  "success": true,
  "data": {
    "countries": ["Singapore", "Malaysia", "Indonesia"]
  },
  "message": "Available countries retrieved"
}
```

---

### POST /api/v1/audit/start

Start a new audit session.

**Authentication Required:** Yes (Bearer Token with `can_start_inventory_audit` permission)

**Request Body:**
```json
{
  "country": "Singapore"
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "audit": {
      "id": "audit_1691750400",
      "country": "Singapore",
      "total_assets": 150,
      "scanned_count": 0,
      "missing_count": 0,
      "unexpected_count": 0,
      "completion_percentage": 0,
      "started_at": "2025-08-11T08:00:00Z",
      "started_by": 1,
      "is_active": true
    }
  },
  "message": "Audit started successfully for Singapore"
}
```

**Error Responses:**
- `400` - Missing country, no assets found, or audit already active
- `403` - Insufficient permissions or invalid country access

---

### POST /api/v1/audit/scan

Scan an asset during audit.

**Authentication Required:** Yes (Bearer Token with audit permissions)

**Request Body:**
```json
{
  "identifier": "SG-001"  // Asset tag or serial number
}
```

**Response (Found Expected):**
```json
{
  "success": true,
  "data": {
    "status": "found_expected",
    "message": "Asset SG-001 scanned successfully",
    "asset": {
      "id": 123,
      "asset_tag": "SG-001",
      "serial_num": "C02X123ABCD",
      "name": "MacBook Pro",
      "model": "A3401",
      "status": "available",
      "location": "Singapore Office",
      "company": "TrueLog"
    },
    "progress": {
      "total_assets": 150,
      "scanned_count": 76,
      "unexpected_count": 2,
      "completion_percentage": 50.67
    }
  },
  "message": "Asset scan processed"
}
```

**Response (Unexpected Asset):**
```json
{
  "success": true,
  "data": {
    "status": "unexpected",
    "message": "Asset UNKNOWN-001 not found in expected inventory (recorded as unexpected)",
    "asset": {
      "identifier": "UNKNOWN-001",
      "scanned_at": "2025-08-11T10:30:00",
      "type": "unexpected"
    },
    "progress": {...}
  },
  "message": "Asset scan processed"
}
```

---

### POST /api/v1/audit/end

End the current audit session.

**Authentication Required:** Yes (Bearer Token with audit permissions)

**Response:**
```json
{
  "success": true,
  "data": {
    "final_report": {
      "audit_id": "audit_1691750400",
      "country": "Singapore",
      "started_at": "2025-08-11T08:00:00Z",
      "completed_at": "2025-08-11T16:00:00Z",
      "summary": {
        "total_expected": 150,
        "total_scanned": 145,
        "total_missing": 5,
        "total_unexpected": 2,
        "completion_percentage": 96.67
      }
    }
  },
  "message": "Audit session ended successfully"
}
```

---

### GET /api/v1/audit/details/{detail_type}

Get detailed asset lists from current audit.

**Authentication Required:** Yes (Bearer Token with audit permissions)

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| detail_type | string | One of: total, scanned, missing, unexpected |

**Response:**
```json
{
  "success": true,
  "data": {
    "detail_type": "missing",
    "title": "Missing Assets (5)",
    "count": 5,
    "assets": [
      {
        "id": 200,
        "asset_tag": "SG-200",
        "serial_num": "C02Y456EFGH",
        "name": "MacBook Air",
        "model": "A2941",
        "status": "deployed",
        "location": "Singapore Office",
        "company": "TrueLog"
      }
    ]
  },
  "message": "Retrieved missing asset details"
}
```

---

## Companies

### GET /api/v1/companies

Get all companies with parent/child hierarchy.

**Authentication Required:** No

**Response:**
```json
{
  "success": true,
  "companies": [
    {
      "id": 1,
      "name": "TrueLog",
      "display_name": "TrueLog Pte Ltd",
      "grouped_display_name": "TrueLog Pte Ltd",
      "is_parent_company": true,
      "parent_company_id": null,
      "parent_company_name": null
    },
    {
      "id": 2,
      "name": "TrueLog Singapore",
      "display_name": "TrueLog Singapore",
      "grouped_display_name": "TrueLog > TrueLog Singapore",
      "is_parent_company": false,
      "parent_company_id": 1,
      "parent_company_name": "TrueLog"
    }
  ]
}
```

---

## Queues

### GET /api/v1/queues

Get list of all available queues for filtering and display.

**Authentication Required:** Yes (API Key with `tickets:read` permission)

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "Support Queue",
      "description": "General support requests"
    },
    {
      "id": 2,
      "name": "Repairs Queue",
      "description": "Device repair requests"
    }
  ],
  "message": "Retrieved 2 queues"
}
```

---

## Asset Management

### GET /api/v1/assets/next-tag

Get next available asset tag for a given prefix.

**Authentication Required:** No

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| prefix | string | SG- | Asset tag prefix |

**Response:**
```json
{
  "success": true,
  "data": {
    "prefix": "SG-",
    "next_number": 156,
    "next_tag": "SG-156"
  },
  "message": "Next asset tag: SG-156"
}
```

---

### POST /api/v1/assets/bulk

Bulk create assets from PDF extraction.

**Authentication Required:** No (for internal use)

**Request Body:**
```json
{
  "assets": [
    {
      "serial_number": "C02X123ABCD",
      "asset_tag": "SG-156",
      "name": "MacBook Pro",
      "model_identifier": "A3401",
      "part_number": "MKGR3LL/A",
      "hardware_type": "MacBook Pro 14\"",
      "cpu_type": "M3 Pro",
      "cpu_cores": 11,
      "gpu_cores": 14,
      "memory": "36.0 GB",
      "storage": "512.0 GB",
      "condition": "New",
      "manufacturer": "Apple",
      "category": "APPLE",
      "company_id": 1,
      "country": "Singapore"
    }
  ],
  "ticket_id": 123  // Optional: link assets to ticket
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "created_count": 5,
    "created_ids": [156, 157, 158, 159, 160],
    "failed_count": 1,
    "errors": [
      {
        "serial_number": "C02X999ZZZZ",
        "error": "Duplicate serial number (exists as SG-050)"
      }
    ]
  },
  "message": "Created 5 of 6 assets"
}
```

---

## Error Response Format

All endpoints return errors in a consistent format:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": {}  // Optional additional details
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| VALIDATION_ERROR | 400 | Invalid request data |
| MISSING_TOKEN | 401 | No authentication token provided |
| INVALID_TOKEN | 401 | Token is invalid |
| TOKEN_EXPIRED | 401 | Token has expired |
| INVALID_CREDENTIALS | 401 | Wrong username/password |
| INSUFFICIENT_PERMISSIONS | 403 | User lacks required permissions |
| RESOURCE_NOT_FOUND | 404 | Requested resource not found |
| ENDPOINT_NOT_FOUND | 404 | API endpoint does not exist |
| METHOD_NOT_ALLOWED | 405 | HTTP method not supported |
| INTERNAL_ERROR | 500 | Server error |

---

## Rate Limiting

Currently no rate limiting is enforced on the API.

---

## Pagination

All list endpoints support pagination with the following response format:

```json
{
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 150,
    "pages": 3,
    "has_next": true,
    "has_prev": false,
    "next_page": 2,
    "prev_page": null
  }
}
```

---

## Source Files

This API is implemented across multiple files:

- `/Users/123456/inventory/routes/api_simple.py` - Main API v1 blueprint with authentication, tickets, users, inventory, audit, and mobile endpoints
- `/Users/123456/inventory/routes/inventory_api.py` - Enhanced inventory API with complete asset/accessory information
- `/Users/123456/inventory/routes/search_api.py` - Search API for global and entity-specific searches
- `/Users/123456/inventory/routes/api.py` - Additional API routes (asset management)
