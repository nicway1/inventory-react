# TrueLog Inline API Documentation

This document provides comprehensive documentation for all inline API endpoints (non-blueprint routes) in the TrueLog codebase that return JSON responses.

---

## Table of Contents

1. [API Simple Routes (`/api/v1/`)](#api-simple-routes-apiv1)
2. [JSON API Routes (`/json-api/`)](#json-api-routes-json-api)
3. [Admin Routes (`/admin/`)](#admin-routes-admin)
4. [Main Routes](#main-routes)
5. [Tickets Routes (`/tickets/`)](#tickets-routes-tickets)
6. [Inventory Routes (`/inventory/`)](#inventory-routes-inventory)
7. [Assets Routes (`/assets/`)](#assets-routes-assets)
8. [Search API Routes (`/search/`)](#search-api-routes-search)
9. [Inventory API Routes](#inventory-api-routes)
10. [Dashboard Routes (`/dashboard/`)](#dashboard-routes-dashboard)
11. [Shipments Routes (`/shipments/`)](#shipments-routes-shipments)
12. [Chatbot Routes (`/chatbot/`)](#chatbot-routes-chatbot)
13. [Documents Routes (`/documents/`)](#documents-routes-documents)
14. [Reports Routes (`/reports/`)](#reports-routes-reports)
15. [Development Routes (`/development/`)](#development-routes-development)
16. [Parcel Tracking Routes (`/parcel-tracking/`)](#parcel-tracking-routes-parcel-tracking)
17. [Knowledge Base Routes (`/knowledge/`)](#knowledge-base-routes-knowledge)
18. [Import Manager Routes (`/import-manager/`)](#import-manager-routes-import-manager)
19. [Action Items Routes (`/action-items/`)](#action-items-routes-action-items)
20. [SLA Routes (`/sla/`)](#sla-routes-sla)
21. [Intake Routes (`/intake/`)](#intake-routes-intake)

---

## API Simple Routes (`/api/v1/`)

File: `/Users/123456/inventory/routes/api_simple.py`

### Health Check

#### GET `/api/v1/health`
- **Description**: API health check endpoint
- **Authentication**: None required
- **Response**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00",
  "version": "1.0.0"
}
```

---

### Authentication Endpoints

#### POST `/api/v1/auth/login`
- **Description**: User authentication endpoint - accepts username/email and password, returns JWT token
- **Authentication**: None required
- **Request Parameters**:
  - `username` or `email` (string, required): User identifier
  - `password` (string, required): User password
- **Response**:
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "id": 1,
    "username": "user",
    "email": "user@example.com",
    "user_type": "ADMIN",
    "token": "jwt_token_here",
    "expires_at": "2024-01-02T00:00:00"
  }
}
```

#### GET `/api/v1/auth/verify`
- **Description**: Verify JWT token validity
- **Authentication**: Bearer token required
- **Response**:
```json
{
  "success": true,
  "data": {
    "user_id": 1,
    "username": "user",
    "user_type": "ADMIN",
    "expires_at": "2024-01-02T00:00:00",
    "valid": true
  }
}
```

#### POST `/api/v1/auth/refresh`
- **Description**: Refresh JWT token (allows refresh within 7 days of expiration)
- **Authentication**: Bearer token required
- **Response**:
```json
{
  "success": true,
  "data": {
    "token": "new_jwt_token",
    "expires_at": "2024-01-02T00:00:00",
    "user_id": 1,
    "username": "user"
  }
}
```

#### GET `/api/v1/auth/permissions`
- **Description**: Get current user's permissions and capabilities
- **Authentication**: Bearer token required
- **Response**:
```json
{
  "success": true,
  "data": {
    "user_id": 1,
    "username": "user",
    "user_type": "ADMIN",
    "permissions": ["tickets:read", "tickets:write", ...],
    "capabilities": {
      "can_create_tickets": true,
      "can_edit_tickets": true,
      ...
    },
    "company_id": 1,
    "assigned_country": "Singapore"
  }
}
```

#### GET `/api/v1/auth/profile`
- **Description**: Get current user's profile information
- **Authentication**: Bearer token required
- **Response**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "username": "user",
    "email": "user@example.com",
    "user_type": "ADMIN",
    "company_id": 1,
    "company_name": "Company Name",
    "assigned_country": "Singapore",
    "theme_preference": "light",
    "created_at": "2024-01-01T00:00:00",
    "last_login": "2024-01-01T12:00:00"
  }
}
```

---

### Ticket Endpoints

#### GET `/api/v1/tickets`
- **Description**: List tickets with filtering and pagination
- **Authentication**: API Key with `tickets:read` permission
- **Query Parameters**:
  - `page` (int, default: 1): Page number
  - `per_page` (int, default: 50, max: 100): Items per page
  - `queue_id` (int, optional): Filter by queue
  - `status` (string, optional): Filter by status
- **Response**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "subject": "Ticket Subject",
      "description": "Description",
      "status": "OPEN",
      "priority": "HIGH",
      "category": "ASSET_REPAIR",
      "queue_id": 1,
      "queue_name": "Queue Name",
      "customer_id": 1,
      "customer_name": "Customer Name",
      "customer_email": "customer@example.com",
      "assigned_to_id": 1,
      "assigned_to_name": "Assignee Name",
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00"
    }
  ],
  "meta": {
    "pagination": {
      "page": 1,
      "per_page": 50,
      "total": 100,
      "has_next": true,
      "has_prev": false
    }
  }
}
```

#### GET `/api/v1/tickets/<ticket_id>`
- **Description**: Get detailed information about a specific ticket
- **Authentication**: API Key with `tickets:read` permission
- **Response**: Full ticket details including customer phone, comments, attachments

#### POST `/api/v1/tickets/create`
- **Description**: Create a new ticket from mobile app (supports multiple categories)
- **Authentication**: Bearer token or X-API-Key + Bearer token
- **Request Parameters**:
  - `category` (string, required): Ticket category (ASSET_REPAIR, ASSET_CHECKOUT_CLAW, etc.)
  - `queue_id` (int, required): Queue ID
  - Additional fields vary by category
- **Response**:
```json
{
  "success": true,
  "message": "Ticket created successfully",
  "data": {
    "ticket_id": 1,
    "display_id": "TKT-000001",
    "subject": "Subject",
    "status": "open"
  }
}
```

#### GET `/api/v1/tickets/categories`
- **Description**: Get available ticket categories for mobile app
- **Authentication**: None required
- **Response**: List of ticket categories with required/optional fields

#### GET `/api/v1/tickets/<ticket_id>/comments`
- **Description**: Get all comments for a specific ticket
- **Authentication**: API Key with `tickets:read` permission
- **Query Parameters**:
  - `page` (int, default: 1)
  - `limit` (int, default: 20, max: 100)
- **Response**: Paginated list of comments

#### POST `/api/v1/tickets/<ticket_id>/comments`
- **Description**: Create a new comment on a specific ticket
- **Authentication**: API Key with `tickets:write` permission
- **Request Parameters**:
  - `content` (string, required): Comment content
  - `user_id` (int, required): User ID
- **Response**: Created comment data

---

### User Endpoints

#### GET `/api/v1/users`
- **Description**: List users with pagination
- **Authentication**: API Key with `users:read` permission
- **Query Parameters**:
  - `page` (int, default: 1)
  - `per_page` (int, default: 50, max: 100)
- **Response**: Paginated list of users

---

### Inventory Endpoints

#### GET `/api/v1/inventory`
- **Description**: List inventory items with pagination
- **Authentication**: API Key with `inventory:read` permission
- **Response**: Paginated list of inventory items with image URLs

#### GET `/api/v1/inventory/<item_id>`
- **Description**: Get detailed information about a specific inventory item
- **Authentication**: API Key with `inventory:read` permission
- **Response**: Full asset details including hardware specs, condition, location

---

### Queue Endpoints

#### GET `/api/v1/queues`
- **Description**: Get list of all available queues
- **Authentication**: API Key with `tickets:read` permission OR Bearer token
- **Response**: List of queues with id, name, description

---

### Company Endpoints

#### GET `/api/v1/companies`
- **Description**: Get all companies with parent/child hierarchy
- **Authentication**: None required (internal use)
- **Response**:
```json
{
  "success": true,
  "companies": [
    {
      "id": 1,
      "name": "Company Name",
      "display_name": "Display Name",
      "grouped_display_name": "Grouped Name",
      "is_parent_company": true,
      "parent_company_id": null,
      "parent_company_name": null
    }
  ]
}
```

---

### Accessory Endpoints

#### GET `/api/v1/accessories`
- **Description**: List accessories with pagination and filtering
- **Authentication**: Dual auth (API Key or Bearer token)
- **Query Parameters**:
  - `page`, `per_page`, `search`, `category`
- **Response**: Paginated list of accessories with image URLs

#### GET `/api/v1/accessories/<accessory_id>`
- **Description**: Get detailed information about a specific accessory
- **Authentication**: Dual auth (API Key or Bearer token)

---

### Asset Endpoints

#### GET `/api/v1/assets/next-tag`
- **Description**: Get next available asset tag for a given prefix
- **Authentication**: None required
- **Query Parameters**:
  - `prefix` (string, default: "SG-"): Asset tag prefix
- **Response**:
```json
{
  "success": true,
  "data": {
    "prefix": "SG-",
    "next_number": 1234,
    "next_tag": "SG-1234"
  }
}
```

#### POST `/api/v1/assets/bulk`
- **Description**: Bulk create assets from PDF extraction
- **Authentication**: None required
- **Request Body**:
```json
{
  "assets": [
    {
      "serial_number": "ABC123",
      "asset_tag": "SG-1234",
      "name": "MacBook Pro 14\"",
      ...
    }
  ],
  "ticket_id": 123
}
```

#### GET `/api/v1/assets/search`
- **Description**: Search assets by serial number or asset tag
- **Authentication**: Bearer token
- **Query Parameters**:
  - `q` or `search` (string, min 2 chars): Search query
  - `limit` (int, default: 20, max: 50)

---

### Customer Endpoints

#### GET `/api/v1/customers`
- **Description**: Get list of customers for ticket creation
- **Authentication**: Bearer token
- **Query Parameters**:
  - `page`, `per_page`, `search`, `company_id`
- **Response**: Paginated list of customers with company information

---

### Audit Endpoints

#### GET `/api/v1/audit/status`
- **Description**: Get current audit session status
- **Authentication**: Bearer token with `can_access_inventory_audit` permission
- **Response**: Active audit details or null

#### GET `/api/v1/audit/countries`
- **Description**: Get available countries for audit
- **Authentication**: Bearer token with `can_start_inventory_audit` permission
- **Response**: List of countries user can audit

#### POST `/api/v1/audit/start`
- **Description**: Start a new audit session
- **Authentication**: Bearer token with `can_start_inventory_audit` permission
- **Request Body**: `{"country": "SINGAPORE"}`

#### POST `/api/v1/audit/scan`
- **Description**: Scan an asset during audit
- **Authentication**: Bearer token with `can_access_inventory_audit` permission
- **Request Body**: `{"identifier": "asset_tag_or_serial"}`

#### POST `/api/v1/audit/end`
- **Description**: End the current audit session
- **Authentication**: Bearer token with `can_access_inventory_audit` permission

#### GET `/api/v1/audit/details/<detail_type>`
- **Description**: Get detailed asset lists from current audit
- **Authentication**: Bearer token with `can_access_inventory_audit` permission
- **Path Parameters**:
  - `detail_type`: `total`, `scanned`, `missing`, or `unexpected`

---

### Debug Endpoints

#### GET `/api/v1/debug/fix-ticket/<ticket_id>`
- **Description**: Debug endpoint to check and fix Asset Return ticket status
- **Authentication**: None required
- **Response**: Ticket debug information and fix status

---

## JSON API Routes (`/json-api/`)

File: `/Users/123456/inventory/routes/json_api.py`

### Authentication

#### POST `/json-api/auth/login`
- **Description**: JSON API login
- **Authentication**: None required
- **Response**: User info with JWT token

#### GET `/json-api/auth/me`
- **Description**: Get current authenticated user info
- **Authentication**: API Key or Bearer token

---

### Data Endpoints

#### GET `/json-api/tickets`
- **Description**: Get tickets list
- **Authentication**: API Key or Bearer token

#### GET `/json-api/inventory`
- **Description**: Get inventory list
- **Authentication**: API Key or Bearer token

#### GET `/json-api/dashboard`
- **Description**: Get dashboard data
- **Authentication**: API Key or Bearer token

---

### Development Endpoints

#### GET `/json-api/dev/dashboard`
- **Description**: Get development dashboard data
- **Authentication**: API Key or Bearer token (Developer access required)

#### GET `/json-api/dev/features`
- **Description**: Get feature requests list
- **Authentication**: Developer access required

#### GET `/json-api/dev/features/<feature_id>`
- **Description**: Get specific feature details
- **Authentication**: Developer access required

#### POST `/json-api/dev/features`
- **Description**: Create new feature request
- **Authentication**: Developer access required

#### PUT `/json-api/dev/features/<feature_id>`
- **Description**: Update feature request
- **Authentication**: Developer access required

#### POST `/json-api/dev/features/<feature_id>/status`
- **Description**: Update feature status
- **Authentication**: Developer access required

#### POST `/json-api/dev/features/<feature_id>/comment`
- **Description**: Add comment to feature
- **Authentication**: Developer access required

#### POST `/json-api/dev/features/<feature_id>/approve`
- **Description**: Approve feature request
- **Authentication**: Developer access required

#### POST `/json-api/dev/features/<feature_id>/reject`
- **Description**: Reject feature request
- **Authentication**: Developer access required

#### DELETE `/json-api/dev/features/<feature_id>`
- **Description**: Delete feature request
- **Authentication**: Developer access required

#### GET `/json-api/dev/bugs`
- **Description**: Get bugs list
- **Authentication**: Developer access required

#### GET `/json-api/dev/bugs/<bug_id>`
- **Description**: Get specific bug details
- **Authentication**: Developer access required

#### POST `/json-api/dev/bugs`
- **Description**: Create new bug report
- **Authentication**: Developer access required

#### PUT `/json-api/dev/bugs/<bug_id>`
- **Description**: Update bug report
- **Authentication**: Developer access required

#### POST `/json-api/dev/bugs/<bug_id>/status`
- **Description**: Update bug status
- **Authentication**: Developer access required

#### POST `/json-api/dev/bugs/<bug_id>/comment`
- **Description**: Add comment to bug
- **Authentication**: Developer access required

#### DELETE `/json-api/dev/bugs/<bug_id>`
- **Description**: Delete bug report
- **Authentication**: Developer access required

#### GET `/json-api/dev/releases`
- **Description**: Get releases list
- **Authentication**: Developer access required

#### GET `/json-api/dev/releases/<release_id>`
- **Description**: Get specific release details
- **Authentication**: Developer access required

#### POST `/json-api/dev/releases`
- **Description**: Create new release
- **Authentication**: Developer access required

#### PUT `/json-api/dev/releases/<release_id>`
- **Description**: Update release
- **Authentication**: Developer access required

#### POST `/json-api/dev/releases/<release_id>/status`
- **Description**: Update release status
- **Authentication**: Developer access required

#### GET `/json-api/dev/changelog`
- **Description**: Get changelog entries
- **Authentication**: Developer access required

#### GET `/json-api/dev/schedule`
- **Description**: Get work schedule
- **Authentication**: Developer access required

#### POST `/json-api/dev/schedule`
- **Description**: Update work schedule
- **Authentication**: Developer access required

#### GET `/json-api/dev/schedule/me`
- **Description**: Get current user's schedule
- **Authentication**: Developer access required

#### POST `/json-api/dev/schedule/bulk`
- **Description**: Bulk update schedule
- **Authentication**: Developer access required

#### POST `/json-api/dev/schedule/week`
- **Description**: Update week schedule
- **Authentication**: Developer access required

#### GET `/json-api/dev/schedule/<user_id>`
- **Description**: Get specific user's schedule
- **Authentication**: Developer access required

#### POST `/json-api/dev/schedule/delete`
- **Description**: Delete schedule entry
- **Authentication**: Developer access required

#### GET `/json-api/dev/work-plans`
- **Description**: Get work plans
- **Authentication**: Developer access required

#### GET `/json-api/dev/work-plans/<user_id>`
- **Description**: Get specific user's work plan
- **Authentication**: Developer access required

#### POST `/json-api/dev/work-plans`
- **Description**: Save work plan
- **Authentication**: Developer access required

#### GET `/json-api/dev/testers`
- **Description**: Get testers list
- **Authentication**: Developer access required

#### GET `/json-api/dev/meetings`
- **Description**: Get meetings list
- **Authentication**: Developer access required

#### POST `/json-api/dev/meetings`
- **Description**: Create new meeting
- **Authentication**: Developer access required

#### GET `/json-api/dev/meetings/<meeting_id>/action-items`
- **Description**: Get meeting action items
- **Authentication**: Developer access required

#### POST `/json-api/dev/action-items`
- **Description**: Create action item
- **Authentication**: Developer access required

#### PUT `/json-api/dev/action-items/<item_id>`
- **Description**: Update action item
- **Authentication**: Developer access required

#### POST `/json-api/dev/action-items/<item_id>/move`
- **Description**: Move action item status
- **Authentication**: Developer access required

#### DELETE `/json-api/dev/action-items/<item_id>`
- **Description**: Delete action item
- **Authentication**: Developer access required

#### GET `/json-api/dev/users`
- **Description**: Get development users
- **Authentication**: Developer access required

---

## Admin Routes (`/admin/`)

File: `/Users/123456/inventory/routes/admin.py`

### User Management API

#### GET `/admin/api/users/<user_id>/quick-details`
- **Description**: Get quick user details for modal display
- **Authentication**: Admin session required
- **Response**: User details including role, companies, countries

#### POST `/admin/api/users/<user_id>/countries`
- **Description**: Update user's country assignments
- **Authentication**: Admin session required
- **Request Body**: `{"countries": ["SG", "US"]}`

#### POST `/admin/api/users/<user_id>/companies`
- **Description**: Update user's company assignments
- **Authentication**: Admin session required
- **Request Body**: `{"company_ids": [1, 2, 3]}`

#### POST `/admin/api/users/<user_id>/queues`
- **Description**: Update user's queue assignments
- **Authentication**: Admin session required
- **Request Body**: `{"queue_ids": [1, 2, 3]}`

#### POST `/admin/api/users/<user_id>/mentions`
- **Description**: Update user's mention settings
- **Authentication**: Admin session required

---

### Permissions

#### POST `/admin/permissions/update`
- **Description**: Update user permission
- **Authentication**: Admin session required

---

### Notification User Groups

#### GET `/admin/notification-user-groups/<group_id>/members`
- **Description**: Get members of a notification user group
- **Authentication**: Admin session required
- **Response**: List of group members

---

### CSV Import API

#### POST `/admin/csv-import/upload`
- **Description**: Upload CSV file for import
- **Authentication**: Admin session with CSV Import permission
- **Response**: File ID, headers, preview data

#### GET `/admin/csv-import/load-data`
- **Description**: Load previously uploaded CSV data
- **Authentication**: Admin session with CSV Import permission
- **Query Parameters**: `file_id`

#### POST `/admin/csv-import/preview-ticket`
- **Description**: Preview ticket from CSV row
- **Authentication**: Admin session with CSV Import permission
- **Request Body**: `{"file_id": "...", "row_index": 0}`

#### POST `/admin/csv-import/import-ticket`
- **Description**: Import single ticket from CSV
- **Authentication**: Admin session with CSV Import permission

#### POST `/admin/csv-import/bulk-import`
- **Description**: Bulk import tickets from CSV
- **Authentication**: Admin session with CSV Import permission

---

### Asset Checkout Import API

#### POST `/admin/asset-checkout-import/upload`
- **Description**: Upload CSV for asset checkout import
- **Authentication**: Admin session with Import Asset Checkout permission

#### GET `/admin/asset-checkout-import/load-data`
- **Description**: Load asset checkout CSV data
- **Authentication**: Admin session with Import Asset Checkout permission

#### POST `/admin/asset-checkout-import/preview-ticket`
- **Description**: Preview asset checkout ticket
- **Authentication**: Admin session with Import Asset Checkout permission

#### POST `/admin/asset-checkout-import/import-ticket`
- **Description**: Import asset checkout ticket
- **Authentication**: Admin session with Import Asset Checkout permission

#### POST `/admin/asset-checkout-import/bulk-import`
- **Description**: Bulk import asset checkout tickets
- **Authentication**: Admin session with Import Asset Checkout permission

---

### Group Management API

#### POST `/admin/groups/create`
- **Description**: Create new user group
- **Authentication**: Admin session required
- **Request Body**: `{"name": "group-name"}`

#### POST `/admin/groups/update`
- **Description**: Update group name
- **Authentication**: Admin session required
- **Request Body**: `{"group_id": 1, "name": "new-name"}`

#### POST `/admin/groups/add-member`
- **Description**: Add member to group
- **Authentication**: Admin session required
- **Request Body**: `{"group_id": 1, "user_id": 2}`

#### POST `/admin/groups/remove-member`
- **Description**: Remove member from group
- **Authentication**: Admin session required

#### POST `/admin/groups/toggle-status`
- **Description**: Toggle group active status
- **Authentication**: Admin session required

#### POST `/admin/groups/delete`
- **Description**: Delete group
- **Authentication**: Admin session required

---

### Mention Suggestions

#### GET `/admin/api/mention-suggestions`
- **Description**: Get mention suggestions for autocomplete
- **Authentication**: Admin session required
- **Query Parameters**: `q` (search query)
- **Response**: List of user/group suggestions

---

### Ticket Status Management

#### GET `/admin/api/ticket-statuses`
- **Description**: Get all ticket statuses
- **Authentication**: Admin session required

#### POST `/admin/manage-ticket-statuses` (CREATE)
- **Description**: Create new ticket status
- **Authentication**: Admin session required

#### POST `/admin/manage-ticket-statuses` (UPDATE)
- **Description**: Update ticket status
- **Authentication**: Admin session required

#### POST `/admin/manage-ticket-statuses` (DELETE)
- **Description**: Delete ticket status
- **Authentication**: Admin session required

---

### User Cloning

#### GET `/admin/api/users-for-cloning`
- **Description**: Get users available for cloning
- **Authentication**: Unauthorized (admin only)
- **Response**: List of users for permission cloning

#### POST `/admin/mass-create-users`
- **Description**: Mass create users with cloned permissions
- **Authentication**: Unauthorized (admin only)

---

### Database Management

#### POST `/admin/database/backup`
- **Description**: Create database backup
- **Authentication**: Admin session required

#### GET `/admin/database/backups`
- **Description**: Get list of backups
- **Authentication**: Admin session required

#### POST `/admin/database/restore`
- **Description**: Restore from backup
- **Authentication**: Admin session required

---

### Billing Generator

#### POST `/admin/billing-generator/tickets`
- **Description**: Get tickets for billing
- **Authentication**: Admin session required

#### POST `/admin/billing-generator/generate`
- **Description**: Generate billing report
- **Authentication**: Admin session required

#### POST `/admin/billing-generator/export`
- **Description**: Export billing report
- **Authentication**: Admin session required

---

## Main Routes

File: `/Users/123456/inventory/routes/main.py`

#### GET `/debug-permissions`
- **Description**: Debug endpoint to view current user permissions
- **Authentication**: Session required
- **Response**: User permissions data

#### GET `/api/customers/search`
- **Description**: Search customers for autocomplete
- **Authentication**: Session required
- **Query Parameters**: `q` (search query)
- **Response**: List of matching customers

#### GET `/debug-supervisor-tickets`
- **Description**: Debug supervisor ticket access
- **Authentication**: Session required

---

## Tickets Routes (`/tickets/`)

File: `/Users/123456/inventory/routes/tickets.py`

#### POST `/tickets/refresh-all-statuses`
- **Description**: Refresh all ticket statuses
- **Authentication**: Session required

#### POST `/tickets/comments/<comment_id>/edit`
- **Description**: Edit a comment
- **Authentication**: Session required (own comments only)
- **Request Body**: `{"content": "Updated content"}`

#### POST `/tickets/comments/<comment_id>/delete`
- **Description**: Delete a comment
- **Authentication**: Session required (own comments only)

---

## Inventory Routes (`/inventory/`)

File: `/Users/123456/inventory/routes/inventory.py`

#### GET `/inventory/debug-permissions`
- **Description**: Debug inventory permissions
- **Authentication**: Session required

#### GET `/inventory/api/sf/filters`
- **Description**: Get filter options for inventory
- **Authentication**: Session required

#### GET `/inventory/api/sf/test`
- **Description**: Test endpoint
- **Authentication**: Session required

#### GET `/inventory/api/sf/assets`
- **Description**: Get assets with filters
- **Authentication**: Session required

#### GET `/inventory/api/sf/accessories`
- **Description**: Get accessories with filters
- **Authentication**: Session required

#### GET `/inventory/api/sf/chart-settings`
- **Description**: Get chart settings
- **Authentication**: Session required

#### POST `/inventory/api/sf/chart-settings`
- **Description**: Save chart settings
- **Authentication**: Session required

---

## Assets Routes (`/assets/`)

File: `/Users/123456/inventory/routes/assets.py`

#### POST `/assets/add`
- **Description**: Add new asset
- **Authentication**: Session required
- **Response**: Created asset data or error

#### POST `/assets/<asset_id>/unlink/<ticket_id>`
- **Description**: Unlink asset from ticket
- **Authentication**: Session required

#### GET `/assets/generate-barcode/<asset_id>`
- **Description**: Generate barcode for asset
- **Authentication**: Session required
- **Response**: Barcode image data

---

## Search API Routes (`/search/`)

File: `/Users/123456/inventory/routes/search_api.py`

#### GET `/search/global`
- **Description**: Global search across all entities
- **Authentication**: Session or API key required

#### GET `/search/assets`
- **Description**: Search assets
- **Authentication**: Session or API key required

#### GET `/search/accessories`
- **Description**: Search accessories
- **Authentication**: Session or API key required

#### GET `/search/suggestions`
- **Description**: Get search suggestions
- **Authentication**: Session or API key required

#### GET `/search/filters`
- **Description**: Get available filters
- **Authentication**: Session or API key required

#### GET `/search/health`
- **Description**: Search API health check
- **Authentication**: None required

---

## Inventory API Routes

File: `/Users/123456/inventory/routes/inventory_api.py`

#### GET `/inventory-api/inventory`
- **Description**: Get inventory items
- **Authentication**: Dual auth

#### GET `/inventory-api/inventory/<asset_id>`
- **Description**: Get specific inventory item
- **Authentication**: Dual auth

#### GET `/inventory-api/accessories`
- **Description**: Get accessories
- **Authentication**: Dual auth

#### GET `/inventory-api/accessories/<accessory_id>`
- **Description**: Get specific accessory
- **Authentication**: Dual auth

#### GET `/inventory-api/inventory/health`
- **Description**: Inventory API health check
- **Authentication**: None required

---

## Dashboard Routes (`/dashboard/`)

File: `/Users/123456/inventory/routes/dashboard.py`

#### POST `/dashboard/api/save-layout`
- **Description**: Save dashboard layout
- **Authentication**: Session required
- **Request Body**: Layout configuration array

#### GET `/dashboard/api/widget/<widget_id>/data`
- **Description**: Get widget data
- **Authentication**: Session required

#### POST `/dashboard/api/reset-layout`
- **Description**: Reset dashboard to default layout
- **Authentication**: Session required

---

## Shipments Routes (`/shipments/`)

File: `/Users/123456/inventory/routes/shipments.py`

#### GET `/shipments/api/history/<tracking_number>`
- **Description**: Get shipment history by tracking number
- **Authentication**: Session required

#### POST `/shipments/api/history/bulk`
- **Description**: Bulk track shipments
- **Authentication**: Session required
- **Request Body**: `{"tracking_numbers": ["...", "..."]}`

---

## Chatbot Routes (`/chatbot/`)

File: `/Users/123456/inventory/routes/chatbot.py`

#### POST `/chatbot/ask`
- **Description**: Ask chatbot a question
- **Authentication**: Session required
- **Request Body**: `{"message": "question"}`

#### POST `/chatbot/execute`
- **Description**: Execute chatbot action
- **Authentication**: Session required

#### GET `/chatbot/suggestions`
- **Description**: Get chatbot suggestions
- **Authentication**: Session required

#### GET `/chatbot/api/logs`
- **Description**: Get chatbot logs
- **Authentication**: Admin session required

#### GET `/chatbot/api/logs/export`
- **Description**: Export chatbot logs
- **Authentication**: Admin session required

#### POST `/chatbot/api/logs/feedback`
- **Description**: Submit feedback for chatbot log
- **Authentication**: Session required

---

### Mobile Chatbot Endpoints

#### POST `/chatbot/mobile/ask`
- **Description**: Mobile chatbot question
- **Authentication**: Bearer token required

#### POST `/chatbot/mobile/execute`
- **Description**: Mobile chatbot action
- **Authentication**: Bearer token required

#### GET `/chatbot/mobile/suggestions`
- **Description**: Mobile chatbot suggestions
- **Authentication**: Bearer token required

#### GET `/chatbot/mobile/history`
- **Description**: Mobile chatbot history
- **Authentication**: Bearer token required

#### GET `/chatbot/mobile/capabilities`
- **Description**: Get chatbot capabilities
- **Authentication**: None required

---

## Documents Routes (`/documents/`)

File: `/Users/123456/inventory/routes/documents.py`

#### POST `/documents/save-invoice`
- **Description**: Save invoice document
- **Authentication**: Session required
- **Response**: Invoice ID and filename

---

## Reports Routes (`/reports/`)

File: `/Users/123456/inventory/routes/reports.py`

#### GET `/reports/debug/unknown-models`
- **Description**: Debug unknown asset models
- **Authentication**: Session required

#### GET `/reports/api/filters`
- **Description**: Get report filters
- **Authentication**: Session required

#### POST `/reports/api/case-data`
- **Description**: Get case report data
- **Authentication**: Session required

#### POST `/reports/api/dashboard-data`
- **Description**: Get dashboard report data
- **Authentication**: Session required

#### POST `/reports/api/report-data`
- **Description**: Get custom report data
- **Authentication**: Session required

---

## Development Routes (`/development/`)

File: `/Users/123456/inventory/routes/development.py`

#### POST `/development/changelog/sync`
- **Description**: Sync changelog from git
- **Authentication**: Developer session required

#### GET `/development/changelog/api/entries`
- **Description**: Get changelog entries
- **Authentication**: Developer session required

#### POST `/development/features/<id>/delete-image`
- **Description**: Delete feature image
- **Authentication**: Developer session required

#### GET `/development/schedule/events`
- **Description**: Get schedule events
- **Authentication**: Developer session required

#### POST `/development/schedule/toggle`
- **Description**: Toggle schedule day
- **Authentication**: Developer session required

#### POST `/development/schedule/bulk`
- **Description**: Bulk update schedule
- **Authentication**: Developer session required

#### GET `/development/schedule/admin/events`
- **Description**: Get admin schedule events
- **Authentication**: Super Admin required

#### POST `/development/work-plan/save`
- **Description**: Save work plan
- **Authentication**: Developer session required

#### GET `/development/work-plan/get/<user_id>`
- **Description**: Get user work plan
- **Authentication**: Developer session required

#### GET `/development/analytics/api/sessions`
- **Description**: Get analytics sessions
- **Authentication**: Developer session required

#### GET `/development/analytics/api/active-users`
- **Description**: Get active users analytics
- **Authentication**: Developer session required

---

## Parcel Tracking Routes (`/parcel-tracking/`)

File: `/Users/123456/inventory/routes/parcel_tracking.py`

#### POST `/parcel-tracking/track`
- **Description**: Track a single parcel
- **Authentication**: Developer session required
- **Request Body**: `{"tracking_number": "..."}`

#### POST `/parcel-tracking/track/bulk`
- **Description**: Bulk track parcels
- **Authentication**: Developer session required

#### GET `/parcel-tracking/carriers`
- **Description**: Get supported carriers
- **Authentication**: Developer session required

#### GET `/parcel-tracking/status`
- **Description**: Get tracking API status
- **Authentication**: Developer session required

#### GET `/parcel-tracking/links/<tracking_number>`
- **Description**: Get tracking links
- **Authentication**: Developer session required

---

## Knowledge Base Routes (`/knowledge/`)

File: `/Users/123456/inventory/routes/knowledge.py`

#### GET `/knowledge/api/search-suggestions`
- **Description**: Get search suggestions
- **Authentication**: None required

#### POST `/knowledge/admin/process-pdf`
- **Description**: Process PDF for knowledge base
- **Authentication**: Admin session required

#### POST `/knowledge/admin/upload-image`
- **Description**: Upload image for article
- **Authentication**: Admin session required

---

## Import Manager Routes (`/import-manager/`)

File: `/Users/123456/inventory/routes/import_manager.py`

#### POST `/import-manager/api/create-session`
- **Description**: Create import session
- **Authentication**: Session required

#### POST `/import-manager/api/update-session/<session_id>`
- **Description**: Update import session
- **Authentication**: Session required

---

## Action Items Routes (`/action-items/`)

File: `/Users/123456/inventory/routes/action_items.py`

#### POST `/action-items/api/create`
- **Description**: Create action item
- **Authentication**: Developer session required

#### POST `/action-items/api/bulk-create`
- **Description**: Bulk create action items from text
- **Authentication**: Developer session required

#### POST `/action-items/api/update/<item_id>`
- **Description**: Update action item
- **Authentication**: Developer session required

#### POST `/action-items/api/move`
- **Description**: Move action item to different status
- **Authentication**: Developer session required

#### DELETE `/action-items/api/delete/<item_id>`
- **Description**: Delete action item
- **Authentication**: Developer session required

#### POST `/action-items/api/clear-done`
- **Description**: Clear completed action items
- **Authentication**: Developer session required

#### POST `/action-items/api/assign-tester`
- **Description**: Assign tester to action items
- **Authentication**: Developer session required

#### POST `/action-items/api/renumber`
- **Description**: Renumber action items
- **Authentication**: Developer session required

#### GET `/action-items/api/item/<item_id>`
- **Description**: Get specific action item
- **Authentication**: Developer session required

#### POST `/action-items/api/item/<item_id>/comments`
- **Description**: Add comment to action item
- **Authentication**: Developer session required

#### DELETE `/action-items/api/comments/<comment_id>`
- **Description**: Delete comment
- **Authentication**: Developer session required

#### GET `/action-items/api/meetings`
- **Description**: Get meetings list
- **Authentication**: Developer session required

#### POST `/action-items/api/meetings/create`
- **Description**: Create meeting
- **Authentication**: Developer session required

#### POST `/action-items/api/meetings/<meeting_id>`
- **Description**: Update meeting
- **Authentication**: Developer session required

#### POST `/action-items/api/meetings/<meeting_id>/select`
- **Description**: Select meeting as active
- **Authentication**: Developer session required

#### DELETE `/action-items/api/meetings/<meeting_id>`
- **Description**: Delete meeting
- **Authentication**: Developer session required

---

## SLA Routes (`/sla/`)

File: `/Users/123456/inventory/routes/sla.py`

#### GET `/sla/api/configs`
- **Description**: Get SLA configurations
- **Authentication**: Admin session required

#### POST `/sla/api/config`
- **Description**: Create/update SLA configuration
- **Authentication**: Admin session required

#### DELETE `/sla/api/config/<config_id>`
- **Description**: Delete SLA configuration
- **Authentication**: Admin session required

#### GET `/sla/api/holidays`
- **Description**: Get holidays list
- **Authentication**: Admin session required

#### POST `/sla/api/holiday`
- **Description**: Add holiday
- **Authentication**: Admin session required

#### DELETE `/sla/api/holiday/<holiday_id>`
- **Description**: Delete holiday
- **Authentication**: Admin session required

---

## Intake Routes (`/intake/`)

File: `/Users/123456/inventory/routes/intake.py`

#### GET `/intake/api/extract-pdf/<attachment_id>`
- **Description**: Extract data from PDF attachment
- **Authentication**: Session required
- **Response**: Extracted assets data from PDF

---

## Common Response Formats

### Success Response
```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": { ... }
}
```

### Error Response
```json
{
  "success": false,
  "error": "ERROR_CODE",
  "message": "Error description",
  "details": { ... }
}
```

### Paginated Response
```json
{
  "success": true,
  "data": [ ... ],
  "meta": {
    "pagination": {
      "page": 1,
      "per_page": 50,
      "total": 100,
      "pages": 2,
      "has_next": true,
      "has_prev": false,
      "next_page": 2,
      "prev_page": null
    }
  }
}
```

---

## Authentication Methods

### 1. API Key Authentication
- Header: `X-API-Key: your_api_key`
- Used for: External integrations, automated systems

### 2. JWT Bearer Token
- Header: `Authorization: Bearer your_jwt_token`
- Used for: Mobile apps, authenticated API access

### 3. Session Authentication
- Cookie-based session
- Used for: Web interface, admin operations

### 4. Dual Authentication
- Accepts either API Key or Bearer token
- Used for: Flexible endpoint access

---

## Error Codes

| Code | Description |
|------|-------------|
| `VALIDATION_ERROR` | Invalid input data |
| `RESOURCE_NOT_FOUND` | Requested resource doesn't exist |
| `MISSING_TOKEN` | Authentication token not provided |
| `INVALID_TOKEN` | Invalid authentication token |
| `TOKEN_EXPIRED` | Authentication token has expired |
| `INSUFFICIENT_PERMISSIONS` | User lacks required permissions |
| `INTERNAL_ERROR` | Server-side error |
| `ENDPOINT_NOT_FOUND` | API endpoint doesn't exist |
| `METHOD_NOT_ALLOWED` | HTTP method not supported |

---

*Documentation generated on 2026-02-06*
