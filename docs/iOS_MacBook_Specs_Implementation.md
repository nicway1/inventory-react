# iOS Implementation: MacBook Specs Collector Feature

## Overview
Implement a new feature in the iOS app to view pending MacBook specs collected from devices and quickly create assets from them, optionally linking to tickets.

## API Endpoints

Base URL: `https://inventory.truelog.com.sg/api/mobile/v1`

All endpoints require Bearer token authentication:
```
Authorization: Bearer <jwt_token>
```

### 1. List Pending Device Specs
```
GET /specs
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| processed | string | "false" | Filter by processed status ("true" or "false") |
| limit | int | 50 | Max results (max 100) |

**Response:**
```json
{
  "success": true,
  "count": 3,
  "specs": [
    {
      "id": 1,
      "serial_number": "C02X12345678",
      "model_id": "Mac14,7",
      "model_name": "MacBook Pro 13\" M2 (2022)",
      "cpu": "Apple M2",
      "cpu_cores": "8 (4P + 4E)",
      "ram_gb": "16",
      "storage_gb": "512",
      "storage_type": "SSD",
      "battery_cycles": "236",
      "battery_health": "92.5",
      "submitted_at": "2024-12-22T10:30:00",
      "processed": false
    }
  ]
}
```

### 2. Get Spec Details
```
GET /specs/{spec_id}
```

**Response:**
```json
{
  "success": true,
  "spec": {
    "id": 1,
    "serial_number": "C02X12345678",
    "hardware_uuid": "ABC123-DEF456-...",
    "model_id": "Mac14,7",
    "model_name": "MacBook Pro",
    "model_name_translated": "MacBook Pro 13\" M2 (2022)",
    "cpu": "Apple M2",
    "cpu_cores": "8 (4P + 4E)",
    "gpu": "Apple M2 GPU",
    "gpu_cores": "10",
    "ram_gb": "16",
    "memory_type": "LPDDR5",
    "storage_gb": "512",
    "storage_type": "SSD",
    "free_space": "234 GB",
    "os_name": "macOS",
    "os_version": "14.2",
    "os_build": "23C64",
    "battery_cycles": "236",
    "battery_health": "92.5",
    "wifi_mac": "A1:B2:C3:D4:E5:F6",
    "ethernet_mac": null,
    "ip_address": "192.168.1.100",
    "submitted_at": "2024-12-22T10:30:00",
    "processed": false,
    "processed_at": null,
    "asset_id": null,
    "asset_prefill": {
      "serial_num": "C02X12345678",
      "model": "Mac14,7",
      "product": "MacBook Pro 13\" M2 (2022)",
      "asset_type": "Laptop",
      "cpu_type": "Apple M2",
      "cpu_cores": "8 (4P + 4E)",
      "gpu_cores": "10",
      "memory": "16 GB",
      "harddrive": "512 GB SSD",
      "manufacturer": "Apple"
    }
  }
}
```

### 3. Find Related Tickets
```
GET /specs/{spec_id}/find-tickets
```

**Response:**
```json
{
  "success": true,
  "count": 2,
  "tickets": [
    {
      "id": 456,
      "display_id": "TKT-2024-0456",
      "title": "MacBook Pro C02X12345678 intake",
      "status": "Open",
      "category": "Asset Intake",
      "created_at": "2024-12-20T09:00:00",
      "customer_name": "Acme Corp"
    }
  ],
  "search_terms": ["C02X12345678", "Mac14,7"]
}
```

### 4. Create Asset from Spec (Without Ticket)
```
POST /specs/{spec_id}/create-asset
```

**Request Body:**
```json
{
  "asset_tag": "ASSET-001",
  "status": "IN_STOCK",
  "condition": "Good",
  "customer": "Acme Corp",
  "country": "Singapore",
  "notes": "Created from spec collector"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Asset created successfully",
  "asset": {
    "id": 789,
    "asset_tag": "ASSET-001",
    "serial_num": "C02X12345678",
    "name": "MacBook Pro 13\" M2 (2022)",
    "model": "Mac14,7",
    "status": "In Stock"
  }
}
```

### 5. Create Asset and Link to Ticket
```
POST /specs/{spec_id}/create-asset-with-ticket
```

**Request Body:**
```json
{
  "ticket_id": 456,
  "asset_tag": "ASSET-001",
  "status": "IN_STOCK",
  "condition": "Good",
  "notes": "Linked to intake ticket"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Asset created and linked to ticket successfully",
  "asset": {
    "id": 789,
    "asset_tag": "ASSET-001",
    "serial_num": "C02X12345678",
    "name": "MacBook Pro 13\" M2 (2022)",
    "model": "Mac14,7",
    "status": "In Stock"
  },
  "ticket": {
    "id": 456,
    "display_id": "TKT-2024-0456"
  }
}
```

### 6. Mark Spec as Processed (Skip/Dismiss)
```
POST /specs/{spec_id}/mark-processed
```

**Request Body:**
```json
{
  "notes": "Duplicate device, skipped"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Spec marked as processed"
}
```

---

## UI Implementation

### 1. New Tab/Section: "Device Specs"
Add a new tab or menu item called "Device Specs" or "MacBook Collector"

### 2. Specs List View
Display a list of pending specs with:
- Serial number (bold, primary text)
- Model name (translated, e.g., "MacBook Pro 13\" M2 (2022)")
- Submitted date/time
- Badge showing "New" for unprocessed

### 3. Spec Detail View
When tapping a spec, show full details:
- **Device Info**: Serial, UUID
- **Model**: Translated name + Model ID
- **Processor**: CPU name + core count
- **Memory**: RAM size
- **Storage**: Size + type
- **Battery**: Cycle count + health percentage
- **macOS**: Version + build
- **Network**: WiFi MAC

### 4. Action Buttons
Two main actions on spec detail:

#### a) "Quick Add Asset" Button
- Uses `asset_prefill` data to pre-fill asset creation form
- Shows form with pre-filled fields (editable)
- User adds: asset_tag, status, condition
- Calls `POST /specs/{id}/create-asset`

#### b) "Find Tickets" Button
- Calls `GET /specs/{id}/find-tickets`
- Shows list of related tickets
- Each ticket shows: display_id, title, status
- "Link & Create" button next to each ticket
- Calls `POST /specs/{id}/create-asset-with-ticket` with selected ticket_id

### 5. Confirmation Flow
After successful asset creation:
- Show success message with asset ID
- Option to view the created asset
- Return to specs list (spec now shows as "Done")

---

## Data Models

### DeviceSpec
```swift
struct DeviceSpec: Codable, Identifiable {
    let id: Int
    let serialNumber: String
    let hardwareUuid: String?
    let modelId: String?
    let modelName: String?
    let modelNameTranslated: String?
    let cpu: String?
    let cpuCores: String?
    let gpu: String?
    let gpuCores: String?
    let ramGb: String?
    let memoryType: String?
    let storageGb: String?
    let storageType: String?
    let freeSpace: String?
    let osName: String?
    let osVersion: String?
    let osBuild: String?
    let batteryCycles: String?
    let batteryHealth: String?
    let wifiMac: String?
    let ethernetMac: String?
    let ipAddress: String?
    let submittedAt: String?
    let processed: Bool
    let processedAt: String?
    let assetId: Int?
    let assetPrefill: AssetPrefill?

    enum CodingKeys: String, CodingKey {
        case id
        case serialNumber = "serial_number"
        case hardwareUuid = "hardware_uuid"
        case modelId = "model_id"
        case modelName = "model_name"
        case modelNameTranslated = "model_name_translated"
        case cpu
        case cpuCores = "cpu_cores"
        case gpu
        case gpuCores = "gpu_cores"
        case ramGb = "ram_gb"
        case memoryType = "memory_type"
        case storageGb = "storage_gb"
        case storageType = "storage_type"
        case freeSpace = "free_space"
        case osName = "os_name"
        case osVersion = "os_version"
        case osBuild = "os_build"
        case batteryCycles = "battery_cycles"
        case batteryHealth = "battery_health"
        case wifiMac = "wifi_mac"
        case ethernetMac = "ethernet_mac"
        case ipAddress = "ip_address"
        case submittedAt = "submitted_at"
        case processed
        case processedAt = "processed_at"
        case assetId = "asset_id"
        case assetPrefill = "asset_prefill"
    }
}

struct AssetPrefill: Codable {
    let serialNum: String
    let model: String
    let product: String
    let assetType: String
    let cpuType: String
    let cpuCores: String
    let gpuCores: String
    let memory: String
    let harddrive: String
    let manufacturer: String

    enum CodingKeys: String, CodingKey {
        case serialNum = "serial_num"
        case model
        case product
        case assetType = "asset_type"
        case cpuType = "cpu_type"
        case cpuCores = "cpu_cores"
        case gpuCores = "gpu_cores"
        case memory
        case harddrive
        case manufacturer
    }
}

struct RelatedTicket: Codable, Identifiable {
    let id: Int
    let displayId: String
    let title: String
    let status: String
    let category: String
    let createdAt: String?
    let customerName: String

    enum CodingKeys: String, CodingKey {
        case id
        case displayId = "display_id"
        case title
        case status
        case category
        case createdAt = "created_at"
        case customerName = "customer_name"
    }
}
```

---

## API Service Methods

```swift
class SpecsService {

    // List pending specs
    func fetchPendingSpecs(limit: Int = 50) async throws -> [DeviceSpec]

    // Get spec details
    func fetchSpecDetail(specId: Int) async throws -> DeviceSpec

    // Find related tickets
    func findRelatedTickets(specId: Int) async throws -> [RelatedTicket]

    // Create asset from spec
    func createAssetFromSpec(
        specId: Int,
        assetTag: String?,
        status: String,
        condition: String?,
        notes: String?
    ) async throws -> CreatedAsset

    // Create asset and link to ticket
    func createAssetWithTicket(
        specId: Int,
        ticketId: Int,
        assetTag: String?,
        status: String,
        condition: String?,
        notes: String?
    ) async throws -> (asset: CreatedAsset, ticket: LinkedTicket)

    // Mark spec as processed (skip)
    func markSpecProcessed(specId: Int, notes: String?) async throws
}
```

---

## Error Handling

| HTTP Code | Error | Description |
|-----------|-------|-------------|
| 401 | Unauthorized | Invalid or expired token |
| 403 | Forbidden | User lacks permission to create assets |
| 404 | Not Found | Spec or ticket not found |
| 400 | Bad Request | Spec already processed or invalid data |
| 409 | Conflict | Asset with same serial number exists |
| 500 | Server Error | Internal error |

---

## Status Values for Asset Creation

Valid status values:
- `IN_STOCK`
- `READY_TO_DEPLOY`
- `DEPLOYED`
- `REPAIR`
- `ARCHIVED`
- `DISPOSED`

---

## Flow Diagram

```
┌─────────────────┐
│  Specs List     │
│  (GET /specs)   │
└────────┬────────┘
         │ tap spec
         ▼
┌─────────────────┐
│  Spec Detail    │
│  (GET /specs/id)│
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌──────────────┐
│Quick   │ │Find Tickets  │
│Add     │ │(GET find-    │
│        │ │tickets)      │
└───┬────┘ └──────┬───────┘
    │             │
    ▼             ▼
┌────────────┐ ┌─────────────────┐
│Create Form │ │Select Ticket    │
│(pre-filled)│ │                 │
└─────┬──────┘ └────────┬────────┘
      │                 │
      ▼                 ▼
┌────────────┐ ┌─────────────────┐
│POST create-│ │POST create-     │
│asset       │ │asset-with-ticket│
└─────┬──────┘ └────────┬────────┘
      │                 │
      └────────┬────────┘
               ▼
        ┌────────────┐
        │  Success!  │
        │  Asset ID  │
        └────────────┘
```

---

## Testing Checklist

- [ ] List specs loads correctly
- [ ] Empty state when no pending specs
- [ ] Spec detail shows all fields
- [ ] Model name translation displays correctly
- [ ] Quick add pre-fills form correctly
- [ ] Find tickets returns results
- [ ] Empty state when no related tickets
- [ ] Create asset without ticket works
- [ ] Create asset with ticket linking works
- [ ] Duplicate serial number shows error
- [ ] Already processed spec shows error
- [ ] Success confirmation displays
- [ ] Spec list refreshes after creation
- [ ] Pull to refresh works
