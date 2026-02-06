# TrueLog API v2 Documentation

**Base URL:** `/api/v2`

**API Version:** 2.0.0

## Overview

The TrueLog API v2 provides a standardized RESTful interface for the React frontend migration. All endpoints follow consistent patterns for response formatting, error handling, pagination, sorting, and authentication.

---

## Authentication

All endpoints (except health check) require authentication via one of the following methods:

1. **Bearer Token (JWT)** - In Authorization header: `Authorization: Bearer <token>`
2. **API Key** - In X-API-Key header: `X-API-Key: <key>` combined with Bearer token
3. **Session-based** - For web users logged in via browser session

### Authentication Types by Endpoint

| Type | Description |
|------|-------------|
| `dual` | Supports both JWT and session authentication |
| `admin` | Requires SUPER_ADMIN or DEVELOPER user type |
| `super_admin` | Requires SUPER_ADMIN user type only |

---

## Response Format

### Success Response
```json
{
  "success": true,
  "data": <payload>,
  "message": "Optional success message",
  "meta": {
    "pagination": {...},
    "request_id": "...",
    "timestamp": "..."
  }
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": {...}
  }
}
```

### Pagination Meta
```json
{
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total_items": 100,
    "total_pages": 5,
    "has_next": true,
    "has_prev": false,
    "next_page": 2,
    "prev_page": null
  }
}
```

---

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `AUTHENTICATION_REQUIRED` | 401 | No valid authentication provided |
| `INVALID_TOKEN` | 401 | Invalid JWT token |
| `TOKEN_EXPIRED` | 401 | JWT token has expired |
| `PERMISSION_DENIED` | 403 | User lacks required permission |
| `INSUFFICIENT_PERMISSIONS` | 403 | Specific permission missing |
| `ADMIN_ACCESS_REQUIRED` | 403 | Admin-only endpoint |
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `MISSING_REQUIRED_FIELD` | 400 | Required field not provided |
| `INVALID_FIELD_VALUE` | 400 | Field value is invalid |
| `INVALID_JSON` | 400 | Request body is not valid JSON |
| `RESOURCE_NOT_FOUND` | 404 | Requested resource does not exist |
| `RESOURCE_ALREADY_EXISTS` | 409 | Resource with same identifier exists |
| `RESOURCE_IN_USE` | 409 | Resource cannot be deleted (in use) |
| `ENDPOINT_NOT_FOUND` | 404 | API endpoint does not exist |
| `METHOD_NOT_ALLOWED` | 405 | HTTP method not supported |
| `INTERNAL_ERROR` | 500 | Unexpected server error |
| `DATABASE_ERROR` | 500 | Database operation failed |

---

## Health Check

### GET /api/v2/health

Health check endpoint (no authentication required).

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "version": "2.0.0",
    "api_version": "v2",
    "timestamp": "2024-01-15T10:30:00Z"
  },
  "message": "API v2 is operational"
}
```

---

# Tickets Module

## List Tickets

### GET /api/v2/tickets

List tickets with pagination, filtering, sorting, and search.

**Authentication:** Dual (JWT/Session)

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `per_page` | int | 20 | Items per page (max: 100) |
| `sort` | string | created_at | Sort field (created_at, updated_at, priority, status, subject, id) |
| `order` | string | desc | Sort order (asc, desc) |
| `search` | string | - | Search in subject, ticket ID, customer name |
| `status` | string | - | Filter by status |
| `queue_id` | int | - | Filter by queue |
| `priority` | string | - | Filter by priority (Low, Medium, High, Critical) |
| `assigned_to_id` | int | - | Filter by assignee |
| `customer_id` | int | - | Filter by customer |
| `category` | string | - | Filter by category |
| `date_from` | ISO date | - | Created after date |
| `date_to` | ISO date | - | Created before date |

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 123,
      "display_id": "TICK-0123",
      "subject": "Laptop Issue",
      "status": "In Progress",
      "custom_status": null,
      "priority": "High",
      "category": "Hardware Issue",
      "queue": {"id": 1, "name": "IT Support"},
      "assigned_to": {"id": 5, "username": "john.doe"},
      "customer": {"id": 10, "name": "Jane Smith"},
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T14:00:00Z"
    }
  ],
  "meta": {
    "pagination": {...},
    "counts": {
      "total": 150,
      "new": 25,
      "in_progress": 50,
      "resolved": 70,
      "on_hold": 5
    }
  }
}
```

---

## Get Ticket Details

### GET /api/v2/tickets/{ticket_id}

Get comprehensive ticket details with all relationships.

**Authentication:** Dual (JWT/Session)

**Path Parameters:**
- `ticket_id` (int, required): Ticket ID

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 123,
    "display_id": "TICK-0123",
    "subject": "Laptop Issue",
    "description": "Screen flickering...",
    "status": "In Progress",
    "custom_status": null,
    "priority": "High",
    "category": "Hardware Issue",
    "category_display": "Hardware Issue",
    "queue": {"id": 1, "name": "IT Support", "description": "..."},
    "assigned_to": {"id": 5, "username": "john.doe", "email": "john@example.com"},
    "requester": {"id": 3, "username": "requester"},
    "customer": {"id": 10, "name": "Jane Smith", "email": "jane@example.com", "company": "Acme Inc"},
    "company": {"id": 2, "name": "Acme Inc"},
    "country": "Singapore",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T14:00:00Z",
    "shipping": {
      "tracking_number": "SG123456",
      "carrier": "SingPost",
      "address": "123 Main St",
      "status": "In Transit"
    },
    "assets": [
      {"id": 1, "asset_tag": "TL-0001", "serial_number": "ABC123", "model": "MacBook Pro", "name": "Dev Laptop", "status": "Deployed"}
    ],
    "accessories": [
      {"id": 1, "name": "USB-C Charger", "quantity": 1, "category": "Charger", "condition": "Good"}
    ],
    "packages": [],
    "attachments": [
      {"id": 1, "filename": "screenshot.png", "file_size": 102400, "file_type": "image/png", "uploaded_at": "2024-01-15T10:35:00Z"}
    ],
    "comments_count": 5,
    "attachments_count": 1,
    "sla": {
      "status": "on_track",
      "due_date": "2024-01-17T10:30:00Z",
      "remaining_hours": 48,
      "is_breached": false
    },
    "permissions": {
      "can_edit": true,
      "can_delete": false,
      "can_assign": true,
      "can_comment": true
    },
    "notes": "Internal notes...",
    "return_tracking": null,
    "return_carrier": null,
    "return_tracking_status": null
  }
}
```

---

## Create Ticket

### POST /api/v2/tickets

Create a new ticket.

**Authentication:** Dual (JWT/Session)

**Request Body:**
```json
{
  "subject": "Laptop screen issue",       // required
  "queue_id": 1,                          // required
  "description": "Screen flickering...",
  "category": "Hardware Issue",
  "priority": "High",                     // Low, Medium, High, Critical
  "customer_id": 10,
  "asset_id": 1,
  "shipping_address": "123 Main St",
  "shipping_tracking": "SG123456",
  "shipping_carrier": "SingPost",
  "country": "Singapore",
  "notes": "Internal notes",
  "assigned_to_id": 5
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "id": 124,
    "display_id": "TICK-0124",
    "subject": "Laptop screen issue",
    ...
  },
  "message": "Ticket TICK-0124 created successfully"
}
```

---

## Update Ticket

### PUT /api/v2/tickets/{ticket_id}

Update an existing ticket.

**Authentication:** Dual (JWT/Session)

**Path Parameters:**
- `ticket_id` (int, required): Ticket ID

**Request Body:**
```json
{
  "subject": "Updated subject",
  "description": "Updated description",
  "priority": "Critical",
  "queue_id": 2,
  "customer_id": 11,
  "asset_id": 2,
  "shipping_address": "456 New St",
  "shipping_tracking": "SG789012",
  "shipping_carrier": "DHL",
  "country": "Malaysia",
  "notes": "Updated notes"
}
```

**Response:**
```json
{
  "success": true,
  "data": {...},
  "message": "Ticket updated successfully"
}
```

---

## Assign Ticket

### POST /api/v2/tickets/{ticket_id}/assign

Assign a ticket to a user.

**Authentication:** Dual (JWT/Session)

**Path Parameters:**
- `ticket_id` (int, required): Ticket ID

**Request Body:**
```json
{
  "assigned_to_id": 5    // required
}
```

**Response:**
```json
{
  "success": true,
  "data": {...},
  "message": "Ticket assigned to john.doe"
}
```

---

## Change Ticket Status

### POST /api/v2/tickets/{ticket_id}/status

Change the status of a ticket.

**Authentication:** Dual (JWT/Session)

**Path Parameters:**
- `ticket_id` (int, required): Ticket ID

**Request Body:**
```json
{
  "status": "RESOLVED",          // NEW, IN_PROGRESS, PROCESSING, ON_HOLD, RESOLVED, RESOLVED_DELIVERED
  "custom_status": null          // or custom status string
}
```

**Response:**
```json
{
  "success": true,
  "data": {...},
  "message": "Ticket status changed to Resolved"
}
```

---

# Ticket Attachments Module

## List Attachments

### GET /api/v2/tickets/{ticket_id}/attachments

List all attachments for a ticket.

**Authentication:** Dual (JWT/Session)

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "ticket_id": 123,
      "filename": "document.pdf",
      "file_type": "application/pdf",
      "file_size": 102400,
      "uploaded_by": 5,
      "uploader_name": "john.doe",
      "created_at": "2024-01-15T10:35:00Z",
      "download_url": "/api/v2/tickets/123/attachments/1/download"
    }
  ],
  "message": "Found 1 attachment(s)"
}
```

---

## Upload Attachments

### POST /api/v2/tickets/{ticket_id}/attachments

Upload attachment(s) to a ticket.

**Authentication:** Dual (JWT/Session)

**Content-Type:** `multipart/form-data`

**Form Data:**
- `attachments`: File(s) to upload (can be multiple)

**Allowed File Types:** pdf, doc, docx, xls, xlsx, csv, txt, png, jpg, jpeg, gif, bmp, webp, zip, rar, 7z, tar, gz

**Maximum File Size:** 25 MB per file

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "uploaded": [
      {"id": 1, "filename": "document.pdf", ...}
    ],
    "count": 1,
    "errors": []
  },
  "message": "Successfully uploaded 1 file(s)"
}
```

---

## Get Attachment Metadata

### GET /api/v2/tickets/{ticket_id}/attachments/{attachment_id}

Get metadata for a single attachment.

**Authentication:** Dual (JWT/Session)

---

## Download Attachment

### GET /api/v2/tickets/{ticket_id}/attachments/{attachment_id}/download

Download an attachment file.

**Authentication:** Dual (JWT/Session)

**Query Parameters:**
- `inline` (bool, default: false): If true, display in browser instead of download

---

## Delete Attachment

### DELETE /api/v2/tickets/{ticket_id}/attachments/{attachment_id}

Delete an attachment.

**Authentication:** Dual (JWT/Session)

**Response:** 204 No Content

---

# Service Records Module

## List Service Records

### GET /api/v2/tickets/{ticket_id}/service-records

List service records for a ticket.

**Authentication:** Dual (JWT/Session)

**Query Parameters:**
- `page` (int): Page number
- `per_page` (int): Items per page
- `status` (string): Filter by status (Requested, In Progress, Completed)

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "request_id": "SR-001",
      "ticket_id": 123,
      "asset_id": 1,
      "asset_tag": "TL-0001",
      "service_type": "OS Reinstall",
      "description": "Reinstall Windows 11",
      "status": "In Progress",
      "requested_by_id": 5,
      "requested_by_name": "john.doe",
      "assigned_to_id": 6,
      "assigned_to_name": "tech.support",
      "completed_by_id": null,
      "completed_by_name": null,
      "completed_at": null,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "meta": {"pagination": {...}}
}
```

---

## Create Service Record

### POST /api/v2/tickets/{ticket_id}/service-records

Create a new service record for a ticket.

**Authentication:** Dual (JWT/Session)

**Request Body:**
```json
{
  "service_type": "OS Reinstall",    // required
  "description": "Reinstall Windows 11",
  "asset_id": 1,
  "assigned_to_id": 6
}
```

**Valid Service Types:** OS Reinstall, Hardware Repair, Screen Replacement, Battery Replacement, Keyboard Replacement, Data Backup, Data Wipe, Software Installation, Firmware Update, Diagnostic Test, Cleaning, Other

**Response (201 Created):**
```json
{
  "success": true,
  "data": {...},
  "message": "Service record SR-001 created successfully"
}
```

---

## Update Service Record

### PUT /api/v2/tickets/{ticket_id}/service-records/{record_id}

Update a service record.

**Authentication:** Dual (JWT/Session)

**Request Body:**
```json
{
  "service_type": "Hardware Repair",
  "description": "Replace RAM",
  "status": "Completed",              // Requested, In Progress, Completed
  "asset_id": 1,
  "assigned_to_id": 6
}
```

---

## Delete Service Record

### DELETE /api/v2/tickets/{ticket_id}/service-records/{record_id}

Delete a service record.

**Authentication:** Dual (JWT/Session)

**Response:** 204 No Content

---

# Assets Module

## Create Asset

### POST /api/v2/assets

Create a new asset.

**Authentication:** Dual (JWT/Session) + `can_edit_assets` permission

**Request Body:**
```json
{
  "asset_tag": "TL-0001",           // required (or serial_number)
  "serial_number": "ABC123456",     // required (or asset_tag)
  "name": "Developer Laptop",
  "model": "MacBook Pro 14",
  "manufacturer": "Apple",
  "asset_type": "Laptop",
  "category": "Computing",
  "status": "IN_STOCK",             // IN_STOCK, DEPLOYED, READY_TO_DEPLOY, REPAIR, ARCHIVED
  "condition": "Excellent",
  "country": "Singapore",
  "customer": "John Doe",
  "location_id": 1,
  "company_id": 2,
  "cost_price": 2500.00,
  "hardware_type": "Apple Silicon",
  "cpu_type": "M3 Pro",
  "cpu_cores": "12",
  "gpu_cores": "18",
  "memory": "18GB",
  "harddrive": "512GB SSD",
  "keyboard": "US Layout",
  "charger": "96W USB-C",
  "erased": "Yes",
  "diag": "Pass",
  "po": "PO-2024-001",
  "notes": "New purchase",
  "tech_notes": "Internal notes",
  "image_url": "/static/uploads/asset.jpg",
  "legal_hold": false,
  "receiving_date": "2024-01-15",
  "specifications": {}
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "asset_tag": "TL-0001",
    "serial_number": "ABC123456",
    ...
  },
  "message": "Asset created successfully"
}
```

---

## Update Asset

### PUT /api/v2/assets/{asset_id}

Update an existing asset.

**Authentication:** Dual (JWT/Session) + `can_edit_assets` permission

**Path Parameters:**
- `asset_id` (int, required): Asset ID

**Request Body:** Same as create (all fields optional)

---

## Delete Asset

### DELETE /api/v2/assets/{asset_id}

Delete or archive an asset.

**Authentication:** Dual (JWT/Session) + `can_edit_assets` permission

**Query Parameters:**
- `mode` (string): `archive` (default) or `delete` (permanent, admin only)

**Response:** 204 No Content

---

## Upload Asset Image

### POST /api/v2/assets/{asset_id}/image

Upload or update an asset's image.

**Authentication:** Dual (JWT/Session) + `can_edit_assets` permission

**Option 1 - File Upload:**
- Content-Type: `multipart/form-data`
- Form field: `image`

**Option 2 - URL:**
```json
{
  "image_url": "https://example.com/image.jpg"
}
```

**Allowed Extensions:** png, jpg, jpeg, gif, webp

**Max Size:** 5MB

**Response:**
```json
{
  "success": true,
  "data": {
    "image_url": "/static/uploads/assets/asset_1_abc123.jpg"
  },
  "message": "Image uploaded successfully"
}
```

---

## Transfer Asset

### POST /api/v2/assets/{asset_id}/transfer

Transfer an asset to a different customer.

**Authentication:** Dual (JWT/Session) + `can_edit_assets` permission

**Request Body:**
```json
{
  "customer_id": 5,                   // required
  "reason": "Employee transfer",
  "notes": "Transfer to new team",
  "effective_date": "2024-01-15"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "asset_tag": "TL-0001",
    "previous_customer": {"id": 3, "name": "John Doe"},
    "new_customer": {"id": 5, "name": "Jane Smith"},
    "transferred_at": "2024-01-15T10:30:00Z",
    "transferred_by": {"id": 1, "username": "admin"}
  },
  "message": "Asset transferred successfully"
}
```

---

# Accessories Module

## Create Accessory

### POST /api/v2/accessories

Create a new accessory.

**Authentication:** Dual (JWT/Session) + `can_edit_assets` permission

**Request Body:**
```json
{
  "name": "USB-C Charger",              // required
  "category": "Computer Accessories",   // required
  "manufacturer": "Apple",
  "model_no": "MX0J2AM/A",
  "total_quantity": 50,
  "country": "Singapore",
  "notes": "96W USB-C Power Adapter",
  "image_url": "/static/uploads/charger.jpg",
  "company_id": 2,
  "aliases": ["96W Charger", "Apple Charger"]
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "USB-C Charger",
    "category": "Computer Accessories",
    "manufacturer": "Apple",
    "model_no": "MX0J2AM/A",
    "total_quantity": 50,
    "available_quantity": 50,
    "checked_out_quantity": 0,
    ...
  },
  "message": "Accessory created successfully"
}
```

---

## Update Accessory

### PUT /api/v2/accessories/{accessory_id}

Update an existing accessory.

**Authentication:** Dual (JWT/Session) + `can_edit_assets` permission

---

## Delete Accessory

### DELETE /api/v2/accessories/{accessory_id}

Delete an accessory.

**Authentication:** Dual (JWT/Session) + Admin privileges

**Note:** Will fail if items are checked out.

**Response:** 204 No Content

---

## Return Accessory

### POST /api/v2/accessories/{accessory_id}/return

Return a checked-out accessory to inventory.

**Authentication:** Dual (JWT/Session) + `can_edit_assets` permission

**Request Body:**
```json
{
  "quantity": 1,
  "customer_id": 5,
  "notes": "Good condition"
}
```

---

## Check-in Accessory

### POST /api/v2/accessories/{accessory_id}/checkin

Check-in (return) an accessory from a specific customer.

**Authentication:** Dual (JWT/Session) + `can_edit_assets` permission

**Request Body:**
```json
{
  "customer_id": 5,          // required
  "quantity": 1,
  "condition": "Good",
  "notes": "Returned in good condition",
  "ticket_id": 123
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "accessory": {
      "id": 1,
      "name": "USB-C Charger",
      "available_quantity": 15,
      "total_quantity": 20
    },
    "customer": {"id": 5, "name": "Jane Smith"},
    "quantity_returned": 1,
    "condition": "Good",
    "transaction_id": 150,
    "checked_in_at": "2024-01-15T10:30:00Z"
  },
  "message": "Accessory checked in successfully"
}
```

---

# Customers Module

## List Customers

### GET /api/v2/customers

List customers with pagination and search.

**Authentication:** Dual (JWT/Session)

**Query Parameters:**
- `page` (int): Page number
- `per_page` (int): Items per page (max: 100)
- `search` (string): Search in name, email, contact number, address
- `company_id` (int): Filter by company
- `country` (string): Filter by country
- `sort` (string): Sort field (name, email, created_at, updated_at, country)
- `order` (string): asc or desc

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "John Doe",
      "contact_number": "+65 9123 4567",
      "email": "john@example.com",
      "address": "123 Main St, Singapore",
      "company_id": 2,
      "company_name": "ACME Inc",
      "country": "SINGAPORE",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ],
  "meta": {"pagination": {...}}
}
```

---

## Create Customer

### POST /api/v2/customers

Create a new customer.

**Authentication:** Dual (JWT/Session)

**Request Body:**
```json
{
  "name": "John Doe",              // required
  "contact_number": "+65 9123 4567", // required
  "address": "123 Main St",        // required
  "country": "SINGAPORE",          // required
  "email": "john@example.com",
  "company_id": 2
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {...},
  "message": "Customer created successfully"
}
```

---

## Get Customer

### GET /api/v2/customers/{customer_id}

Get a single customer by ID.

**Authentication:** Dual (JWT/Session)

---

## Update Customer

### PUT /api/v2/customers/{customer_id}

Update an existing customer.

**Authentication:** Dual (JWT/Session)

**Request Body:** Same as create (all fields optional)

---

## Delete Customer

### DELETE /api/v2/customers/{customer_id}

Delete a customer.

**Authentication:** Dual (JWT/Session)

**Note:** Cannot delete customers with assigned assets, accessories, or tickets.

**Response:** 204 No Content

---

## Get Customer Tickets

### GET /api/v2/customers/{customer_id}/tickets

Get all tickets associated with a customer.

**Authentication:** Dual (JWT/Session)

**Query Parameters:**
- `page` (int): Page number
- `per_page` (int): Items per page
- `status` (string): Filter by status
- `sort` (string): Sort field (created_at, updated_at, status, subject)
- `order` (string): asc or desc

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 123,
      "display_id": "TICK-0123",
      "subject": "Asset Request",
      "status": "Resolved",
      "category": "Asset Checkout",
      "created_at": "2024-01-15T10:30:00Z",
      "resolved_at": "2024-01-16T14:00:00Z",
      "assets_count": 2,
      "assigned_to": {"id": 5, "username": "support.agent"}
    }
  ],
  "meta": {
    "pagination": {...},
    "counts": {
      "total": 25,
      "open": 3,
      "resolved": 22
    }
  }
}
```

---

# Admin Module

All admin endpoints require SUPER_ADMIN or DEVELOPER user type.

## User Management

### GET /api/v2/admin/users

List all users with pagination and sorting.

**Authentication:** Admin required

**Query Parameters:**
- `page`, `per_page`: Pagination
- `sort`: id, username, email, user_type, created_at, updated_at
- `order`: asc, desc
- `search`: Search in username/email
- `user_type`: Filter by type (SUPER_ADMIN, DEVELOPER, COUNTRY_ADMIN, SUPERVISOR, CLIENT)
- `company_id`: Filter by company
- `include_deleted`: Include soft-deleted users (default: false)

---

### POST /api/v2/admin/users

Create a new user.

**Authentication:** Admin required

**Request Body:**
```json
{
  "username": "john.doe",           // required
  "email": "john@example.com",      // required
  "password": "SecurePass123!",     // required
  "user_type": "SUPERVISOR",        // required
  "company_id": 2,
  "assigned_country": "Singapore"
}
```

---

### PUT /api/v2/admin/users/{user_id}

Update an existing user.

**Authentication:** Admin required

---

### DELETE /api/v2/admin/users/{user_id}

Delete (soft-delete) a user.

**Authentication:** Admin required

**Query Parameters:**
- `permanent`: If 'true', permanently delete (only for already soft-deleted users)

---

## Company Management

### GET /api/v2/admin/companies

List all companies.

**Authentication:** Admin required

**Query Parameters:**
- `page`, `per_page`: Pagination
- `sort`: id, name, created_at, updated_at
- `order`: asc, desc
- `search`: Search by name
- `parent_only`: Show only parent/standalone companies

---

### POST /api/v2/admin/companies

Create a new company.

**Authentication:** Admin required

**Request Body:**
```json
{
  "name": "ACME Inc",               // required
  "description": "Technology company",
  "address": "123 Business Park",
  "contact_name": "John Manager",
  "contact_email": "contact@acme.com",
  "parent_company_id": null,
  "display_name": "ACME",
  "is_parent_company": false
}
```

---

### PUT /api/v2/admin/companies/{company_id}

Update a company.

**Authentication:** Admin required

---

### DELETE /api/v2/admin/companies/{company_id}

Delete a company.

**Authentication:** Admin required

**Note:** Cannot delete companies with associated users or child companies.

---

## Queue Management

### GET /api/v2/admin/queues

List all queues.

**Authentication:** Admin required

---

### POST /api/v2/admin/queues

Create a new queue.

**Authentication:** Admin required

**Request Body:**
```json
{
  "name": "IT Support",             // required
  "description": "General IT issues",
  "folder_id": 1,
  "display_order": 0
}
```

---

### PUT /api/v2/admin/queues/{queue_id}

Update a queue.

**Authentication:** Admin required

---

### DELETE /api/v2/admin/queues/{queue_id}

Delete a queue.

**Authentication:** Admin required

**Note:** Cannot delete queues with associated tickets.

---

## Ticket Category Management

### GET /api/v2/admin/ticket-categories

List all ticket categories.

**Authentication:** Admin required

**Query Parameters:**
- `page`, `per_page`: Pagination
- `type`: predefined, custom, or all
- `enabled_only`: If 'true', only show enabled categories

---

### POST /api/v2/admin/ticket-categories

Create a custom ticket category.

**Authentication:** Admin required

**Request Body:**
```json
{
  "category_key": "HARDWARE_UPGRADE",    // required
  "display_name": "Hardware Upgrade",    // required
  "is_enabled": true,
  "is_predefined": false,
  "sort_order": 10
}
```

---

### PUT /api/v2/admin/ticket-categories/{category_id}

Update a ticket category display configuration.

**Authentication:** Admin required

---

### DELETE /api/v2/admin/ticket-categories/{category_id}

Delete a ticket category configuration.

**Authentication:** Admin required

**Note:** Predefined categories can only be disabled, not deleted.

---

# API Key Management Module

All API key endpoints require SUPER_ADMIN user type.

## List API Keys

### GET /api/v2/admin/api-keys

List all API keys.

**Authentication:** Super Admin required

**Query Parameters:**
- `page`, `per_page`: Pagination
- `status`: active, revoked, or expired
- `search`: Search by name or key prefix

---

## Create API Key

### POST /api/v2/admin/api-keys

Create a new API key.

**Authentication:** Super Admin required

**Request Body:**
```json
{
  "name": "Mobile App Key",          // required
  "permissions": ["tickets:read", "tickets:write", "inventory:read"],
  "expires_in_days": 365
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "Mobile App Key",
    "key": "tl_abc123def456...",     // Only shown once!
    "key_prefix": "tl_abc123de...",
    "permissions": [...],
    "expires_at": "2025-01-15T10:30:00Z"
  },
  "message": "API key created. Save this key - it won't be shown again."
}
```

---

## Get API Key

### GET /api/v2/admin/api-keys/{key_id}

Get API key details with usage stats.

**Authentication:** Super Admin required

---

## Update API Key

### PUT /api/v2/admin/api-keys/{key_id}

Update an API key.

**Authentication:** Super Admin required

**Request Body:**
```json
{
  "name": "Updated Name",
  "permissions": ["tickets:*", "inventory:*"],
  "extend_days": 90
}
```

---

## Revoke API Key

### DELETE /api/v2/admin/api-keys/{key_id}

Revoke (soft delete) an API key.

**Authentication:** Super Admin required

**Response:** 204 No Content

---

## Get API Key Usage

### GET /api/v2/admin/api-keys/{key_id}/usage

Get detailed usage statistics for an API key.

**Authentication:** Super Admin required

**Query Parameters:**
- `days` (int, default: 30, max: 365): Days to look back

---

## Get Available Permissions

### GET /api/v2/admin/api-keys/permissions

Get list of available permissions and permission groups.

**Authentication:** Super Admin required

---

# System Settings Module

## Get System Settings

### GET /api/v2/admin/system-settings

Get all system settings.

**Authentication:** Admin required

**Response:**
```json
{
  "success": true,
  "data": {
    "general": {
      "default_homepage": "dashboard",
      "default_ticket_view": "sf",
      "default_inventory_view": "sf",
      "system_timezone": "Asia/Singapore"
    },
    "email": {
      "smtp_enabled": true,
      "from_email": "support@example.com",
      "ms365_oauth_configured": true
    },
    "features": {
      "chatbot_enabled": true,
      "sla_enabled": true,
      "audit_enabled": true
    },
    "issue_types": [
      {"id": 1, "name": "Hardware Issue", "is_active": true, "usage_count": 150}
    ]
  }
}
```

---

## Update System Settings

### PUT /api/v2/admin/system-settings

Update system settings.

**Authentication:** Admin required

**Request Body:**
```json
{
  "general": {
    "default_homepage": "tickets",
    "default_ticket_view": "sf",
    "default_inventory_view": "sf",
    "system_timezone": "UTC"
  },
  "features": {
    "chatbot_enabled": true,
    "sla_enabled": false,
    "audit_enabled": true
  }
}
```

**Note:** Email settings cannot be updated via API (require environment changes).

---

## Issue Types

### GET /api/v2/admin/system-settings/issue-types

List all issue types.

**Authentication:** Admin required

**Query Parameters:**
- `active_only` (bool): Only return active issue types

---

### POST /api/v2/admin/system-settings/issue-types

Create a new custom issue type.

**Authentication:** Admin required

**Request Body:**
```json
{
  "name": "Hardware Issue",          // required
  "is_active": true
}
```

---

### PUT /api/v2/admin/system-settings/issue-types/{issue_type_id}

Update an issue type.

**Authentication:** Admin required

---

### DELETE /api/v2/admin/system-settings/issue-types/{issue_type_id}

Delete an issue type.

**Authentication:** Admin required

---

# User Preferences Module

## Get Preferences

### GET /api/v2/user/preferences

Get current user's preferences.

**Authentication:** Dual (JWT/Session)

**Response:**
```json
{
  "success": true,
  "data": {
    "theme": {
      "mode": "light",
      "primary_color": "#1976D2",
      "sidebar_style": "expanded"
    },
    "layout": {
      "default_homepage": "dashboard",
      "default_ticket_view": "sf",
      "default_inventory_view": "sf",
      "sidebar_collapsed": false,
      "compact_mode": false
    },
    "notifications": {
      "email_enabled": true,
      "in_app_enabled": true,
      "sound_enabled": false
    }
  }
}
```

---

## Update Preferences

### PUT /api/v2/user/preferences

Update current user's preferences (partial update supported).

**Authentication:** Dual (JWT/Session)

**Request Body:**
```json
{
  "theme": {
    "mode": "dark",
    "primary_color": "#4CAF50"
  },
  "layout": {
    "sidebar_collapsed": true
  },
  "notifications": {
    "sound_enabled": true
  }
}
```

---

## Get Preference Options

### GET /api/v2/user/preferences/options

Get available theme and layout options.

**Authentication:** Dual (JWT/Session)

**Response:**
```json
{
  "success": true,
  "data": {
    "theme_modes": ["light", "dark", "auto"],
    "primary_colors": [
      {"name": "Blue", "value": "#1976D2"},
      {"name": "Green", "value": "#4CAF50"},
      ...
    ],
    "sidebar_styles": ["expanded", "compact", "hidden"],
    "homepage_options": ["dashboard", "tickets", "inventory"],
    "view_options": ["classic", "sf"]
  }
}
```

---

# Dashboard Module

## List Dashboard Widgets

### GET /api/v2/dashboard/widgets

List all available dashboard widgets.

**Authentication:** Dual (JWT/Session)

**Query Parameters:**
- `category` (string): Filter by category (stats, charts, lists, actions, system)
- `include_all` (bool): Include widgets user doesn't have access to

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "inventory_stats",
      "name": "Inventory Statistics",
      "description": "Total asset and accessory counts",
      "category": "stats",
      "icon": "laptop",
      "color": "#2196F3",
      "default_size": {"w": 2, "h": 1},
      "min_size": {"w": 1, "h": 1},
      "max_size": {"w": 4, "h": 1},
      "config_options": [],
      "permissions": [],
      "refreshable": true,
      "configurable": false,
      "has_access": true
    }
  ],
  "meta": {
    "categories": [...],
    "total_available": 10,
    "total_widgets": 15
  }
}
```

---

## Get Widget Data

### GET /api/v2/dashboard/widgets/{widget_id}/data

Get data for a specific dashboard widget.

**Authentication:** Dual (JWT/Session)

**Query Parameters:**
- `config` (JSON string): Widget configuration options

**Response:**
```json
{
  "success": true,
  "data": {
    "widget_id": "ticket_stats",
    "generated_at": "2024-01-15T10:30:00Z",
    "values": {
      "total": 150,
      "open": 25,
      "in_progress": 50,
      "resolved": 75
    },
    "chart_data": {
      "labels": ["Open", "In Progress", "Resolved"],
      "values": [25, 50, 75],
      "colors": ["#F44336", "#FF9800", "#4CAF50"]
    }
  }
}
```

---

# Reports Module

## List Report Templates

### GET /api/v2/reports/templates

List all available report templates.

**Authentication:** Dual (JWT/Session)

**Query Parameters:**
- `category` (string): Filter by category (tickets, inventory, users, analytics)

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "ticket_summary",
      "name": "Ticket Summary Report",
      "description": "Summary of tickets by status, queue, and priority",
      "category": "tickets",
      "icon": "file-text",
      "parameters": [
        {"key": "date_from", "type": "date", "label": "From Date", "required": true},
        {"key": "date_to", "type": "date", "label": "To Date", "required": true},
        {"key": "queue_ids", "type": "multi_select", "label": "Queues", "required": false},
        {"key": "group_by", "type": "select", "label": "Group By", "options": ["status", "queue", "priority", "category"], "default": "status"}
      ],
      "output_formats": ["json", "csv", "pdf"],
      "permissions": ["reports:read"]
    }
  ],
  "meta": {
    "categories": [
      {"id": "tickets", "name": "Ticket Reports"},
      {"id": "inventory", "name": "Inventory Reports"},
      {"id": "users", "name": "User Reports"},
      {"id": "analytics", "name": "Analytics"}
    ],
    "total_templates": 7
  }
}
```

---

## Generate Report

### POST /api/v2/reports/generate

Generate a report based on template and parameters.

**Authentication:** Dual (JWT/Session)

**Request Body:**
```json
{
  "template_id": "ticket_summary",   // required
  "parameters": {
    "date_from": "2024-01-01",
    "date_to": "2024-01-31",
    "queue_ids": [1, 2],
    "group_by": "status"
  },
  "format": "json"                   // json, csv, pdf
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "report_id": "rpt_abc123def456",
    "template": "ticket_summary",
    "template_name": "Ticket Summary Report",
    "generated_at": "2024-01-15T10:30:00Z",
    "parameters": {...},
    "format": "json",
    "summary": {
      "total_tickets": 150,
      "date_range": "Jan 01, 2024 - Jan 31, 2024",
      "group_by": "status"
    },
    "data": [
      {"status": "Resolved", "count": 75, "percentage": 50.0},
      {"status": "In Progress", "count": 50, "percentage": 33.3},
      {"status": "New", "count": 25, "percentage": 16.7}
    ],
    "charts": [
      {
        "type": "pie",
        "title": "Tickets by Status",
        "data": {
          "labels": ["Resolved", "In Progress", "New"],
          "values": [75, 50, 25]
        }
      }
    ]
  },
  "message": "Report generated successfully: Ticket Summary Report"
}
```

### Available Report Templates

| Template ID | Name | Description |
|-------------|------|-------------|
| `ticket_summary` | Ticket Summary Report | Summary of tickets by status, queue, and priority |
| `ticket_resolution_time` | Ticket Resolution Time Report | Average resolution time by category and queue |
| `asset_inventory` | Asset Inventory Report | Complete asset inventory with status and assignments |
| `asset_by_status` | Assets by Status Report | Asset breakdown by status with counts and percentages |
| `asset_age_distribution` | Asset Age Distribution Report | Distribution of asset ages for lifecycle planning |
| `user_activity` | User Activity Report | User ticket activity and workload analysis |
| `customer_tickets` | Customer Ticket Report | Ticket volume and trends by customer/company |

---

# Endpoint Summary

## Total Endpoints: 67

### By Module

| Module | Endpoints |
|--------|-----------|
| Health | 1 |
| Tickets | 6 |
| Attachments | 5 |
| Service Records | 4 |
| Assets | 5 |
| Accessories | 5 |
| Customers | 6 |
| Admin - Users | 4 |
| Admin - Companies | 4 |
| Admin - Queues | 4 |
| Admin - Categories | 4 |
| API Keys | 7 |
| System Settings | 6 |
| User Preferences | 3 |
| Dashboard | 2 |
| Reports | 2 |

### By HTTP Method

| Method | Count |
|--------|-------|
| GET | 31 |
| POST | 22 |
| PUT | 10 |
| DELETE | 9 |

---

*Generated: 2024*

*API Version: 2.0.0*
