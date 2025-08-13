# Search API Documentation

## Overview

The Search API provides comprehensive search functionality for your iOS app that exactly matches your web interface capabilities. It supports searching across assets, accessories, customers, and tickets with advanced filtering, sorting, and user permission controls.

## Base URL
```
/api/v1/search
```

## Authentication

The Search API supports dual authentication methods:

### Method 1: JSON API Key + JWT Token
```
Headers:
X-API-Key: xAQhm3__ZH6MvRIPMIBSDRAsIa1w2Slh5uaCtc4NurM
Authorization: Bearer <jwt_token>
```

### Method 2: Mobile JWT Token Only
```
Headers:
Authorization: Bearer <mobile_jwt_token>
```

## Endpoints

### 1. Global Search
**GET** `/api/v1/search/global`

Search across all entities (assets, accessories, customers, tickets) with a single query.

#### Query Parameters
- `q` (required): Search term
- `page` (optional): Page number (default: 1)
- `limit` (optional): Results per page (default: 20, max: 100)
- `types` (optional): Comma-separated entity types to search (default: "assets,accessories,customers,tickets")
- `include_related` (optional): Include related tickets for found assets (default: "true")

#### Example Request
```bash
GET /api/v1/search/global?q=macbook&page=1&limit=10&types=assets,accessories
```

#### Response Format
```json
{
  "data": {
    "assets": [
      {
        "id": 123,
        "name": "MacBook Pro 14\" Apple",
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
        "assigned_to": {
          "id": 5,
          "name": "john.doe",
          "email": "john@company.com",
          "username": "john.doe",
          "user_type": "SUPERVISOR"
        },
        "location_details": {
          "id": 1,
          "name": "Singapore Office",
          "address": "123 Business St",
          "city": "Singapore",
          "country": "Singapore"
        },
        "created_at": "2025-08-11T09:04:27.257649",
        "updated_at": "2025-08-11T09:04:27.257649",
        "item_type": "asset"
      }
    ],
    "accessories": [
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
        "description": "Wireless ergonomic mouse",
        "created_at": "2025-08-11T09:04:27.257649",
        "updated_at": "2025-08-11T09:04:27.257649",
        "item_type": "accessory"
      }
    ],
    "customers": [
      {
        "id": 10,
        "name": "John Smith",
        "email": "john.smith@company.com",
        "contact_number": "+65 9123 4567",
        "address": "123 Main Street, Singapore",
        "company": "TechCorp Pte Ltd",
        "company_id": 5,
        "created_at": "2025-08-11T09:04:27.257649",
        "updated_at": "2025-08-11T09:04:27.257649",
        "item_type": "customer"
      }
    ],
    "tickets": [
      {
        "id": 1001,
        "display_id": "TICK-1001",
        "subject": "MacBook screen repair",
        "description": "Screen has dead pixels",
        "status": "OPEN",
        "priority": "MEDIUM",
        "category": "HARDWARE_ISSUE",
        "serial_number": "GFXWF6W4HW",
        "damage_description": "Dead pixels on screen",
        "requester": {
          "id": 2,
          "name": "jane.doe",
          "email": "jane@company.com"
        },
        "assigned_to": {
          "id": 3,
          "name": "tech.support",
          "email": "tech@company.com"
        },
        "country": "Singapore",
        "created_at": "2025-08-11T09:04:27.257649",
        "updated_at": "2025-08-11T09:04:27.257649",
        "item_type": "ticket"
      }
    ],
    "related_tickets": []
  },
  "query": "macbook",
  "counts": {
    "assets": 1,
    "accessories": 1,
    "customers": 1,
    "tickets": 1,
    "related_tickets": 0,
    "total": 4
  },
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 4,
    "pages": 1
  },
  "search_types": ["assets", "accessories"]
}
```

### 2. Advanced Asset Search
**GET** `/api/v1/search/assets`

Search assets with advanced filtering and sorting options.

#### Query Parameters
- `q` (required): Search term
- `status` (optional): Asset status filter (available, deployed, repair, etc.)
- `category` (optional): Asset type/category filter
- `country` (optional): Country filter
- `manufacturer` (optional): Manufacturer filter
- `condition` (optional): Condition filter (NEW, GOOD, FAIR, etc.)
- `assigned` (optional): Filter by assignment status (true/false)
- `page` (optional): Page number (default: 1)
- `limit` (optional): Results per page (default: 20, max: 100)
- `sort` (optional): Sort field (name, created_at, updated_at, receiving_date)
- `order` (optional): Sort order (asc, desc)

#### Example Request
```bash
GET /api/v1/search/assets?q=laptop&status=available&category=laptop&sort=name&order=asc&limit=10
```

#### Response Format
```json
{
  "data": [
    {
      // Complete asset object with 48+ fields
      "id": 123,
      "name": "MacBook Pro 14\" Apple",
      // ... all asset fields as shown in global search
    }
  ],
  "query": "laptop",
  "filters": {
    "status": "available",
    "category": "laptop",
    "country": null,
    "manufacturer": null,
    "condition": null,
    "assigned": null
  },
  "sorting": {
    "field": "name",
    "order": "asc"
  },
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 25,
    "pages": 3
  }
}
```

### 3. Accessory Search
**GET** `/api/v1/search/accessories`

Search accessories with filtering options.

#### Query Parameters
- `q` (required): Search term
- `status` (optional): Accessory status filter (available, checked_out, maintenance, etc.)
- `category` (optional): Accessory category filter
- `country` (optional): Country filter
- `manufacturer` (optional): Manufacturer filter
- `available_only` (optional): Show only available accessories (true/false)
- `page` (optional): Page number (default: 1)
- `limit` (optional): Results per page (default: 20, max: 100)
- `sort` (optional): Sort field (name, created_at, updated_at, category, manufacturer)
- `order` (optional): Sort order (asc, desc)

#### Example Request
```bash
GET /api/v1/search/accessories?q=mouse&status=available&available_only=true&limit=5
```

### 4. Search Suggestions
**GET** `/api/v1/search/suggestions`

Get autocomplete suggestions for search terms.

#### Query Parameters
- `q` (required): Partial search term (minimum 2 characters)
- `type` (optional): Entity type (assets, accessories, customers, tickets)
- `limit` (optional): Number of suggestions (default: 10, max: 20)

#### Example Request
```bash
GET /api/v1/search/suggestions?q=mac&type=assets&limit=5
```

#### Response Format
```json
{
  "suggestions": [
    {
      "text": "MacBook Pro 14\" Apple",
      "type": "asset_name"
    },
    {
      "text": "MacBook Air 13\" Apple",
      "type": "asset_name"
    },
    {
      "text": "Apple",
      "type": "asset_manufacturer"
    }
  ]
}
```

### 5. Filter Options
**GET** `/api/v1/search/filters`

Get available filter options for search forms.

#### Query Parameters
- `type` (optional): Entity type (assets, accessories)

#### Example Request
```bash
GET /api/v1/search/filters?type=assets
```

#### Response Format
```json
{
  "assets": {
    "statuses": [
      "Archived",
      "Deployed", 
      "Disposed",
      "In Stock",
      "Ready to Deploy",
      "Repair",
      "Shipped"
    ],
    "categories": [
      "Desktop PC",
      "Laptop",
      "Phone",
      "Tablet"
    ],
    "manufacturers": [
      "Apple",
      "Dell",
      "HP",
      "Lenovo"
    ],
    "countries": [
      "Australia",
      "Israel", 
      "Singapore",
      "USA"
    ],
    "conditions": [
      "Good",
      "NEW",
      "USED"
    ]
  }
}
```

### 6. Health Check
**GET** `/api/v1/search/health`

Check API health status.

#### Response Format
```json
{
  "status": "healthy",
  "timestamp": "2025-08-13T11:13:13.046Z",
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

## Asset Search Fields

The search functionality searches across the following asset fields (matching your web version):

- `name` - Asset name
- `model` - Asset model
- `serial_num` - Serial number
- `asset_tag` - Asset tag
- `category` - Asset category
- `customer` - Customer name
- `country` - Country
- `hardware_type` - Hardware type
- `cpu_type` - CPU type
- `manufacturer` - Manufacturer

## Accessory Search Fields

- `name` - Accessory name
- `category` - Accessory category
- `manufacturer` - Manufacturer
- `model_no` - Model number
- `country` - Country
- `notes` - Notes/description

## Customer Search Fields

- `name` - Customer name
- `email` - Email address
- `contact_number` - Contact number
- `address` - Address

## Ticket Search Fields

- `subject` - Ticket subject
- `description` - Ticket description
- `notes` - Ticket notes
- `serial_number` - Associated serial number
- `damage_description` - Damage description
- `return_description` - Return description
- `shipping_tracking` - Shipping tracking numbers
- `return_tracking` - Return tracking numbers
- `shipping_tracking_2` - Additional tracking numbers
- Ticket ID search (supports "TICK-1001", "#1001", or just "1001")

## User Permissions

The search API respects user permissions and applies appropriate filters:

### SUPER_ADMIN
- Can search all assets, accessories, customers, and tickets
- No restrictions applied

### COUNTRY_ADMIN
- Assets and accessories filtered by assigned country
- Tickets filtered by country
- Full access within assigned country

### CLIENT
- Assets filtered by company (own company's assets only)
- Customers filtered by company
- Limited access to company-specific data

### SUPERVISOR
- Standard access with permission checks
- Asset viewing requires `can_view_assets` permission

## Error Handling

### Common Error Responses

#### 400 Bad Request - Missing search term
```json
{
  "error": "Search term is required",
  "message": "Please provide a search term using the \"q\" parameter"
}
```

#### 401 Unauthorized - Missing authentication
```json
{
  "error": "Authentication required",
  "message": "Please provide either: (1) Mobile JWT token in Authorization header, or (2) JSON API key in X-API-Key header plus JWT token in Authorization header"
}
```

#### 403 Forbidden - Insufficient permissions
```json
{
  "error": "Insufficient permissions",
  "message": "User does not have permission to view assets and accessories"
}
```

#### 500 Internal Server Error
```json
{
  "error": "Search failed",
  "message": "Detailed error message"
}
```

## Rate Limiting

- No specific rate limiting implemented
- Pagination limits: Max 100 items per page
- Suggestion limits: Max 20 suggestions per request

## Performance Considerations

1. **Pagination**: Always use pagination for large result sets
2. **Filters**: Apply filters to reduce result size
3. **Field Selection**: All available fields are returned (48+ for assets, 20+ for accessories)
4. **Search Types**: Limit search types in global search when possible
5. **Caching**: No caching implemented - consider implementing client-side caching

## Integration Examples

### iOS Swift Example
```swift
// Global search
let url = "https://your-api.com/api/v1/search/global?q=macbook&limit=10"
var request = URLRequest(url: URL(string: url)!)
request.setValue("Bearer \(jwtToken)", forHTTPHeaderField: "Authorization")

// Asset search with filters
let assetUrl = "https://your-api.com/api/v1/search/assets?q=laptop&status=available&sort=name"
var assetRequest = URLRequest(url: URL(string: assetUrl)!)
assetRequest.setValue("xAQhm3__ZH6MvRIPMIBSDRAsIa1w2Slh5uaCtc4NurM", forHTTPHeaderField: "X-API-Key")
assetRequest.setValue("Bearer \(jwtToken)", forHTTPHeaderField: "Authorization")
```

### cURL Examples
```bash
# Global search
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     "https://your-api.com/api/v1/search/global?q=macbook&limit=5"

# Asset search with JSON API key
curl -H "X-API-Key: xAQhm3__ZH6MvRIPMIBSDRAsIa1w2Slh5uaCtc4NurM" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     "https://your-api.com/api/v1/search/assets?q=laptop&status=available"

# Get suggestions
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     "https://your-api.com/api/v1/search/suggestions?q=mac&type=assets&limit=5"
```

## Complete Feature Set

✅ **Global Search**: Search across assets, accessories, customers, tickets  
✅ **Advanced Filtering**: Status, category, manufacturer, country filters  
✅ **Sorting & Pagination**: Flexible sorting with pagination support  
✅ **User Permissions**: Respects user roles and access controls  
✅ **Related Discovery**: Finds related tickets for assets  
✅ **Autocomplete**: Search suggestions and filter discovery  
✅ **Dual Authentication**: Supports both JSON API key and mobile JWT  
✅ **Complete Data**: Returns all 48+ asset fields and 20+ accessory fields  
✅ **Web Compatibility**: Exact same search logic as your web interface  

Your iOS app now has full search capabilities matching your web interface!