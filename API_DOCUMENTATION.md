# Enhanced Inventory API Documentation

## Overview

The enhanced inventory API provides comprehensive access to both assets and accessories with complete specifications, condition details, and location/assignment information.

## Base URLs
```
/api/v1/inventory    (for assets)
/api/v1/accessories  (for accessories)
```

## Authentication

All inventory API endpoints require authentication using a Bearer token obtained from the mobile authentication endpoint.

### Get Authentication Token
```http
POST /api/mobile/v1/auth/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "success": true,
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": 1,
    "username": "user@example.com",
    "user_type": "SUPERVISOR"
  }
}
```

## Endpoints

### 1. List All Inventory Items

Get a paginated list of all inventory assets with complete information.

```http
GET /api/v1/inventory
Authorization: Bearer <token>
```

**Query Parameters:**
- `page` (integer, optional): Page number (default: 1)
- `limit` (integer, optional): Items per page (default: 20, max: 100)
- `search` (string, optional): Search term for name, serial number, model, etc.
- `status` (string, optional): Filter by status (`available`, `deployed`, `in_stock`, `shipped`, `repair`, `archived`, `disposed`)
- `category` (string, optional): Filter by asset category/type

**Example Request:**
```http
GET /api/v1/inventory?page=1&limit=20&search=macbook&status=available
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

**Response:**
```json
{
  "data": [
    {
      "id": 123,
      "name": "MacBook Pro",
      "serial_number": "GFXWF6W4HW",
      "model": "A3401",
      "asset_tag": "ASSET001",
      "manufacturer": "Apple",
      "status": "available",
      "cpu_type": "M3 Pro",
      "cpu_cores": 11,
      "gpu_cores": 14,
      "memory": "36.0 GB",
      "storage": "512.0 GB",
      "hardware_type": "MacBook Pro 14\" Apple",
      "asset_type": "Laptop",
      "condition": "NEW",
      "is_erased": true,
      "has_keyboard": true,
      "has_charger": true,
      "diagnostics_code": "ADP000",
      "current_customer": null,
      "country": "Singapore",
      "asset_company": "Wise",
      "receiving_date": "2025-08-11T09:04:27.257649",
      "created_at": "2025-08-11T09:04:27.257649",
      "updated_at": "2025-08-11T09:04:27.257649",
      "description": "Apple MacBook Pro with M3 Pro chip",
      "location": "Warehouse A",
      "assigned_to": null,
      "customer_user": null
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 150,
    "pages": 8
  }
}
```

### 2. Get Single Asset

Get complete information for a specific asset by ID.

```http
GET /api/v1/inventory/{id}
Authorization: Bearer <token>
```

**Example Request:**
```http
GET /api/v1/inventory/123
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

**Response:**
```json
{
  "data": {
    "id": 123,
    "name": "MacBook Pro",
    "serial_number": "GFXWF6W4HW",
    "model": "A3401",
    "asset_tag": "ASSET001",
    "manufacturer": "Apple",
    "status": "available",
    "cpu_type": "M3 Pro",
    "cpu_cores": 11,
    "gpu_cores": 14,
    "memory": "36.0 GB",
    "storage": "512.0 GB",
    "hardware_type": "MacBook Pro 14\" Apple",
    "asset_type": "Laptop",
    "condition": "NEW",
    "is_erased": true,
    "has_keyboard": true,
    "has_charger": true,
    "diagnostics_code": "ADP000",
    "current_customer": null,
    "country": "Singapore",
    "asset_company": "Wise",
    "receiving_date": "2025-08-11T09:04:27.257649",
    "created_at": "2025-08-11T09:04:27.257649",
    "updated_at": "2025-08-11T09:04:27.257649",
    "description": "Apple MacBook Pro with M3 Pro chip",
    "location": "Warehouse A",
    "assigned_to": null,
    "customer_user": null
  }
}
```

## Accessory Endpoints

### 3. List All Accessories

Get a paginated list of all inventory accessories with complete information.

```http
GET /api/v1/accessories
Authorization: Bearer <token>
```

**Query Parameters:**
- `page` (integer, optional): Page number (default: 1)
- `limit` (integer, optional): Items per page (default: 20, max: 100)
- `search` (string, optional): Search term for name, category, manufacturer, model
- `status` (string, optional): Filter by status (`available`, `checked_out`, `unavailable`, `maintenance`, `retired`)
- `category` (string, optional): Filter by accessory category

**Example Request:**
```http
GET /api/v1/accessories?page=1&limit=20&search=mouse&status=available
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

**Response:**
```json
{
  "data": [
    {
      "id": 45,
      "name": "Wireless Mouse",
      "category": "Computer Accessories",
      "manufacturer": "Logitech",
      "model": "MX Master 3",
      "status": "available",
      "total_quantity": 50,
      "available_quantity": 35,
      "checked_out_quantity": 15,
      "country": "Singapore",
      "current_customer": null,
      "customer_email": null,
      "is_available": true,
      "checkout_date": null,
      "return_date": null,
      "description": "Wireless ergonomic mouse with USB-C charging",
      "notes": "Wireless ergonomic mouse with USB-C charging",
      "created_at": "2025-08-11T09:04:27.257649",
      "updated_at": "2025-08-12T10:15:33.445522",
      "item_type": "accessory"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 85,
    "pages": 5
  }
}
```

### 4. Get Single Accessory

Get complete information for a specific accessory by ID.

```http
GET /api/v1/accessories/{id}
Authorization: Bearer <token>
```

**Example Request:**
```http
GET /api/v1/accessories/45
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

**Response:**
```json
{
  "data": {
    "id": 45,
    "name": "Wireless Mouse",
    "category": "Computer Accessories",
    "manufacturer": "Logitech",
    "model": "MX Master 3",
    "status": "available",
    "total_quantity": 50,
    "available_quantity": 35,
    "checked_out_quantity": 15,
    "country": "Singapore",
    "current_customer": null,
    "customer_email": null,
    "is_available": true,
    "checkout_date": null,
    "return_date": null,
    "description": "Wireless ergonomic mouse with USB-C charging",
    "notes": "Wireless ergonomic mouse with USB-C charging",
    "created_at": "2025-08-11T09:04:27.257649",
    "updated_at": "2025-08-12T10:15:33.445522",
    "item_type": "accessory"
  }
}
```

### 5. Health Check

Check API status and availability.

```http
GET /api/v1/inventory/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-12T12:00:00.000000Z",
  "version": "v1",
  "endpoints": [
    "/api/v1/inventory",
    "/api/v1/inventory/{id}",
    "/api/v1/accessories",
    "/api/v1/accessories/{id}"
  ]
}
```

## Response Fields

### Asset Response Fields

#### Core Asset Information
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Unique asset identifier |
| `name` | string | Asset name/title |
| `serial_number` | string | Device serial number |
| `model` | string | Asset model number |
| `asset_tag` | string | Internal asset tag |
| `manufacturer` | string | Device manufacturer |
| `status` | string | Current asset status |

### Hardware Specifications
| Field | Type | Description |
|-------|------|-------------|
| `cpu_type` | string | CPU/processor type |
| `cpu_cores` | integer | Number of CPU cores |
| `gpu_cores` | integer | Number of GPU cores |
| `memory` | string | RAM/memory specification |
| `storage` | string | Storage capacity |
| `hardware_type` | string | Detailed hardware description |
| `asset_type` | string | Asset category (Laptop, Desktop, etc.) |

### Condition and Status Details
| Field | Type | Description |
|-------|------|-------------|
| `condition` | string | Physical condition (NEW, USED, etc.) |
| `is_erased` | boolean | Whether data has been wiped |
| `has_keyboard` | boolean | Keyboard included/present |
| `has_charger` | boolean | Charger included/present |
| `diagnostics_code` | string | Diagnostic/testing code |

### Location and Assignment Details
| Field | Type | Description |
|-------|------|-------------|
| `current_customer` | string | Current customer assignment |
| `country` | string | Asset location country |
| `asset_company` | string | Owning/assigned company |
| `receiving_date` | string (ISO 8601) | Date asset was received |

### Additional Information
| Field | Type | Description |
|-------|------|-------------|
| `description` | string | Asset notes/description |
| `location` | string | Physical location |
| `assigned_to` | object | Assigned user information |
| `customer_user` | object | Customer user information |
| `created_at` | string (ISO 8601) | Record creation timestamp |
| `updated_at` | string (ISO 8601) | Last update timestamp |

### Accessory Response Fields

#### Core Accessory Information
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Unique accessory identifier |
| `name` | string | Accessory name/title |
| `category` | string | Accessory category |
| `manufacturer` | string | Device manufacturer |
| `model` | string | Model number/identifier |
| `status` | string | Current accessory status |
| `item_type` | string | Always "accessory" for accessories |

#### Inventory Details
| Field | Type | Description |
|-------|------|-------------|
| `total_quantity` | integer | Total quantity in inventory |
| `available_quantity` | integer | Currently available quantity |
| `checked_out_quantity` | integer | Currently checked out quantity |
| `is_available` | boolean | Whether any units are available |

#### Assignment and Status Details
| Field | Type | Description |
|-------|------|-------------|
| `current_customer` | string | Currently assigned customer name |
| `customer_email` | string | Customer email address |
| `checkout_date` | string (ISO 8601) | Date when checked out |
| `return_date` | string (ISO 8601) | Date when returned |

#### Location Details
| Field | Type | Description |
|-------|------|-------------|
| `country` | string | Accessory location country |

#### Additional Information
| Field | Type | Description |
|-------|------|-------------|
| `description` | string | Accessory notes/description |
| `notes` | string | Additional notes |
| `created_at` | string (ISO 8601) | Record creation timestamp |
| `updated_at` | string (ISO 8601) | Last update timestamp |

## Status Values

### Asset Status Values

| Status | Description |
|--------|-------------|
| `available` | Ready for deployment |
| `in_stock` | In inventory |
| `deployed` | Currently assigned |
| `shipped` | In transit |
| `repair` | Under repair |
| `archived` | Archived/inactive |
| `disposed` | Disposed of |

### Accessory Status Values

| Status | Description |
|--------|-------------|
| `available` | Available for checkout |
| `checked_out` | Currently checked out |
| `unavailable` | Not available |
| `maintenance` | Under maintenance |
| `retired` | Retired from service |

## Error Responses

### Authentication Error (401)
```json
{
  "error": "Invalid or expired token"
}
```

### Permission Error (403)
```json
{
  "error": "No permission to view inventory"
}
```

### Asset Not Found (404)
```json
{
  "error": "Asset not found or access denied"
}
```

### Server Error (500)
```json
{
  "error": "Failed to get inventory"
}
```

## Usage Examples

### Python Example
```python
import requests

# Get authentication token
login_response = requests.post('http://localhost:5000/api/mobile/v1/auth/login', json={
    'username': 'admin@example.com',
    'password': 'password123'
})
token = login_response.json()['token']

# Get inventory with search and filtering
headers = {'Authorization': f'Bearer {token}'}
inventory_response = requests.get(
    'http://localhost:5000/api/v1/inventory?search=macbook&limit=10', 
    headers=headers
)
assets = inventory_response.json()['data']

# Get specific asset
asset_response = requests.get(
    f'http://localhost:5000/api/v1/inventory/{assets[0]["id"]}',
    headers=headers
)
asset_details = asset_response.json()['data']

# Get accessories with filtering
accessories_response = requests.get(
    'http://localhost:5000/api/v1/accessories?search=mouse&status=available&limit=10',
    headers=headers
)
accessories = accessories_response.json()['data']

# Get specific accessory
accessory_response = requests.get(
    f'http://localhost:5000/api/v1/accessories/{accessories[0]["id"]}',
    headers=headers
)
accessory_details = accessory_response.json()['data']
```

### JavaScript Example
```javascript
// Get authentication token
const loginResponse = await fetch('/api/mobile/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'admin@example.com',
    password: 'password123'
  })
});
const { token } = await loginResponse.json();

// Get inventory
const inventoryResponse = await fetch('/api/v1/inventory?page=1&limit=20', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const { data: assets, pagination } = await inventoryResponse.json();

// Get specific asset
const assetResponse = await fetch(`/api/v1/inventory/${assets[0].id}`, {
  headers: { 'Authorization': `Bearer ${token}` }
});
const { data: asset } = await assetResponse.json();

// Get accessories
const accessoriesResponse = await fetch('/api/v1/accessories?page=1&limit=20&status=available', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const { data: accessories } = await accessoriesResponse.json();

// Get specific accessory
const accessoryResponse = await fetch(`/api/v1/accessories/${accessories[0].id}`, {
  headers: { 'Authorization': `Bearer ${token}` }
});
const { data: accessory } = await accessoryResponse.json();
```

## Testing

Use the provided test script to verify API functionality:

```bash
python test_enhanced_inventory_api.py
```

The test script will:
1. Test authentication
2. Verify all endpoints are working
3. Check that all required fields are present
4. Test filtering and search capabilities

## Migration from Existing APIs

If you're migrating from the existing mobile API endpoints:

### Assets
**Old Endpoint (Limited Fields)**
```
GET /api/mobile/v1/inventory
```

**New Endpoint (Complete Fields)**
```
GET /api/v1/inventory
```

### Accessories
**New Endpoints (Complete Fields)**
```
GET /api/v1/accessories        (list all accessories)
GET /api/v1/accessories/{id}   (get single accessory)
```

The new endpoints include comprehensive information:
- **Assets**: All hardware specifications, condition details, and location information
- **Accessories**: Complete inventory tracking with quantities, availability, and assignment details

Both asset and accessory endpoints support the same authentication, filtering, and pagination capabilities.