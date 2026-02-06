# TrueLog Mobile API Documentation

**Base URL:** `/api/mobile/v1`

This document provides comprehensive documentation for all mobile API endpoints in the TrueLog inventory management system. These RESTful API endpoints are specifically designed for iOS mobile app integration.

---

## Table of Contents

1. [Authentication](#authentication)
2. [User Management](#user-management)
3. [Tickets](#tickets)
4. [Inventory / Assets](#inventory--assets)
5. [Asset Images](#asset-images)
6. [Asset Labels](#asset-labels)
7. [Tracking](#tracking)
8. [Accessories](#accessories)
9. [Device Specs (MacBook Collector)](#device-specs-macbook-collector)
10. [Ticket Attachments](#ticket-attachments)
11. [Asset Intake Check-in](#asset-intake-check-in)
12. [PDF/OCR Asset Extraction](#pdfocr-asset-extraction)
13. [Service Records](#service-records)
14. [Utility Endpoints](#utility-endpoints)

---

## Authentication

All authenticated endpoints require a JWT Bearer token in the Authorization header:

```
Authorization: Bearer <token>
```

Tokens are obtained via the login endpoint and expire after 30 days.

---

### POST /auth/login

**Description:** Authenticate user and obtain JWT token for mobile access.

**Authentication:** None required

**Request Body:**
```json
{
  "username": "user@example.com",
  "password": "password123"
}
```

**Response (200):**
```json
{
  "success": true,
  "token": "jwt_token_here",
  "user": {
    "id": 1,
    "username": "user@example.com",
    "name": "user@example.com",
    "user_type": "SUPERVISOR",
    "email": "user@example.com",
    "is_admin": false,
    "is_supervisor": true,
    "permissions": {
      "can_view_assets": true,
      "can_create_assets": true,
      ...
    }
  }
}
```

**Error Responses:**
- `400`: Missing username or password
- `401`: Invalid credentials

---

### GET /auth/me

**Description:** Get current authenticated user's information.

**Authentication:** Required (Bearer Token)

**Response (200):**
```json
{
  "success": true,
  "user": {
    "id": 1,
    "username": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "user_type": "SUPERVISOR",
    "email": "user@example.com",
    "is_admin": false,
    "is_supervisor": true,
    "permissions": {...}
  }
}
```

---

## User Management

_(See /auth endpoints above)_

---

## Tickets

### GET /tickets

**Description:** Get paginated list of tickets for the current user. Staff users can view all tickets; client users see only their own.

**Authentication:** Required

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | int | 1 | Page number |
| limit | int | 20 | Items per page (max 100) |
| status | string | null | Filter by status (e.g., OPEN, IN_PROGRESS, RESOLVED) |

**Response (200):**
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
        "id": 1,
        "name": "john.doe",
        "email": "john.doe@example.com"
      },
      "assigned_to": {...},
      "queue": {"id": 1, "name": "IT Support"},
      "has_assets": true,
      "has_tracking": false,
      "customer_name": "Acme Corp"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 100,
    "pages": 5
  }
}
```

---

### GET /tickets/<ticket_id>

**Description:** Get detailed ticket information including case progress, customer info, tech assets, tracking, comments, and attachments.

**Authentication:** Required

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| ticket_id | int | Ticket ID |

**Response (200):**
```json
{
  "success": true,
  "ticket": {
    "id": 123,
    "display_id": "TIC-123",
    "subject": "...",
    "description": "...",
    "status": "OPEN",
    "priority": "MEDIUM",
    "category": "ASSET_CHECKOUT_MAIN",
    "notes": "...",
    "created_at": "2023-10-01T10:00:00",
    "updated_at": "2023-10-01T15:30:00",
    "requester": {...},
    "assigned_to": {...},
    "queue": {...},
    "customer": {
      "id": 1,
      "name": "John Doe",
      "email": "john@example.com",
      "phone": "+65 1234 5678",
      "address": "123 Main St",
      "company": {"id": 1, "name": "Acme Corp"}
    },
    "assets": [
      {
        "id": 1,
        "serial_number": "SN123456",
        "asset_tag": "ASSET-001",
        "model": "MacBook Pro",
        "manufacturer": "Apple",
        "status": "DEPLOYED",
        "image_url": "https://..."
      }
    ],
    "case_progress": {
      "case_created": true,
      "assets_assigned": true,
      "tracking_added": false,
      "delivered": false
    },
    "tracking": {
      "shipping_tracking": "XZB123456",
      "shipping_carrier": "SingPost",
      "shipping_status": "In Transit",
      "shipping_address": "...",
      "return_tracking": null,
      "return_status": null
    },
    "comments": [
      {
        "id": 1,
        "content": "Asset has been shipped",
        "created_at": "2023-10-02T09:00:00",
        "user": {"id": 2, "name": "admin", "username": "admin"}
      }
    ],
    "attachments": [
      {
        "id": 1,
        "filename": "invoice.pdf",
        "content_type": "application/pdf",
        "url": "https://...",
        "thumbnail_url": null,
        "size": 245678,
        "created_at": "2023-10-01T10:35:00"
      }
    ]
  }
}
```

**Error Responses:**
- `404`: Ticket not found or access denied

---

### GET /tickets/<ticket_id>/assets

**Description:** Get ticket's assets and tracking info optimized for inline display.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "ticket": {
    "id": 123,
    "ticket_id": 123,
    "display_id": "#TL-00123",
    "subject": "Asset Return Request",
    "category": "Asset Return (claw)",
    "customer_name": "John Doe",
    "assets": [
      {
        "id": 1,
        "asset_tag": "SG-1001",
        "serial_number": "SN123",
        "name": "MacBook Pro",
        "model": "A2338",
        "status": "DEPLOYED",
        "image_url": "https://..."
      }
    ],
    "outbound_tracking": {
      "tracking_number": "XZB123456",
      "carrier": "SingPost",
      "status": "in_transit",
      "is_received": false,
      "events": []
    },
    "return_tracking": null
  }
}
```

---

### POST /tickets/<ticket_id>/assets

**Description:** Add an existing asset to a ticket.

**Authentication:** Required

**Request Body:**
```json
{
  "asset_id": 456
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Asset successfully added to ticket"
}
```

**Error Responses:**
- `400`: asset_id required or asset already assigned
- `404`: Ticket or asset not found

---

## Inventory / Assets

### GET /inventory

**Description:** Get paginated inventory assets with optional filters.

**Authentication:** Required (must have `can_view_assets` permission)

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | int | 1 | Page number |
| limit | int | 20 | Items per page (max 100) |
| status | string | null | Filter by status (e.g., DEPLOYED, IN_STOCK) |
| search | string | null | Text search across name, asset_tag, serial_num, model |
| manufacturer | string | null | Filter by manufacturer (partial match) |
| category | string | null | Filter by category (partial match) |
| country | string | null | Filter by country (exact match) |
| asset_type | string | null | Filter by asset type |
| location_id | int | null | Filter by location ID |
| has_assignee | string | null | 'true' or 'false' - filter by assignment status |

**Response (200):**
```json
{
  "success": true,
  "assets": [
    {
      "id": 1,
      "asset_tag": "SG-1001",
      "name": "MacBook Pro 14",
      "model": "A2338",
      "serial_num": "C02XG1YHJK77",
      "status": "DEPLOYED",
      "asset_type": "APPLE",
      "manufacturer": "Apple",
      "location": "Singapore Office",
      "country": "Singapore",
      "image_url": "https://...",
      "assigned_to": {
        "id": 5,
        "name": "John Doe",
        "email": "john@example.com"
      },
      "customer_user": {...}
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 100,
    "pages": 5
  }
}
```

---

### POST /assets

**Description:** Create a new tech asset from mobile app (including from QR code scan).

**Authentication:** Required (must have `can_create_assets` permission)

**Request Body:**
```json
{
  "asset_tag": "ASSET-001",
  "serial_num": "SN123456",
  "name": "MacBook Pro 14",
  "model": "MacBook Pro 14-inch 2023",
  "manufacturer": "Apple",
  "category": "Laptop",
  "hardware_type": "Laptop",
  "country": "Singapore",
  "status": "IN_STOCK",
  "notes": "Optional notes",
  "customer": "CUSTOMER_NAME",
  "asset_type": "APPLE",
  "condition": "New",
  "cpu_type": "M3 Pro",
  "cpu_cores": "12",
  "gpu_cores": "18",
  "memory": "18GB",
  "storage": "512GB",
  "diagnostics_code": "DIAG123",
  "is_erased": true,
  "has_keyboard": true,
  "has_charger": true,
  "receiving_date": "2025-01-15",
  "po": "PO-12345",
  "image": "base64_encoded_image_data"
}
```

**Response (201):**
```json
{
  "success": true,
  "message": "Asset created successfully",
  "asset": {
    "id": 123,
    "asset_tag": "ASSET-001",
    "serial_num": "SN123456",
    "name": "MacBook Pro 14",
    "model": "MacBook Pro 14-inch 2023",
    "manufacturer": "Apple",
    "status": "IN_STOCK",
    "image_url": "https://...",
    "created_at": "2025-01-15T10:00:00",
    ...
  }
}
```

**Error Responses:**
- `400`: Missing required fields or duplicate asset_tag/serial_num
- `403`: No permission to create assets

---

### GET /assets/search

**Description:** Search for assets by asset tag, serial number, or name.

**Authentication:** Required

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| q | string | required | Search query |
| limit | int | 20 | Max results (max 50) |

**Response (200):**
```json
{
  "success": true,
  "assets": [
    {
      "id": 1,
      "asset_tag": "SG-1001",
      "serial_number": "SN123456",
      "name": "MacBook Pro",
      "model": "A2338",
      "status": "DEPLOYED",
      "image_url": "https://..."
    }
  ]
}
```

---

### POST /create-assets

**Description:** Bulk create assets from mobile app with full control over all fields.

**Authentication:** Required

**Request Body:**
```json
{
  "ticket_id": 2040,
  "company_id": 5,
  "assets": [
    {
      "serial_num": "C02XG1YHJK77",
      "asset_tag": "SG-1207",
      "name": "13\" MacBook Air",
      "model": "A3240",
      "cpu_type": "M4",
      "cpu_cores": "10",
      "gpu_cores": "8",
      "memory": "16GB",
      "harddrive": "256GB",
      "hardware_type": "13\" MacBook Air M4 10-Core 256GB",
      "manufacturer": "Apple",
      "category": "APPLE",
      "condition": "New",
      "country": "Singapore"
    }
  ]
}
```

**Response (200):**
```json
{
  "success": true,
  "created_count": 56,
  "error_count": 0,
  "assets": [...],
  "errors": [],
  "ticket_id": 2040,
  "message": "Successfully created 56 asset(s) and linked to ticket #2040"
}
```

---

## Asset Images

### POST /assets/<asset_id>/image

**Description:** Upload an image for an asset.

**Authentication:** Required

**Request Body (JSON):**
```json
{
  "image": "base64_encoded_image_data",
  "content_type": "image/jpeg"
}
```

**OR multipart/form-data with 'image' file field**

**Response (200):**
```json
{
  "success": true,
  "message": "Image uploaded successfully",
  "image_url": "https://.../static/uploads/assets/asset_123_timestamp.jpg",
  "asset_id": 123
}
```

**Error Responses:**
- `400`: No image data or invalid base64
- `404`: Asset not found

---

### GET /assets/<asset_id>/image

**Description:** Get asset image URL.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "image_url": "https://.../static/uploads/assets/asset_123.jpg",
  "has_image": true,
  "asset_id": 123
}
```

---

### DELETE /assets/<asset_id>/image

**Description:** Delete asset image.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "message": "Image deleted successfully"
}
```

---

## Asset Labels

### GET /assets/<asset_id>/label

**Description:** Get asset label as base64 image for printing.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "label": "data:image/png;base64,...",
  "asset": {
    "id": 123,
    "serial_num": "SN123456",
    "asset_tag": "SG-1001",
    "name": "MacBook Pro"
  }
}
```

---

## Tracking

### GET /tracking/outbound

**Description:** Get all tickets with outbound/shipping tracking.

**Authentication:** Required

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | int | 1 | Page number |
| limit | int | 20 | Items per page (max 100) |
| status | string | all | Filter: 'pending', 'in_transit', 'delivered', 'all' |

**Response (200):**
```json
{
  "success": true,
  "tracking_items": [
    {
      "ticket_id": 123,
      "display_id": "TIC-123",
      "subject": "Asset Checkout",
      "category": "ASSET_CHECKOUT_MAIN",
      "customer_name": "John Doe",
      "shipping_address": "123 Main St",
      "tracking_numbers": [
        {
          "slot": 1,
          "tracking_number": "XZB123456",
          "carrier": "SingPost",
          "status": "In Transit",
          "is_delivered": false
        }
      ],
      "created_at": "2025-01-15T10:00:00",
      "updated_at": "2025-01-16T14:30:00"
    }
  ],
  "pagination": {...}
}
```

---

### POST /tracking/outbound/<ticket_id>/mark-received

**Description:** Mark outbound/shipping tracking as received/delivered.

**Authentication:** Required

**Request Body:**
```json
{
  "slot": 1,
  "notes": "Received by customer"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Marked as received",
  "tracking": {
    "ticket_id": 123,
    "slot": 1,
    "tracking_number": "XZB123456",
    "status": "Delivered - Received on 2025-01-16 14:30 - Received by customer"
  }
}
```

---

### GET /tickets/<ticket_id>/tracking

**Description:** Get tracking information for a ticket with optional refresh from carrier API.

**Authentication:** Required

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| force_refresh | bool | false | Bypass cache and fetch fresh data |
| slot | int | 1 | Which tracking slot (1-5) |

**Response (200):**
```json
{
  "success": true,
  "tracking": {
    "tracking_number": "XZB123456",
    "carrier": "SingPost",
    "status": "Information Received",
    "was_pushed": false,
    "origin_country": "Singapore",
    "destination_country": "Malaysia",
    "events": [
      {
        "timestamp": "2025-01-15T10:00:00",
        "location": "Singapore",
        "description": "Parcel collected",
        "status": "collected"
      }
    ],
    "is_cached": false,
    "last_updated": "2025-01-16T10:00:00"
  }
}
```

---

### POST /tracking/lookup

**Description:** Look up a tracking number directly without ticket association (SingPost only).

**Authentication:** Required

**Request Body:**
```json
{
  "tracking_number": "XZB123456"
}
```

**Response (200):**
```json
{
  "success": true,
  "tracking": {
    "tracking_number": "XZB123456",
    "carrier": "SingPost",
    "status": "Information Received",
    "was_pushed": false,
    "origin_country": "Singapore",
    "destination_country": "Malaysia",
    "events": [...],
    "last_updated": "2025-01-16T10:00:00"
  }
}
```

---

### GET /tracking/return

**Description:** Get all tickets with return tracking.

**Authentication:** Required

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | int | 1 | Page number |
| limit | int | 20 | Items per page (max 100) |
| status | string | all | Filter: 'pending', 'in_transit', 'received', 'all' |

**Response (200):**
```json
{
  "success": true,
  "tracking_items": [
    {
      "ticket_id": 123,
      "display_id": "TIC-123",
      "subject": "Asset Return",
      "category": "ASSET_RETURN",
      "customer_name": "John Doe",
      "return_tracking": "RET123456",
      "return_status": "In Transit",
      "is_received": false,
      "shipping_address": "123 Main St",
      "created_at": "2025-01-15T10:00:00",
      "updated_at": "2025-01-16T14:30:00"
    }
  ],
  "pagination": {...}
}
```

---

### POST /tracking/return/<ticket_id>/mark-received

**Description:** Mark return tracking as received.

**Authentication:** Required

**Request Body:**
```json
{
  "notes": "Package received in good condition"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Return marked as received",
  "tracking": {
    "ticket_id": 123,
    "return_tracking": "RET123456",
    "return_status": "Received on 2025-01-16 14:30 - Package received in good condition"
  }
}
```

---

### POST /tickets/<ticket_id>/tracking/outbound/received

**Description:** Alternative URL pattern for marking outbound tracking as received.

**Authentication:** Required

**Request Body:**
```json
{
  "slot": 1,
  "notes": "Package received in good condition"
}
```

---

### POST /tickets/<ticket_id>/tracking/return/received

**Description:** Alternative URL pattern for marking return tracking as received.

**Authentication:** Required

**Request Body:**
```json
{
  "notes": "Return package received"
}
```

---

### POST /tickets/<ticket_id>/tracking/refresh

**Description:** Refresh tracking information from carrier API.

**Authentication:** Required

**Request Body:**
```json
{
  "type": "outbound"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Tracking information refreshed",
  "tracking": {
    "tracking_number": "XZB123456",
    "carrier": "SingPost",
    "status": "in_transit",
    "is_received": false,
    "events": [...]
  }
}
```

---

## Accessories

### GET /accessories

**Description:** Get accessories list with optional filters.

**Authentication:** Required

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | int | 1 | Page number |
| limit | int | 20 | Items per page (max 100) |
| search | string | null | Text search across name, model_no, manufacturer |
| category | string | null | Filter by category |
| country | string | null | Filter by country |
| status | string | null | Filter by status |

**Response (200):**
```json
{
  "success": true,
  "accessories": [
    {
      "id": 1,
      "name": "USB-C Cable",
      "category": "Cable",
      "manufacturer": "Apple",
      "model_no": "MLL82AM/A",
      "total_quantity": 50,
      "available_quantity": 35,
      "country": "Singapore",
      "status": "Available",
      "notes": "2m length",
      "image_url": "https://...",
      "company": {"id": 1, "name": "Acme Corp"},
      "created_at": "2025-01-15T10:00:00",
      "updated_at": "2025-01-16T14:30:00"
    }
  ],
  "pagination": {...}
}
```

---

### GET /accessories/<accessory_id>

**Description:** Get detailed accessory information.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "accessory": {
    "id": 123,
    "name": "USB-C Cable",
    "category": "Cable",
    "manufacturer": "Apple",
    "model_no": "MLL82AM/A",
    "total_quantity": 50,
    "available_quantity": 35,
    "country": "Singapore",
    "status": "Available",
    "notes": "2m length",
    "image_url": "https://...",
    "customer_id": null,
    "company": {...},
    "checkout_date": null,
    "return_date": null,
    "created_at": "2025-01-15T10:00:00",
    "updated_at": "2025-01-16T14:30:00"
  }
}
```

---

### GET /accessories/search

**Description:** Search for accessories by name, model number, or manufacturer.

**Authentication:** Required

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| q | string | required | Search query |
| limit | int | 20 | Max results (max 50) |

**Response (200):**
```json
{
  "success": true,
  "accessories": [...]
}
```

---

### POST /accessories/<accessory_id>/image

**Description:** Upload an image for an accessory.

**Authentication:** Required

**Request Body:** Same as asset image upload.

---

### GET /accessories/<accessory_id>/image

**Description:** Get accessory image URL.

**Authentication:** Required

---

### DELETE /accessories/<accessory_id>/image

**Description:** Delete accessory image.

**Authentication:** Required

---

## Device Specs (MacBook Collector)

### GET /specs

**Description:** Get list of pending device specs from MacBook Specs Collector app.

**Authentication:** Required

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| processed | string | false | 'true' or 'false' to filter by processed status |
| limit | int | 50 | Max number of results (max 100) |

**Response (200):**
```json
{
  "success": true,
  "count": 10,
  "specs": [
    {
      "id": 1,
      "serial_number": "C02XG1YHJK77",
      "model_id": "Mac14,2",
      "model_name": "MacBook Pro 14-inch 2023",
      "cpu": "Apple M3 Pro",
      "cpu_cores": "12",
      "ram_gb": 18,
      "storage_gb": 512,
      "storage_type": "SSD",
      "battery_cycles": 45,
      "battery_health": "Normal",
      "submitted_at": "2025-01-15T10:00:00",
      "processed": false
    }
  ]
}
```

---

### GET /specs/<spec_id>

**Description:** Get detailed device spec information for auto-filling asset creation form.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "spec": {
    "id": 1,
    "serial_number": "C02XG1YHJK77",
    "hardware_uuid": "ABC123-...",
    "model_id": "Mac14,2",
    "model_name": "MacBook Pro",
    "model_name_translated": "MacBook Pro 14-inch 2023",
    "cpu": "Apple M3 Pro",
    "cpu_cores": "12",
    "gpu": "Apple M3 Pro GPU",
    "gpu_cores": "18",
    "ram_gb": 18,
    "memory_type": "Unified",
    "storage_gb": 512,
    "storage_type": "SSD",
    "free_space": 350,
    "os_name": "macOS",
    "os_version": "14.2",
    "os_build": "23C64",
    "battery_cycles": 45,
    "battery_health": "Normal",
    "wifi_mac": "AA:BB:CC:DD:EE:FF",
    "ethernet_mac": null,
    "ip_address": "192.168.1.100",
    "submitted_at": "2025-01-15T10:00:00",
    "processed": false,
    "processed_at": null,
    "asset_id": null,
    "asset_prefill": {
      "serial_num": "C02XG1YHJK77",
      "model": "Mac14,2",
      "product": "MacBook Pro 14-inch 2023",
      "asset_type": "APPLE",
      "cpu_type": "Apple M3 Pro",
      "cpu_cores": "12",
      "gpu_cores": "18",
      "memory": "18 GB",
      "harddrive": "512 GB SSD",
      "manufacturer": "Apple"
    }
  }
}
```

---

### POST /specs/<spec_id>/create-asset

**Description:** Create an asset from a device spec.

**Authentication:** Required

**Request Body:**
```json
{
  "asset_tag": "SG-1001",
  "status": "IN_STOCK",
  "condition": "New",
  "customer": "Acme Corp",
  "country": "Singapore",
  "notes": "Created from collector"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Asset created successfully",
  "asset": {
    "id": 123,
    "asset_tag": "SG-1001",
    "serial_num": "C02XG1YHJK77",
    "name": "MacBook Pro 14-inch 2023",
    "model": "Mac14,2",
    "status": "IN_STOCK"
  }
}
```

**Error Responses:**
- `400`: Spec already processed
- `403`: No permission to create assets
- `409`: Serial number already exists

---

### POST /specs/<spec_id>/mark-processed

**Description:** Mark a spec as processed without creating an asset (for skipping/dismissing).

**Authentication:** Required

**Request Body:**
```json
{
  "notes": "Reason for marking as processed"
}
```

---

### GET /specs/<spec_id>/find-tickets

**Description:** Find tickets related to a device spec by searching serial number, model, etc.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "count": 2,
  "tickets": [
    {
      "id": 123,
      "display_id": "#TL-00123",
      "title": "Asset checkout for new employee",
      "status": "IN_PROGRESS",
      "category": "ASSET_CHECKOUT_MAIN",
      "created_at": "2025-01-15T10:00:00",
      "customer_name": "John Doe"
    }
  ],
  "search_terms": ["C02XG1YHJK77", "Mac14,2"]
}
```

---

### POST /specs/<spec_id>/create-asset-with-ticket

**Description:** Create an asset from a device spec and link it to a ticket.

**Authentication:** Required

**Request Body:**
```json
{
  "ticket_id": 123,
  "asset_tag": "SG-1001",
  "status": "IN_STOCK",
  "condition": "New",
  "notes": "Created and linked"
}
```

---

## Ticket Attachments

### POST /tickets/<ticket_id>/attachments

**Description:** Upload an attachment to a ticket.

**Authentication:** Required

**Content-Type:** multipart/form-data

**Form Fields:**
| Field | Type | Description |
|-------|------|-------------|
| file | file | The file to upload |

**Allowed Extensions:** jpg, jpeg, png, gif, pdf, doc, docx, xls, xlsx, txt, csv

**Max Size:** 10MB

**Response (201):**
```json
{
  "success": true,
  "message": "Document uploaded successfully",
  "attachment_id": 456,
  "attachment": {
    "id": 456,
    "filename": "scanned_document.jpg",
    "content_type": "image/jpeg",
    "size": 245678,
    "url": "https://.../uploads/tickets/123/...",
    "thumbnail_url": "https://.../uploads/tickets/123/thumb_...",
    "created_at": "2025-12-23T10:30:00Z"
  }
}
```

---

### GET /tickets/<ticket_id>/attachments

**Description:** Get all attachments for a ticket.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "attachments": [
    {
      "id": 456,
      "filename": "document.pdf",
      "content_type": "application/pdf",
      "size": 245678,
      "url": "https://...",
      "thumbnail_url": "https://...",
      "created_at": "2025-12-23T10:30:00Z",
      "uploaded_by": {"id": 1, "name": "admin"}
    }
  ],
  "total": 5
}
```

---

### DELETE /tickets/<ticket_id>/attachments/<attachment_id>

**Description:** Delete an attachment from a ticket.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "message": "Attachment deleted successfully"
}
```

---

### GET /tickets/<ticket_id>/attachments/<attachment_id>/download

**Description:** Download a ticket attachment file.

**Authentication:** Required

**Response:** Raw file data with appropriate Content-Type header.

---

## Asset Intake Check-in

### POST /tickets/<ticket_id>/checkin

**Description:** Check in an asset by serial number for Asset Intake tickets.

**Authentication:** Required

**Request Body:**
```json
{
  "serial_number": "SN123456789"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Asset SN123 checked in successfully",
  "asset": {
    "id": 1,
    "serial_number": "SN123",
    "asset_tag": "ASSET-001",
    "model": "MacBook Pro"
  },
  "progress": {
    "total": 10,
    "checked_in": 5,
    "pending": 5,
    "progress_percent": 50,
    "step": 2
  },
  "ticket_closed": false
}
```

---

### GET /tickets/<ticket_id>/checkin-status

**Description:** Get check-in status for an Asset Intake ticket.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "ticket": {
    "id": 123,
    "display_id": "TICK-0123",
    "subject": "Asset Intake",
    "status": "In Progress"
  },
  "progress": {
    "step": 2,
    "step_label": "Assets Added",
    "total": 10,
    "checked_in": 5,
    "pending": 5,
    "progress_percent": 50
  },
  "steps": [
    {"number": 1, "label": "Case Created", "completed": true},
    {"number": 2, "label": "Assets Added", "completed": true},
    {"number": 3, "label": "All Checked In", "completed": false}
  ],
  "assets": [
    {
      "id": 1,
      "serial_number": "SN001",
      "asset_tag": "ASSET-001",
      "model": "MacBook Pro",
      "checked_in": true,
      "checked_in_at": "2025-12-23T10:30:00Z",
      "checked_in_by": "John Doe"
    }
  ]
}
```

---

### GET /tickets/<ticket_id>/intake-assets

**Description:** Get list of assets for an Asset Intake ticket with check-in status (optimized for mobile).

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "assets": [
    {
      "id": 1,
      "serial_number": "SN001",
      "asset_tag": "ASSET-001",
      "model": "MacBook Pro",
      "type": null,
      "image_url": "https://...",
      "checked_in": true,
      "checked_in_at": "2025-12-23T10:30:00Z"
    }
  ],
  "summary": {
    "total": 10,
    "checked_in": 5,
    "pending": 5
  }
}
```

---

### POST /tickets/<ticket_id>/undo-checkin/<asset_id>

**Description:** Undo a check-in for an asset.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "message": "Check-in undone successfully",
  "progress": {
    "total": 10,
    "checked_in": 4,
    "pending": 6,
    "progress_percent": 40,
    "step": 2
  }
}
```

---

### POST /tickets/<ticket_id>/update-serial-checkin

**Description:** Update an asset's serial number and check it in (for correcting OCR errors).

**Authentication:** Required

**Request Body:**
```json
{
  "asset_id": 123,
  "new_serial": "K59L170P9P"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Asset serial updated and checked in successfully",
  "asset": {
    "id": 123,
    "serial_number": "K59L170P9P",
    "asset_tag": "SG-1234",
    "model": "MacBook Pro 14"
  },
  "progress": {...},
  "ticket_closed": false
}
```

---

## PDF/OCR Asset Extraction

### POST /extract-assets-from-text

**Description:** Extract asset information from pre-extracted OCR text (iOS Vision framework).

**Authentication:** Required

**Request Body:**
```json
{
  "text": "The OCR-extracted text from the packing list PDF",
  "ticket_id": 123
}
```

**Response (200):**
```json
{
  "success": true,
  "assets": [
    {
      "serial_num": "ABC123...",
      "name": "MacBook Air",
      "model": "A3113",
      "manufacturer": "Apple",
      "category": "Laptop",
      "cpu_type": "M3",
      "cpu_cores": "8",
      "gpu_cores": "10",
      "memory": "16GB",
      "harddrive": "256GB",
      "hardware_type": "Laptop",
      "condition": "New"
    }
  ],
  "count": 10,
  "message": "Successfully extracted 10 assets"
}
```

---

### POST /tickets/<ticket_id>/create-assets-from-text

**Description:** Create assets from OCR text and link them to a ticket.

**Authentication:** Required

**Request Body:**
```json
{
  "text": "The OCR-extracted text",
  "asset_tags": ["SG-1180", "SG-1181"],
  "company_id": 1
}
```

**Response (200):**
```json
{
  "success": true,
  "created_assets": [...],
  "count": 10,
  "ticket_id": 123,
  "ticket_display_id": "#TL-00123",
  "message": "Successfully created 10 assets and linked to ticket #TL-00123"
}
```

---

### GET /companies

**Description:** Get list of all companies for mobile app dropdown.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "companies": [
    {"id": 1, "name": "Company A", "grouped_display_name": "Company A"},
    {"id": 2, "name": "Company B", "grouped_display_name": "Company B"}
  ]
}
```

---

### GET /next-asset-tag

**Description:** Get the next available asset tag number and optionally pre-generate a list of tags.

**Authentication:** Required

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| prefix | string | SG- | Tag prefix |
| count | int | 1 | Number of tags to generate (max 200) |

**Response (200):**
```json
{
  "success": true,
  "next_number": 1207,
  "prefix": "SG-",
  "tags": ["SG-1207", "SG-1208", "SG-1209"]
}
```

---

### GET /intake/tickets/<ticket_id>/pdf-attachments

**Description:** Get list of PDF attachments for a ticket that can be processed for asset extraction.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "ticket_id": 123,
  "ticket_number": "INT-2025-001",
  "attachments": [
    {
      "id": 1,
      "filename": "delivery_order.pdf",
      "uploaded_at": "2025-01-15T10:30:00Z",
      "uploaded_by": "admin"
    }
  ]
}
```

---

### GET /intake/tickets/<ticket_id>/extract-assets

**Description:** Extract assets from all PDF attachments of an intake ticket using OCR.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "ticket_id": 123,
  "ticket_number": "INT-2025-001",
  "total_assets": 8,
  "results": [
    {
      "attachment_id": 1,
      "filename": "4500153441 SOPHOS.pdf",
      "po_number": "4500153441",
      "do_number": "SCT-DO250154",
      "customer": "Sophos Computer Security Pte Ltd",
      "ship_date": "13 Jan 2026",
      "assets": [
        {
          "serial_num": "0F3P86Y25463P7",
          "name": "Surface Laptop",
          "model": "Surface Laptop 7th Edition",
          "manufacturer": "Microsoft",
          "memory": "32GB",
          "storage": "512GB",
          "cpu_type": "Intel Core Ultra"
        }
      ],
      "error": null
    }
  ]
}
```

---

### POST /intake/tickets/<ticket_id>/import-assets

**Description:** Import extracted assets into inventory from PDF extraction results.

**Authentication:** Required

**Request Body:**
```json
{
  "company_id": 1,
  "customer_name": "Sophos",
  "country": "Singapore",
  "status": "Available",
  "assets": [
    {
      "serial_num": "0F3P86Y25463P7",
      "name": "Surface Laptop",
      "model": "Surface Laptop 7th Edition",
      "manufacturer": "Microsoft",
      "memory": "32GB",
      "storage": "512GB",
      "cpu_type": "Intel Core Ultra",
      "po_number": "4500153441",
      "do_number": "SCT-DO250154"
    }
  ]
}
```

**Response (200):**
```json
{
  "success": true,
  "imported_count": 7,
  "skipped_count": 1,
  "errors": ["Serial 0F3P86Y25463P7 already exists (Asset #123)"],
  "imported_assets": [
    {"id": 456, "serial_num": "0F36YW925483P7", "name": "Surface Laptop"}
  ],
  "ticket_status": "COMPLETED"
}
```

---

### GET /intake/extract-single-pdf/<attachment_id>

**Description:** Extract assets from a single PDF attachment.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "attachment_id": 1,
  "filename": "delivery_order.pdf",
  "po_number": "4500153441",
  "do_number": "SCT-DO250154",
  "reference": null,
  "customer": "Sophos Computer Security Pte Ltd",
  "ship_date": "13 Jan 2026",
  "supplier": "Success Tech",
  "total_quantity": 7,
  "assets": [...]
}
```

**Error Responses:**
- `408`: PDF extraction timed out (max 120 seconds)

---

## Service Records

### GET /tickets/<ticket_id>/service-records

**Description:** Get all service records for a ticket.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "service_records": [
    {
      "id": 1,
      "request_id": "SR-0001",
      "ticket_id": 123,
      "asset_id": 456,
      "asset_tag": "ASSET-001",
      "service_type": "OS Reinstall",
      "description": "Full OS reinstallation required",
      "status": "Requested",
      "requested_by_id": 1,
      "requested_by_name": "john.doe",
      "completed_by_id": null,
      "completed_by_name": null,
      "completed_at": null,
      "created_at": "2026-01-19T10:30:00"
    }
  ],
  "assets": [
    {"id": 456, "asset_tag": "ASSET-001", "serial_num": "SN123", "model": "MacBook Pro"}
  ],
  "service_types": ["OS Reinstall", "Hardware Repair", "Data Recovery", ...],
  "status_options": ["Requested", "In Progress", "Completed"]
}
```

---

### POST /tickets/<ticket_id>/service-records

**Description:** Add a new service record to a ticket.

**Authentication:** Required

**Request Body:**
```json
{
  "service_type": "OS Reinstall",
  "description": "Full OS reinstallation required",
  "asset_id": 456,
  "status": "Requested"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Service record added successfully",
  "service_record": {
    "id": 1,
    "request_id": "SR-0001",
    ...
  }
}
```

---

### GET /tickets/<ticket_id>/service-records/<record_id>

**Description:** Get a specific service record.

**Authentication:** Required

---

### PUT /tickets/<ticket_id>/service-records/<record_id>/status

**Description:** Update the status of a service record.

**Authentication:** Required

**Request Body:**
```json
{
  "status": "In Progress"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Service record status updated",
  "service_record": {...}
}
```

---

### DELETE /tickets/<ticket_id>/service-records/<record_id>

**Description:** Delete a service record.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "message": "Service record deleted successfully"
}
```

---

### GET /assets/<asset_id>/service-records

**Description:** Get all service records for a specific asset (across all tickets).

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "asset": {
    "id": 456,
    "asset_tag": "ASSET-001",
    "serial_num": "SN123456",
    "model": "MacBook Pro"
  },
  "service_records": [...]
}
```

---

## Utility Endpoints

### GET /dashboard

**Description:** Get dashboard statistics for mobile.

**Authentication:** Required

**Response (200):**
```json
{
  "success": true,
  "stats": {
    "total_tickets": 50,
    "open_tickets": 25,
    "assigned_tickets": 10,
    "total_assets": 100,
    "available_assets": 75
  }
}
```

---

### GET /health

**Description:** Health check endpoint.

**Authentication:** None required

**Response (200):**
```json
{
  "success": true,
  "status": "healthy",
  "timestamp": "2025-01-01T12:00:00Z"
}
```

---

### GET /debug/routes

**Description:** Debug endpoint to list all registered mobile API routes.

**Authentication:** None required

**Response (200):**
```json
{
  "success": true,
  "routes": [
    {
      "endpoint": "mobile_api.mobile_login",
      "methods": ["OPTIONS", "POST"],
      "url": "/api/mobile/v1/auth/login"
    }
  ],
  "total": 65
}
```

---

## Error Response Format

All endpoints return errors in a consistent format:

```json
{
  "success": false,
  "error": "Error message describing what went wrong"
}
```

Common HTTP status codes:
- `400`: Bad Request - Invalid input data
- `401`: Unauthorized - Missing or invalid authentication token
- `403`: Forbidden - User lacks required permissions
- `404`: Not Found - Resource not found
- `408`: Request Timeout - Operation timed out
- `409`: Conflict - Resource already exists (duplicate)
- `413`: Payload Too Large - File too large
- `415`: Unsupported Media Type - Invalid file type
- `500`: Internal Server Error - Server-side error

---

## Summary of Endpoints

| Endpoint | Method | Authentication | Description |
|----------|--------|----------------|-------------|
| `/auth/login` | POST | No | User login |
| `/auth/me` | GET | Yes | Get current user |
| `/tickets` | GET | Yes | List tickets |
| `/tickets/<id>` | GET | Yes | Get ticket details |
| `/tickets/<id>/assets` | GET | Yes | Get ticket assets |
| `/tickets/<id>/assets` | POST | Yes | Add asset to ticket |
| `/inventory` | GET | Yes | List inventory |
| `/assets` | POST | Yes | Create asset |
| `/assets/search` | GET | Yes | Search assets |
| `/assets/<id>/label` | GET | Yes | Get asset label |
| `/assets/<id>/image` | GET/POST/DELETE | Yes | Asset image operations |
| `/create-assets` | POST | Yes | Bulk create assets |
| `/tracking/outbound` | GET | Yes | List outbound tracking |
| `/tracking/outbound/<id>/mark-received` | POST | Yes | Mark outbound received |
| `/tickets/<id>/tracking` | GET | Yes | Get ticket tracking |
| `/tracking/lookup` | POST | Yes | Lookup tracking number |
| `/tracking/return` | GET | Yes | List return tracking |
| `/tracking/return/<id>/mark-received` | POST | Yes | Mark return received |
| `/tickets/<id>/tracking/outbound/received` | POST | Yes | Mark outbound received (alt) |
| `/tickets/<id>/tracking/return/received` | POST | Yes | Mark return received (alt) |
| `/tickets/<id>/tracking/refresh` | POST | Yes | Refresh tracking |
| `/accessories` | GET | Yes | List accessories |
| `/accessories/<id>` | GET | Yes | Get accessory details |
| `/accessories/search` | GET | Yes | Search accessories |
| `/accessories/<id>/image` | GET/POST/DELETE | Yes | Accessory image operations |
| `/specs` | GET | Yes | List device specs |
| `/specs/<id>` | GET | Yes | Get spec details |
| `/specs/<id>/create-asset` | POST | Yes | Create asset from spec |
| `/specs/<id>/mark-processed` | POST | Yes | Mark spec processed |
| `/specs/<id>/find-tickets` | GET | Yes | Find related tickets |
| `/specs/<id>/create-asset-with-ticket` | POST | Yes | Create asset with ticket link |
| `/tickets/<id>/attachments` | GET/POST | Yes | Ticket attachments |
| `/tickets/<id>/attachments/<id>` | DELETE | Yes | Delete attachment |
| `/tickets/<id>/attachments/<id>/download` | GET | Yes | Download attachment |
| `/tickets/<id>/checkin` | POST | Yes | Check in asset |
| `/tickets/<id>/checkin-status` | GET | Yes | Get check-in status |
| `/tickets/<id>/intake-assets` | GET | Yes | Get intake assets |
| `/tickets/<id>/undo-checkin/<asset_id>` | POST | Yes | Undo check-in |
| `/tickets/<id>/update-serial-checkin` | POST | Yes | Update serial & check in |
| `/extract-assets-from-text` | POST | Yes | Extract assets from text |
| `/tickets/<id>/create-assets-from-text` | POST | Yes | Create assets from text |
| `/companies` | GET | Yes | List companies |
| `/next-asset-tag` | GET | Yes | Get next asset tag |
| `/intake/tickets/<id>/pdf-attachments` | GET | Yes | List PDF attachments |
| `/intake/tickets/<id>/extract-assets` | GET | Yes | Extract assets from PDFs |
| `/intake/tickets/<id>/import-assets` | POST | Yes | Import extracted assets |
| `/intake/extract-single-pdf/<id>` | GET | Yes | Extract single PDF |
| `/tickets/<id>/service-records` | GET/POST | Yes | Service records |
| `/tickets/<id>/service-records/<id>` | GET/DELETE | Yes | Single service record |
| `/tickets/<id>/service-records/<id>/status` | PUT | Yes | Update record status |
| `/assets/<id>/service-records` | GET | Yes | Asset service records |
| `/dashboard` | GET | Yes | Dashboard stats |
| `/health` | GET | No | Health check |
| `/debug/routes` | GET | No | List all routes |

**Total Endpoints: 65**

---

*Documentation generated for TrueLog Mobile API v1*
