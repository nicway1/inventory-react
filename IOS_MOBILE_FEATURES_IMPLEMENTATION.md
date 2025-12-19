# iOS App Implementation Guide: Asset Management & Tracking Features

---

## YOUR TASK

You need to implement **3 new features** in the iOS mobile app:

### What You Need To Build:

1. **Add Tech Asset Screen**
   - Create a new form screen where users can add a new tech asset
   - Include fields: Asset Tag (required), Serial Number (required), Name, Model, Manufacturer, Category, Country, Status, Notes
   - Submit to the API endpoint and show success/error feedback
   - Add navigation to this screen from the main menu or assets list

2. **Outbound Tracking Screen**
   - Create a list view showing all tickets with outbound shipping tracking
   - Each item should show: Ticket ID, Customer name, Tracking numbers, Carrier, Status
   - Add a "Mark as Received" button for each tracking item
   - When tapped, call the API to mark that shipment as received
   - Support pull-to-refresh and pagination

3. **Return Tracking Screen**
   - Create a list view showing all tickets with return tracking
   - Each item should show: Ticket ID, Customer name, Return tracking number, Carrier, Status
   - Add a "Mark as Received" button for each return tracking item
   - When tapped, call the API to mark that return as received
   - Support pull-to-refresh and pagination

### Navigation:
- Add menu items or tab bar entries to access these 3 new screens
- Use appropriate icons for each feature

---

## IMPLEMENTATION DETAILS

This guide covers the implementation of three new features for the iOS mobile app:
1. **Add Tech Asset** - Create new assets from mobile
2. **Outbound Tracking** - View and manage shipping tracking with mark as received
3. **Return Tracking** - View and manage return tracking with mark as received

---

## API Base URL
```
/api/mobile/v1
```

All endpoints require JWT authentication:
```
Authorization: Bearer <token>
```

---

## 1. ADD TECH ASSET FEATURE

### API Endpoint

**POST** `/api/mobile/v1/assets`

### Request Body
```json
{
  "asset_tag": "ASSET-001",        // Required - Unique asset tag
  "serial_num": "SN123456",        // Required - Unique serial number
  "name": "MacBook Pro 14",        // Optional - Display name
  "model": "MacBook Pro 14-inch 2023",  // Optional
  "manufacturer": "Apple",         // Optional
  "category": "Laptop",            // Optional
  "hardware_type": "Laptop",       // Optional
  "country": "Singapore",          // Optional - Country location
  "status": "IN_STOCK",            // Optional - Default: IN_STOCK
  "notes": "Optional notes",       // Optional
  "customer": "CUSTOMER_NAME",     // Optional - Customer assignment
  "asset_type": "Computer",        // Optional
  "condition": "New"               // Optional
}
```

### Response (Success - 201)
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
    "category": "Laptop",
    "hardware_type": "Laptop",
    "country": "Singapore",
    "status": "In Stock",
    "notes": "Optional notes",
    "created_at": "2025-01-15T10:30:00"
  }
}
```

### Response (Error - 400)
```json
{
  "success": false,
  "error": "Asset with serial number SN123456 already exists"
}
```

### Response (Permission Denied - 403)
```json
{
  "success": false,
  "error": "No permission to create assets"
}
```

### iOS Data Model
```swift
struct CreateAssetRequest: Codable {
    let assetTag: String
    let serialNum: String
    let name: String?
    let model: String?
    let manufacturer: String?
    let category: String?
    let hardwareType: String?
    let country: String?
    let status: String?
    let notes: String?
    let customer: String?
    let assetType: String?
    let condition: String?

    enum CodingKeys: String, CodingKey {
        case assetTag = "asset_tag"
        case serialNum = "serial_num"
        case name, model, manufacturer, category
        case hardwareType = "hardware_type"
        case country, status, notes, customer
        case assetType = "asset_type"
        case condition
    }
}

struct CreateAssetResponse: Codable {
    let success: Bool
    let message: String?
    let asset: Asset?
    let error: String?
}
```

### UI Implementation Suggestions

**Add Asset Screen:**
- Form with text fields for each asset property
- Asset Tag and Serial Number fields marked as required (with asterisk)
- Dropdown/Picker for:
  - Status: IN_STOCK, READY_TO_DEPLOY, SHIPPED, DEPLOYED, REPAIR, ARCHIVED, DISPOSED
  - Country: Singapore, USA, Japan, Philippines, Australia, Israel, India
  - Category: Laptop, Desktop, Monitor, Tablet, Phone, etc.
- Optional barcode scanner button next to Serial Number field
- Save button at bottom
- Show loading indicator during API call
- Show success alert with created asset info
- Show error alert if duplicate or validation fails

---

## 2. OUTBOUND TRACKING FEATURE

### List Outbound Tracking

**GET** `/api/mobile/v1/tracking/outbound`

### Query Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | int | 1 | Page number |
| limit | int | 20 | Items per page (max 100) |
| status | string | all | Filter: `pending`, `in_transit`, `delivered`, `all` |

### Response (Success - 200)
```json
{
  "success": true,
  "tracking_items": [
    {
      "ticket_id": 123,
      "display_id": "TIC-00123",
      "subject": "Asset Checkout for John Doe",
      "category": "ASSET_CHECKOUT_CLAW",
      "customer_name": "John Doe",
      "shipping_address": "123 Main St, Singapore 123456",
      "tracking_numbers": [
        {
          "slot": 1,
          "tracking_number": "TRACK123456",
          "carrier": "DHL",
          "status": "In Transit",
          "is_delivered": false
        },
        {
          "slot": 2,
          "tracking_number": "TRACK789012",
          "carrier": "FedEx",
          "status": "Delivered - Received on 2025-01-15 10:30",
          "is_delivered": true
        }
      ],
      "created_at": "2025-01-10T09:00:00",
      "updated_at": "2025-01-15T10:30:00"
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

### Mark Outbound as Received

**POST** `/api/mobile/v1/tracking/outbound/<ticket_id>/mark-received`

### Request Body
```json
{
  "slot": 1,                          // Optional: tracking slot 1-5, default 1
  "notes": "Received by customer"     // Optional: additional notes
}
```

### Response (Success - 200)
```json
{
  "success": true,
  "message": "Marked as received",
  "tracking": {
    "ticket_id": 123,
    "slot": 1,
    "tracking_number": "TRACK123456",
    "status": "Delivered - Received on 2025-01-15 10:30 - Received by customer"
  }
}
```

### iOS Data Models
```swift
struct OutboundTrackingItem: Codable, Identifiable {
    let ticketId: Int
    let displayId: String
    let subject: String
    let category: String?
    let customerName: String?
    let shippingAddress: String?
    let trackingNumbers: [TrackingNumber]
    let createdAt: String?
    let updatedAt: String?

    var id: Int { ticketId }

    enum CodingKeys: String, CodingKey {
        case ticketId = "ticket_id"
        case displayId = "display_id"
        case subject, category
        case customerName = "customer_name"
        case shippingAddress = "shipping_address"
        case trackingNumbers = "tracking_numbers"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

struct TrackingNumber: Codable, Identifiable {
    let slot: Int
    let trackingNumber: String
    let carrier: String?
    let status: String
    let isDelivered: Bool

    var id: Int { slot }

    enum CodingKeys: String, CodingKey {
        case slot
        case trackingNumber = "tracking_number"
        case carrier, status
        case isDelivered = "is_delivered"
    }
}

struct OutboundTrackingResponse: Codable {
    let success: Bool
    let trackingItems: [OutboundTrackingItem]?
    let pagination: Pagination?
    let error: String?

    enum CodingKeys: String, CodingKey {
        case success
        case trackingItems = "tracking_items"
        case pagination, error
    }
}

struct MarkReceivedRequest: Codable {
    let slot: Int?
    let notes: String?
}

struct MarkReceivedResponse: Codable {
    let success: Bool
    let message: String?
    let tracking: MarkReceivedTracking?
    let error: String?
}

struct MarkReceivedTracking: Codable {
    let ticketId: Int
    let slot: Int?
    let trackingNumber: String
    let status: String

    enum CodingKeys: String, CodingKey {
        case ticketId = "ticket_id"
        case slot
        case trackingNumber = "tracking_number"
        case status
    }
}
```

### UI Implementation Suggestions

**Outbound Tracking List Screen:**
- Segmented control at top for status filter: All | Pending | In Transit | Delivered
- List of tracking items showing:
  - Ticket display ID and subject
  - Customer name
  - Each tracking number with carrier badge
  - Status indicator (color-coded: yellow=pending, blue=in transit, green=delivered)
  - "Mark Received" button for non-delivered items
- Pull-to-refresh functionality
- Pagination (load more on scroll)

**Tracking Item Card Design:**
```
┌─────────────────────────────────────────┐
│ TIC-00123                    [In Transit]│
│ Asset Checkout for John Doe             │
│                                         │
│ Customer: John Doe                      │
│ Address: 123 Main St, Singapore         │
│                                         │
│ Tracking Numbers:                       │
│ ┌─────────────────────────────────────┐ │
│ │ 1. TRACK123456 [DHL]                │ │
│ │    Status: In Transit               │ │
│ │    [Mark Received]                  │ │
│ └─────────────────────────────────────┘ │
│ ┌─────────────────────────────────────┐ │
│ │ 2. TRACK789012 [FedEx]     ✓        │ │
│ │    Status: Delivered                │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

**Mark Received Action:**
- Tap "Mark Received" button
- Show confirmation sheet/dialog with optional notes field
- On confirm, call API
- Update UI to show delivered status with checkmark
- Show success toast/alert

---

## 3. RETURN TRACKING FEATURE

### List Return Tracking

**GET** `/api/mobile/v1/tracking/return`

### Query Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | int | 1 | Page number |
| limit | int | 20 | Items per page (max 100) |
| status | string | all | Filter: `pending`, `in_transit`, `received`, `all` |

### Response (Success - 200)
```json
{
  "success": true,
  "tracking_items": [
    {
      "ticket_id": 456,
      "display_id": "TIC-00456",
      "subject": "Asset Return from Jane Smith",
      "category": "ASSET_RETURN_CLAW",
      "customer_name": "Jane Smith",
      "return_tracking": "RET987654",
      "return_status": "Pending",
      "is_received": false,
      "shipping_address": "456 Oak Ave, Singapore 654321",
      "created_at": "2025-01-12T14:00:00",
      "updated_at": "2025-01-12T14:00:00"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 12,
    "pages": 1
  }
}
```

### Mark Return as Received

**POST** `/api/mobile/v1/tracking/return/<ticket_id>/mark-received`

### Request Body
```json
{
  "notes": "Package received in good condition"  // Optional
}
```

### Response (Success - 200)
```json
{
  "success": true,
  "message": "Return marked as received",
  "tracking": {
    "ticket_id": 456,
    "return_tracking": "RET987654",
    "return_status": "Received on 2025-01-15 11:00 - Package received in good condition"
  }
}
```

### iOS Data Models
```swift
struct ReturnTrackingItem: Codable, Identifiable {
    let ticketId: Int
    let displayId: String
    let subject: String
    let category: String?
    let customerName: String?
    let returnTracking: String
    let returnStatus: String
    let isReceived: Bool
    let shippingAddress: String?
    let createdAt: String?
    let updatedAt: String?

    var id: Int { ticketId }

    enum CodingKeys: String, CodingKey {
        case ticketId = "ticket_id"
        case displayId = "display_id"
        case subject, category
        case customerName = "customer_name"
        case returnTracking = "return_tracking"
        case returnStatus = "return_status"
        case isReceived = "is_received"
        case shippingAddress = "shipping_address"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

struct ReturnTrackingResponse: Codable {
    let success: Bool
    let trackingItems: [ReturnTrackingItem]?
    let pagination: Pagination?
    let error: String?

    enum CodingKeys: String, CodingKey {
        case success
        case trackingItems = "tracking_items"
        case pagination, error
    }
}

struct MarkReturnReceivedResponse: Codable {
    let success: Bool
    let message: String?
    let tracking: ReturnReceivedTracking?
    let error: String?
}

struct ReturnReceivedTracking: Codable {
    let ticketId: Int
    let returnTracking: String
    let returnStatus: String

    enum CodingKeys: String, CodingKey {
        case ticketId = "ticket_id"
        case returnTracking = "return_tracking"
        case returnStatus = "return_status"
    }
}
```

### UI Implementation Suggestions

**Return Tracking List Screen:**
- Segmented control: All | Pending | In Transit | Received
- List of return tracking items showing:
  - Ticket display ID and subject
  - Customer name
  - Return tracking number
  - Status with color indicator
  - "Mark Received" button for non-received items
- Pull-to-refresh
- Pagination

**Return Tracking Card Design:**
```
┌─────────────────────────────────────────┐
│ TIC-00456                      [Pending]│
│ Asset Return from Jane Smith            │
│                                         │
│ Customer: Jane Smith                    │
│                                         │
│ Return Tracking: RET987654              │
│ Status: Pending                         │
│                                         │
│        [Mark Received]                  │
└─────────────────────────────────────────┘
```

---

## 4. NAVIGATION STRUCTURE

Suggested tab bar or menu structure:

```
┌─────────────────────────────────────────┐
│              Inventory App              │
├─────────────────────────────────────────┤
│                                         │
│  [Home]  [Tracking]  [Assets]  [More]   │
│                                         │
└─────────────────────────────────────────┘

Tracking Tab → Shows sub-navigation:
  - Outbound Tracking
  - Return Tracking

Assets Tab → Shows options:
  - View Assets (existing)
  - Add Asset (new)
```

Or as a drawer menu:
```
├── Dashboard
├── Tickets
├── Assets
│   ├── View Assets
│   └── Add Asset ← NEW
├── Tracking ← NEW SECTION
│   ├── Outbound Tracking
│   └── Return Tracking
└── Settings
```

---

## 5. API SERVICE IMPLEMENTATION

```swift
class TrackingService {
    private let apiClient: APIClient

    init(apiClient: APIClient) {
        self.apiClient = apiClient
    }

    // MARK: - Outbound Tracking

    func getOutboundTracking(
        page: Int = 1,
        limit: Int = 20,
        status: String = "all"
    ) async throws -> OutboundTrackingResponse {
        let endpoint = "/tracking/outbound?page=\(page)&limit=\(limit)&status=\(status)"
        return try await apiClient.get(endpoint)
    }

    func markOutboundReceived(
        ticketId: Int,
        slot: Int = 1,
        notes: String? = nil
    ) async throws -> MarkReceivedResponse {
        let endpoint = "/tracking/outbound/\(ticketId)/mark-received"
        let body = MarkReceivedRequest(slot: slot, notes: notes)
        return try await apiClient.post(endpoint, body: body)
    }

    // MARK: - Return Tracking

    func getReturnTracking(
        page: Int = 1,
        limit: Int = 20,
        status: String = "all"
    ) async throws -> ReturnTrackingResponse {
        let endpoint = "/tracking/return?page=\(page)&limit=\(limit)&status=\(status)"
        return try await apiClient.get(endpoint)
    }

    func markReturnReceived(
        ticketId: Int,
        notes: String? = nil
    ) async throws -> MarkReturnReceivedResponse {
        let endpoint = "/tracking/return/\(ticketId)/mark-received"
        let body = ["notes": notes]
        return try await apiClient.post(endpoint, body: body)
    }
}

class AssetService {
    private let apiClient: APIClient

    init(apiClient: APIClient) {
        self.apiClient = apiClient
    }

    func createAsset(_ request: CreateAssetRequest) async throws -> CreateAssetResponse {
        return try await apiClient.post("/assets", body: request)
    }
}
```

---

## 6. ERROR HANDLING

Common error responses to handle:

| Status | Error | User Message |
|--------|-------|--------------|
| 400 | Missing required fields | "Please fill in all required fields" |
| 400 | Duplicate asset_tag | "An asset with this tag already exists" |
| 400 | Duplicate serial_num | "An asset with this serial number already exists" |
| 400 | No return tracking | "No return tracking found for this ticket" |
| 400 | Invalid slot | "Invalid tracking slot number" |
| 401 | Invalid token | "Session expired. Please log in again" |
| 403 | No permission | "You don't have permission to perform this action" |
| 404 | Ticket not found | "Ticket not found or access denied" |
| 500 | Server error | "Something went wrong. Please try again" |

---

## 7. TESTING

### Test Scenarios

**Add Asset:**
1. Create asset with all fields → Success
2. Create asset with only required fields → Success
3. Create asset with duplicate asset_tag → Error
4. Create asset with duplicate serial_num → Error
5. Create asset without permission → 403 Error

**Outbound Tracking:**
1. Load all outbound tracking → Success
2. Filter by pending → Only pending items
3. Filter by delivered → Only delivered items
4. Mark as received → Status updates
5. Mark as received with notes → Notes included in status

**Return Tracking:**
1. Load all return tracking → Success
2. Filter by received → Only received items
3. Mark return as received → Status updates
4. Mark return without tracking number → Error

---

## 8. IMPLEMENTATION CHECKLIST

### Add Asset Feature
- [ ] Create `CreateAssetRequest` model
- [ ] Create `CreateAssetResponse` model
- [ ] Implement `AssetService.createAsset()` API call
- [ ] Create AddAssetView with form fields
- [ ] Add validation for required fields
- [ ] Implement barcode scanner (optional)
- [ ] Add to navigation/menu
- [ ] Test all scenarios

### Outbound Tracking Feature
- [ ] Create `OutboundTrackingItem` model
- [ ] Create `TrackingNumber` model
- [ ] Create `OutboundTrackingResponse` model
- [ ] Create `MarkReceivedRequest/Response` models
- [ ] Implement `TrackingService` with outbound methods
- [ ] Create OutboundTrackingListView
- [ ] Implement status filter segmented control
- [ ] Create tracking item card component
- [ ] Implement "Mark Received" action with confirmation
- [ ] Add pagination support
- [ ] Add to navigation/menu
- [ ] Test all scenarios

### Return Tracking Feature
- [ ] Create `ReturnTrackingItem` model
- [ ] Create `ReturnTrackingResponse` model
- [ ] Create `MarkReturnReceivedResponse` model
- [ ] Implement `TrackingService` with return methods
- [ ] Create ReturnTrackingListView
- [ ] Implement status filter segmented control
- [ ] Create return tracking card component
- [ ] Implement "Mark Received" action with confirmation
- [ ] Add pagination support
- [ ] Add to navigation/menu
- [ ] Test all scenarios

---

## Questions?

Contact the backend team if you need:
- Additional fields on any endpoint
- Different response formats
- Additional filtering options
- Webhook/push notification support for tracking updates
