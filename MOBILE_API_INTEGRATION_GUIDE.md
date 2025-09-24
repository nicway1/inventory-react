# Mobile API Integration Guide for iOS Developer

## Overview
The mobile API has been enhanced to support comprehensive ticket viewing with Case Progress, Customer Information, and Tech Asset sections. This guide details the endpoints and data structures for iOS app integration.

## Base URL
```
https://inventory.truelog.com.sg/api/mobile/v1
```

## Authentication
All endpoints require JWT Bearer token authentication:
```
Headers: Authorization: Bearer <jwt_token>
```

## Key Endpoints for Ticket Views

### 1. Get Tickets List
**Endpoint:** `GET /tickets`
**Purpose:** Display tickets list with basic progress indicators

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `limit` (optional): Items per page (default: 20, max: 100)
- `status` (optional): Filter by status (OPEN, IN_PROGRESS, RESOLVED, etc.)

**Example Request:**
```
GET /api/mobile/v1/tickets?page=1&limit=20&status=OPEN
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response Structure:**
```json
{
  "success": true,
  "tickets": [
    {
      "id": 123,
      "display_id": "TIC-123",
      "subject": "Asset checkout request",
      "description": "Need laptop for new employee...",
      "status": "OPEN",
      "priority": "MEDIUM",
      "category": "ASSET_CHECKOUT_MAIN",
      "created_at": "2023-10-01T10:00:00",
      "updated_at": "2023-10-01T15:30:00",
      "requester": {
        "id": 456,
        "name": "John Doe",
        "email": "john@company.com"
      },
      "assigned_to": {
        "id": 789,
        "name": "Admin User",
        "email": "admin@company.com"
      },
      "queue": {
        "id": 1,
        "name": "IT Support"
      },
      "has_assets": true,
      "has_tracking": false,
      "customer_name": "John Doe"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 45,
    "pages": 3
  }
}
```

### 2. Get Ticket Detail (MAIN ENDPOINT FOR TICKET VIEWS)
**Endpoint:** `GET /tickets/<ticket_id>`
**Purpose:** Get comprehensive ticket information including all sections

**Example Request:**
```
GET /api/mobile/v1/tickets/123
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Full Response Structure:**
```json
{
  "success": true,
  "ticket": {
    "id": 123,
    "display_id": "TIC-123",
    "subject": "Asset checkout request",
    "description": "Need laptop for new employee starting Monday",
    "status": "OPEN",
    "priority": "MEDIUM",
    "category": "ASSET_CHECKOUT_MAIN",
    "created_at": "2023-10-01T10:00:00",
    "updated_at": "2023-10-01T15:30:00",
    "notes": "Urgent request - new starter",

    "requester": {
      "id": 456,
      "name": "John Doe",
      "email": "john@company.com",
      "username": "john.doe"
    },

    "assigned_to": {
      "id": 789,
      "name": "Admin User",
      "email": "admin@company.com",
      "username": "admin"
    },

    "queue": {
      "id": 1,
      "name": "IT Support"
    },

    // === CUSTOMER INFORMATION SECTION ===
    "customer": {
      "id": 456,
      "name": "John Doe",
      "email": "john@company.com",
      "phone": "+65 1234 5678",
      "address": "123 Main Street\nSingapore 123456",
      "company": {
        "id": 789,
        "name": "ABC Company Pte Ltd"
      }
    },

    // === TECH ASSET SECTION ===
    "assets": [
      {
        "id": 101,
        "serial_number": "ABC123DEF456",
        "asset_tag": "LAPTOP001",
        "model": "ThinkPad X1 Carbon",
        "manufacturer": "Lenovo",
        "status": "CHECKED_OUT"
      },
      {
        "id": 102,
        "serial_number": "XYZ789GHI012",
        "asset_tag": "MOUSE001",
        "model": "MX Master 3",
        "manufacturer": "Logitech",
        "status": "AVAILABLE"
      }
    ],

    // === CASE PROGRESS SECTION ===
    "case_progress": {
      "case_created": true,
      "assets_assigned": true,
      "tracking_added": false,
      "delivered": false
    },

    // === TRACKING INFORMATION ===
    "tracking": {
      "shipping_tracking": "1Z123456789",
      "shipping_carrier": "DHL",
      "shipping_status": "In Transit",
      "shipping_address": "123 Main Street\nSingapore 123456",
      "return_tracking": null,
      "return_status": null
    },

    // === COMMENTS SECTION ===
    "comments": [
      {
        "id": 1,
        "content": "Asset has been prepared and ready for shipment",
        "created_at": "2023-10-01T14:30:00",
        "user": {
          "id": 789,
          "name": "Admin User",
          "username": "admin"
        }
      }
    ]
  }
}
```

## Implementation Guide for iOS

### 1. **Case Progress Section**
Use the `case_progress` object to show visual progress indicators:

```swift
struct CaseProgress {
    let caseCreated: Bool
    let assetsAssigned: Bool
    let trackingAdded: Bool
    let delivered: Bool
}

// Display as progress bar or step indicators
// Green checkmarks for completed steps
// Gray/pending for incomplete steps
```

### 2. **Customer Information Section**
Display customer details in an organized card:

```swift
struct CustomerInfo {
    let id: Int
    let name: String
    let email: String?
    let phone: String?
    let address: String?
    let company: CompanyInfo?
}

struct CompanyInfo {
    let id: Int
    let name: String
}
```

### 3. **Tech Asset Section**
Show assets in a list or table format:

```swift
struct TechAsset {
    let id: Int
    let serialNumber: String
    let assetTag: String
    let model: String
    let manufacturer: String
    let status: String
}

// Display as cards or table rows
// Show status with color coding
// Allow tap for more asset details
```

### 4. **Tracking Information**
Show shipping/delivery status:

```swift
struct TrackingInfo {
    let shippingTracking: String?
    let shippingCarrier: String?
    let shippingStatus: String?
    let shippingAddress: String?
    let returnTracking: String?
    let returnStatus: String?
}
```

## Error Handling

### Common Error Responses:
```json
{
  "success": false,
  "error": "Ticket not found or access denied"
}
```

### HTTP Status Codes:
- `200`: Success
- `401`: Unauthorized (invalid/expired token)
- `404`: Ticket not found or no access
- `500`: Server error

## UI/UX Recommendations

1. **Case Progress**: Use a horizontal progress bar or step indicator
2. **Customer Information**: Card layout with contact details
3. **Tech Assets**: Expandable list with asset details
4. **Loading States**: Show skeleton screens while loading
5. **Error States**: Graceful error messages for failed requests
6. **Pull to Refresh**: Allow refreshing ticket details
7. **Caching**: Cache ticket details for offline viewing

## Testing

Use these example ticket IDs for testing:
- Valid ticket: Use any ticket ID from the tickets list
- Invalid ticket: Use ID `99999` to test 404 response
- Unauthorized: Test with expired/invalid token

## Timeline Display

All timestamps are in ISO 8601 format and should be converted to Singapore time for display:
```
"2023-10-01T10:00:00" → Display as Singapore local time
```

## Next Steps

1. Implement the ticket detail view with all sections
2. Test with various ticket types and statuses
3. Handle edge cases (missing data, network errors)
4. Implement proper error messaging
5. Add pull-to-refresh functionality
6. Test with different user permission levels

## Support

For any questions or issues with the API integration, please contact the backend team.