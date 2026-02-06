# iOS App Feature Implementation - Master Prompt

## Context

You are an iOS developer agent tasked with implementing missing features in the TrueLog Inventory iOS app. The app is built with **SwiftUI** and uses **100% native Apple frameworks** (no third-party dependencies).

---

## Current Architecture

### Authentication
- **API Key**: `X-API-Key` header (stored in AppConfig.swift)
- **JWT Token**: `Bearer` token stored in iOS Keychain (30-day expiry)
- **Base URLs**:
  - Production: `https://inventory.truelog.com.sg`
  - Testing: `https://www.truelog.site`

### Networking Pattern
The app uses URLSession with a centralized API client. All requests should:
1. Include `X-API-Key` header
2. Include `Authorization: Bearer {token}` header
3. Use JSON content type for request/response bodies
4. Handle standard error response format:
```json
{
  "success": false,
  "error": "ERROR_CODE",
  "message": "Human readable message"
}
```

### Success Response Format
```json
{
  "success": true,
  "data": { ... },
  "message": "Optional success message"
}
```

---

## Features to Implement

### Phase 1: HIGH PRIORITY - Ticket Workflow (6 features)

#### 1.1 Edit Ticket
- **Endpoint**: `PUT /api/v2/tickets/{ticket_id}`
- **Purpose**: Allow users to modify ticket details (subject, description, priority, notes)
- **Request Body**:
```json
{
  "subject": "string (optional)",
  "description": "string (optional)",
  "priority": "LOW|MEDIUM|HIGH|URGENT (optional)",
  "notes": "string (optional)",
  "queue_id": "integer (optional)",
  "customer_id": "integer (optional)"
}
```
- **UI Requirements**:
  - Add "Edit" button to ticket detail view
  - Create edit form with pre-populated fields
  - Show loading state during save
  - Return to detail view on success with updated data

#### 1.2 Change Ticket Status
- **Endpoint**: `POST /api/v2/tickets/{ticket_id}/status`
- **Purpose**: Change ticket status (NEW, IN_PROGRESS, PROCESSING, ON_HOLD, RESOLVED, RESOLVED_DELIVERED)
- **Request Body**:
```json
{
  "status": "NEW|IN_PROGRESS|PROCESSING|ON_HOLD|RESOLVED|RESOLVED_DELIVERED",
  "custom_status": "string (optional)"
}
```
- **UI Requirements**:
  - Add status picker/dropdown to ticket detail view
  - Show confirmation before status change
  - Update UI immediately on success
  - Support custom statuses if available

#### 1.3 Assign Ticket
- **Endpoint**: `POST /api/v2/tickets/{ticket_id}/assign`
- **Purpose**: Assign ticket to a user
- **Request Body**:
```json
{
  "assigned_to_id": "integer (required)"
}
```
- **Dependencies**: Requires user list from `GET /api/v1/users`
- **UI Requirements**:
  - Add "Assign" button or user picker
  - Show searchable user list
  - Display current assignee
  - Update ticket detail on success

#### 1.4 Delete Ticket
- **Endpoint**: `DELETE /api/v2/tickets/{ticket_id}`
- **Purpose**: Delete a ticket (with confirmation)
- **UI Requirements**:
  - Add delete option (swipe action or menu)
  - Show confirmation alert with ticket subject
  - Navigate back to ticket list on success
  - Remove from local cache

#### 1.5 Edit Comment
- **Endpoint**: `PUT /api/v2/tickets/{ticket_id}/comments/{comment_id}` (NOTE: May need to use existing endpoint or build)
- **Alternative**: Check if `/api/v1/tickets/{id}/comments/{cid}` supports PUT
- **Request Body**:
```json
{
  "content": "string (required)"
}
```
- **UI Requirements**:
  - Add edit button to own comments only
  - Show inline edit or modal editor
  - Preserve @mentions formatting

#### 1.6 Delete Comment
- **Endpoint**: `DELETE /api/v2/tickets/{ticket_id}/comments/{comment_id}` (NOTE: May need to use existing endpoint or build)
- **Alternative**: Check if `/api/v1/tickets/{id}/comments/{cid}` supports DELETE
- **UI Requirements**:
  - Add delete option to own comments only
  - Show confirmation
  - Remove from comment list on success

---

### Phase 2: MEDIUM PRIORITY - Asset Management (3 features)

#### 2.1 Edit Asset
- **Endpoint**: `PUT /api/v2/assets/{asset_id}`
- **Purpose**: Modify existing asset details
- **Request Body**:
```json
{
  "name": "string",
  "model": "string",
  "serial_num": "string",
  "asset_tag": "string",
  "status": "IN_STOCK|DEPLOYED|READY_TO_DEPLOY|REPAIR|ARCHIVED|DISPOSED",
  "condition": "NEW|GOOD|FAIR|POOR",
  "manufacturer": "string",
  "asset_type": "string",
  "cpu_type": "string",
  "cpu_cores": "string",
  "memory": "string",
  "harddrive": "string",
  "country": "string",
  "customer": "string",
  "notes": "string",
  "tech_notes": "string",
  "is_erased": "boolean",
  "has_keyboard": "boolean",
  "has_charger": "boolean"
}
```
- **UI Requirements**:
  - Add "Edit" button to asset detail view
  - Reuse asset creation form with pre-populated data
  - Support image update

#### 2.2 Delete/Archive Asset
- **Endpoint**: `DELETE /api/v2/assets/{asset_id}?mode=archive` (or `mode=delete` for permanent)
- **Purpose**: Archive or permanently delete an asset
- **UI Requirements**:
  - Add delete/archive option
  - Default to archive mode
  - Show confirmation with asset tag
  - Remove from list on success

#### 2.3 Transfer Asset
- **Endpoint**: `POST /api/v2/assets/{asset_id}/transfer`
- **Purpose**: Transfer asset to different customer
- **Request Body**:
```json
{
  "customer_id": "integer (required)",
  "reason": "string (optional)",
  "notes": "string (optional)",
  "effective_date": "YYYY-MM-DD (optional)"
}
```
- **Dependencies**: Requires customer list/search
- **UI Requirements**:
  - Add "Transfer" button to asset detail
  - Show customer picker with search
  - Optional reason/notes fields
  - Update asset detail on success

---

### Phase 3: MEDIUM PRIORITY - Accessory Management (5 features)

#### 3.1 Create Accessory
- **Endpoint**: `POST /api/v2/accessories`
- **Request Body**:
```json
{
  "name": "string (required)",
  "category": "string (required)",
  "manufacturer": "string",
  "model_no": "string",
  "total_quantity": "integer",
  "country": "string",
  "notes": "string",
  "image_url": "string",
  "company_id": "integer"
}
```
- **UI Requirements**:
  - Add "Create Accessory" button to accessories list
  - Form with required/optional fields
  - Support image upload
  - Navigate to detail on success

#### 3.2 Edit Accessory
- **Endpoint**: `PUT /api/v2/accessories/{accessory_id}`
- **Request Body**: Same as create (all fields optional)
- **UI Requirements**:
  - Add "Edit" button to accessory detail
  - Pre-populate form with current values

#### 3.3 Delete Accessory
- **Endpoint**: `DELETE /api/v2/accessories/{accessory_id}`
- **Note**: Will fail if items are checked out
- **UI Requirements**:
  - Add delete option
  - Show warning about checked-out items
  - Confirmation dialog

#### 3.4 Return/Checkin Accessory
- **Endpoint**: `POST /api/v2/accessories/{accessory_id}/checkin`
- **Request Body**:
```json
{
  "customer_id": "integer (required)",
  "quantity": "integer (default: 1)",
  "condition": "string (optional)",
  "notes": "string (optional)",
  "ticket_id": "integer (optional)"
}
```
- **UI Requirements**:
  - Add "Check-in" button to accessory detail
  - Show customer picker (who is returning)
  - Quantity selector
  - Optional condition and notes

#### 3.5 Checkout Accessory (NOTE: Endpoint may need to be built)
- **Endpoint**: `POST /api/v2/accessories/{accessory_id}/checkout` (may not exist yet)
- **Fallback**: Use existing web workflow or request backend endpoint
- **Request Body**:
```json
{
  "customer_id": "integer (required)",
  "quantity": "integer (default: 1)",
  "notes": "string (optional)",
  "ticket_id": "integer (optional)"
}
```
- **UI Requirements**:
  - Add "Check-out" button
  - Customer picker
  - Quantity selector (up to available)
  - Update available count on success

---

### Phase 4: MEDIUM PRIORITY - Customer Management (5 features)

#### 4.1 Get Customer Detail
- **Endpoint**: `GET /api/v2/customers/{customer_id}`
- **UI Requirements**:
  - Create customer detail view
  - Show all customer fields
  - Navigate from customer list/search

#### 4.2 Create Customer
- **Endpoint**: `POST /api/v2/customers`
- **Request Body**:
```json
{
  "name": "string (required)",
  "contact_number": "string (required)",
  "address": "string (required)",
  "country": "string (required)",
  "email": "string (optional)",
  "company_id": "integer (optional)"
}
```
- **UI Requirements**:
  - Add "Create Customer" button
  - Form with validation
  - Country picker
  - Company picker (optional)

#### 4.3 Edit Customer
- **Endpoint**: `PUT /api/v2/customers/{customer_id}`
- **Request Body**: Same as create (all optional)
- **UI Requirements**:
  - Add "Edit" button to customer detail
  - Pre-populated form

#### 4.4 Delete Customer
- **Endpoint**: `DELETE /api/v2/customers/{customer_id}`
- **Note**: Cannot delete customers with assigned assets/accessories/tickets
- **UI Requirements**:
  - Delete option with confirmation
  - Show error if customer has dependencies

#### 4.5 View Customer Tickets
- **Endpoint**: `GET /api/v2/customers/{customer_id}/tickets`
- **Query Parameters**: `page`, `per_page`, `status`, `sort`, `order`
- **UI Requirements**:
  - Add "Tickets" tab/section to customer detail
  - Show ticket list with status
  - Navigate to ticket detail on tap

---

### Phase 5: LOW PRIORITY - Dashboard & Reports (3 features)

#### 5.1 Dashboard Widgets
- **Endpoint**: `GET /api/v2/dashboard/widgets`
- **Widget Data**: `GET /api/v2/dashboard/widgets/{widget_id}/data`
- **UI Requirements**:
  - Create dashboard view
  - Display key metrics (ticket counts, asset counts)
  - Refresh on pull

#### 5.2 User Preferences
- **Get**: `GET /api/v2/user/preferences`
- **Update**: `PUT /api/v2/user/preferences`
- **Request Body**:
```json
{
  "theme": {"mode": "light|dark|auto"},
  "layout": {"default_homepage": "dashboard|tickets|inventory"},
  "notifications": {"email_enabled": true, "sound_enabled": false}
}
```
- **UI Requirements**:
  - Add settings/preferences screen
  - Theme selector
  - Default homepage picker
  - Notification toggles

#### 5.3 Report Generation
- **Templates**: `GET /api/v2/reports/templates`
- **Generate**: `POST /api/v2/reports/generate`
- **Request Body**:
```json
{
  "template_id": "string (required)",
  "parameters": {
    "date_from": "YYYY-MM-DD",
    "date_to": "YYYY-MM-DD"
  },
  "format": "json|csv|pdf"
}
```
- **UI Requirements**:
  - Add reports section
  - Template picker
  - Date range selector
  - Display results or share file

---

## Implementation Guidelines

### Code Organization
```
TrueLog/
├── Models/
│   ├── Ticket+Extensions.swift      // Add edit/status/assign models
│   ├── Asset+Extensions.swift       // Add edit/transfer models
│   ├── Accessory+Extensions.swift   // Add CRUD models
│   ├── Customer.swift               // New customer model
│   └── Dashboard.swift              // New dashboard models
├── Services/
│   ├── TicketService+Edit.swift     // Ticket edit/status/assign
│   ├── AssetService+Edit.swift      // Asset edit/delete/transfer
│   ├── AccessoryService+CRUD.swift  // Full accessory CRUD
│   ├── CustomerService.swift        // New customer service
│   └── DashboardService.swift       // New dashboard service
├── Views/
│   ├── Tickets/
│   │   ├── TicketEditView.swift
│   │   ├── TicketStatusPicker.swift
│   │   └── TicketAssignSheet.swift
│   ├── Assets/
│   │   ├── AssetEditView.swift
│   │   └── AssetTransferSheet.swift
│   ├── Accessories/
│   │   ├── AccessoryCreateView.swift
│   │   ├── AccessoryEditView.swift
│   │   ├── AccessoryCheckoutSheet.swift
│   │   └── AccessoryCheckinSheet.swift
│   ├── Customers/
│   │   ├── CustomerListView.swift
│   │   ├── CustomerDetailView.swift
│   │   ├── CustomerCreateView.swift
│   │   └── CustomerEditView.swift
│   └── Dashboard/
│       └── DashboardView.swift
└── ViewModels/
    ├── TicketEditViewModel.swift
    ├── AssetEditViewModel.swift
    ├── AccessoryViewModel.swift
    ├── CustomerViewModel.swift
    └── DashboardViewModel.swift
```

### API Client Pattern
```swift
// Example API call pattern
func updateTicketStatus(ticketId: Int, status: String) async throws -> Ticket {
    let endpoint = "/api/v2/tickets/\(ticketId)/status"
    let body = ["status": status]

    let response: APIResponse<Ticket> = try await apiClient.post(endpoint, body: body)

    guard response.success else {
        throw APIError.serverError(response.message ?? "Unknown error")
    }

    return response.data
}
```

### Error Handling
```swift
enum APIError: LocalizedError {
    case unauthorized
    case forbidden(String)
    case notFound
    case validationError(String)
    case serverError(String)
    case networkError(Error)

    var errorDescription: String? {
        switch self {
        case .unauthorized: return "Session expired. Please login again."
        case .forbidden(let msg): return msg
        case .notFound: return "Resource not found."
        case .validationError(let msg): return msg
        case .serverError(let msg): return msg
        case .networkError(let error): return error.localizedDescription
        }
    }
}
```

### UI/UX Guidelines
1. **Loading States**: Show progress indicator during API calls
2. **Error Handling**: Display user-friendly error alerts
3. **Optimistic Updates**: Update UI immediately, rollback on failure
4. **Confirmation Dialogs**: Always confirm destructive actions (delete)
5. **Pull to Refresh**: Support refresh on all list views
6. **Offline Handling**: Show appropriate message when offline

---

## Testing Checklist

### For Each Feature:
- [ ] API endpoint responds correctly
- [ ] Success case works
- [ ] Error cases handled gracefully
- [ ] Loading state displayed
- [ ] UI updates after action
- [ ] Works offline (shows appropriate error)
- [ ] Works with different user permission levels

### Permission-Gated Features:
- Ticket edit/delete: Check `can_edit_tickets` permission
- Asset edit/delete: Check `can_edit_assets` permission
- Accessory operations: Check `can_edit_assets` permission
- Customer operations: Check user type (not CLIENT)

---

## Priority Order Summary

| Phase | Features | Endpoints | Estimated Effort |
|-------|----------|-----------|------------------|
| 1 | Ticket Workflow | 6 | HIGH |
| 2 | Asset Management | 3 | MEDIUM |
| 3 | Accessory CRUD | 5 | MEDIUM |
| 4 | Customer CRUD | 5 | MEDIUM |
| 5 | Dashboard/Reports | 3 | LOW |

**Total: 22 features to implement**

---

## Notes for Backend Team

The following endpoints may need to be created or verified:

1. **Comment Edit/Delete**: Verify if `PUT/DELETE /api/v2/tickets/{id}/comments/{cid}` exists
2. **Accessory Checkout**: May need `POST /api/v2/accessories/{id}/checkout` endpoint
3. **Notifications API**: Currently session-based, may need mobile endpoint

---

## Reference Documentation

- Mobile API Docs: `/Users/123456/inventory/api_docs_mobile.md`
- API v2 Docs: `/Users/123456/inventory/api_docs_v2.md`
- Gap Analysis: `/Users/123456/inventory/mobile_api_gap_analysis.md`
- Full API Documentation: `/Users/123456/inventory/TrueLog_API_Documentation.docx`
