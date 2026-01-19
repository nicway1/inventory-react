# Mobile App: PDF Asset Extraction Feature

## Overview

Add a new feature to the iOS app that allows users to extract and import assets from PDF delivery orders attached to Intake Tickets. The backend uses OCR to parse scanned delivery orders (Success Tech, AsiaCloud format) and extract asset information like serial numbers, model, specs, etc.

## API Endpoints

Base URL: `/api/mobile/v1`

### 1. Get PDF Attachments
```
GET /intake/tickets/{ticket_id}/pdf-attachments
```

Returns list of PDF attachments for an intake ticket.

**Response:**
```json
{
    "success": true,
    "ticket_id": 123,
    "ticket_number": "INT-2025-001",
    "attachments": [
        {
            "id": 1,
            "filename": "4500153441 SOPHOS.pdf",
            "uploaded_at": "2025-01-15T10:30:00Z",
            "uploaded_by": "admin"
        }
    ]
}
```

### 2. Extract Assets from PDFs
```
GET /intake/tickets/{ticket_id}/extract-assets
```

Extracts assets from all PDF attachments using OCR. This is the main extraction endpoint.

**Response:**
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
            "supplier": "Success Tech Pte Ltd",
            "total_quantity": 1,
            "assets": [
                {
                    "serial_num": "0F3P86Y25463P7",
                    "name": "Surface Laptop",
                    "model": "Surface Laptop 7th Edition",
                    "manufacturer": "Microsoft",
                    "category": "Laptop",
                    "cpu_type": "Intel Core Ultra",
                    "cpu_cores": null,
                    "memory": "32GB",
                    "storage": "512GB",
                    "keyboard": "US - English",
                    "condition": "New"
                }
            ],
            "error": null
        }
    ]
}
```

### 3. Extract Single PDF (Optional)
```
GET /intake/extract-single-pdf/{attachment_id}
```

Extract assets from a single PDF attachment.

**Response:** Same structure as individual result in extract-assets.

### 4. Import Assets
```
POST /intake/tickets/{ticket_id}/import-assets
```

Import selected assets into inventory.

**Request Body:**
```json
{
    "company_id": 1,
    "customer_name": "Sophos Computer Security Pte Ltd",
    "country": "Singapore",
    "status": "Available",
    "assets": [
        {
            "serial_num": "0F3P86Y25463P7",
            "name": "Surface Laptop",
            "model": "Surface Laptop 7th Edition",
            "manufacturer": "Microsoft",
            "category": "Laptop",
            "cpu_type": "Intel Core Ultra",
            "memory": "32GB",
            "storage": "512GB",
            "keyboard": "US - English",
            "condition": "New",
            "po_number": "4500153441",
            "do_number": "SCT-DO250154"
        }
    ]
}
```

**Response:**
```json
{
    "success": true,
    "imported_count": 7,
    "skipped_count": 1,
    "errors": ["Serial 0F3P86Y25463P7 already exists (Asset #123)"],
    "imported_assets": [
        {
            "id": 456,
            "serial_num": "0F36YW925483P7",
            "name": "Surface Laptop",
            "model": "Surface Laptop 7th Edition"
        }
    ],
    "ticket_status": "Completed"
}
```

## UI Flow

### 1. Entry Point
Add a "Extract from PDF" option in the Intake Ticket detail view when:
- Ticket has PDF attachments
- Ticket status is not "Completed"

### 2. PDF Extraction Screen
**Header:** "Extract Assets from PDF"
**Subheader:** Show ticket number

**Content:**
1. Show loading indicator while calling `/extract-assets`
2. On success, display:
   - Summary card: "Found X assets from Y PDF(s)"
   - For each PDF result:
     - Filename
     - PO Number, DO Number, Customer (if available)
     - Error message (if extraction failed)
     - List of extracted assets

### 3. Asset List
For each extracted asset, show:
- Checkbox (selected by default)
- Serial Number (monospace font)
- Name/Model
- Memory / Storage
- Manufacturer

**Actions:**
- "Select All" / "Deselect All" toggle per PDF
- Selected count at bottom

### 4. Import Options Form
Before importing, allow user to set:
- **Company** (dropdown from existing companies)
- **Customer Name** (text field, pre-filled from extraction)
- **Country** (dropdown: Singapore, Malaysia, Indonesia, etc.)
- **Status** (dropdown: Available, In Stock, Deployed, In Transit)

### 5. Import Confirmation
**Button:** "Import X Selected Assets"

On tap:
1. Show confirmation alert
2. Call `/import-assets` with selected assets and options
3. Show success/error result
4. Navigate back to ticket (ticket status will be "Completed")

### 6. Result Screen
Show import results:
- Success count
- Skipped count (duplicates)
- Error messages (if any)
- List of imported assets with their new IDs

## SwiftUI Models

```swift
// MARK: - PDF Attachment
struct PDFAttachment: Codable, Identifiable {
    let id: Int
    let filename: String
    let uploadedAt: String?
    let uploadedBy: String?

    enum CodingKeys: String, CodingKey {
        case id, filename
        case uploadedAt = "uploaded_at"
        case uploadedBy = "uploaded_by"
    }
}

// MARK: - Extracted Asset
struct ExtractedAsset: Codable, Identifiable {
    var id: String { serialNum }  // Use serial as ID
    let serialNum: String
    let name: String?
    let model: String?
    let manufacturer: String?
    let category: String?
    let cpuType: String?
    let cpuCores: String?
    let memory: String?
    let storage: String?
    let keyboard: String?
    let condition: String?

    var isSelected: Bool = true  // For UI selection

    enum CodingKeys: String, CodingKey {
        case serialNum = "serial_num"
        case name, model, manufacturer, category
        case cpuType = "cpu_type"
        case cpuCores = "cpu_cores"
        case memory, storage, keyboard, condition
    }
}

// MARK: - PDF Extraction Result
struct PDFExtractionResult: Codable, Identifiable {
    var id: Int { attachmentId }
    let attachmentId: Int
    let filename: String
    let poNumber: String?
    let doNumber: String?
    let reference: String?
    let customer: String?
    let shipDate: String?
    let supplier: String?
    let totalQuantity: Int?
    let assets: [ExtractedAsset]
    let error: String?

    enum CodingKeys: String, CodingKey {
        case attachmentId = "attachment_id"
        case filename
        case poNumber = "po_number"
        case doNumber = "do_number"
        case reference, customer
        case shipDate = "ship_date"
        case supplier
        case totalQuantity = "total_quantity"
        case assets, error
    }
}

// MARK: - Extraction Response
struct ExtractionResponse: Codable {
    let success: Bool
    let ticketId: Int?
    let ticketNumber: String?
    let totalAssets: Int?
    let results: [PDFExtractionResult]?
    let error: String?

    enum CodingKeys: String, CodingKey {
        case success
        case ticketId = "ticket_id"
        case ticketNumber = "ticket_number"
        case totalAssets = "total_assets"
        case results, error
    }
}

// MARK: - Import Request
struct ImportAssetsRequest: Codable {
    let companyId: Int?
    let customerName: String?
    let country: String
    let status: String
    let assets: [ExtractedAsset]

    enum CodingKeys: String, CodingKey {
        case companyId = "company_id"
        case customerName = "customer_name"
        case country, status, assets
    }
}

// MARK: - Imported Asset
struct ImportedAsset: Codable, Identifiable {
    let id: Int
    let serialNum: String
    let name: String
    let model: String?

    enum CodingKeys: String, CodingKey {
        case id
        case serialNum = "serial_num"
        case name, model
    }
}

// MARK: - Import Response
struct ImportResponse: Codable {
    let success: Bool
    let importedCount: Int?
    let skippedCount: Int?
    let errors: [String]?
    let importedAssets: [ImportedAsset]?
    let ticketStatus: String?
    let error: String?

    enum CodingKeys: String, CodingKey {
        case success
        case importedCount = "imported_count"
        case skippedCount = "skipped_count"
        case errors
        case importedAssets = "imported_assets"
        case ticketStatus = "ticket_status"
        case error
    }
}
```

## API Service Methods

```swift
// In MobileAPIService or similar

func getPDFAttachments(ticketId: Int) async throws -> [PDFAttachment]

func extractAssetsFromPDFs(ticketId: Int) async throws -> ExtractionResponse

func extractSinglePDF(attachmentId: Int) async throws -> PDFExtractionResult

func importAssets(
    ticketId: Int,
    companyId: Int?,
    customerName: String?,
    country: String,
    status: String,
    assets: [ExtractedAsset]
) async throws -> ImportResponse
```

## Error Handling

1. **No PDF attachments:** Show message "No PDF attachments found"
2. **Extraction failed:** Show error message from API, allow retry
3. **OCR timeout:** May happen on large/complex PDFs - show appropriate message
4. **Import errors:** Show list of failed serials (duplicates)
5. **Network errors:** Standard network error handling

## Notes

- OCR extraction can take 5-15 seconds per PDF depending on size
- Show appropriate loading state with progress indication
- Duplicate serial numbers are automatically skipped during import
- Ticket status is set to "Completed" after successful import
- Currently supports Success Tech and AsiaCloud delivery order formats
- Serial numbers starting with "0F" are Microsoft Surface devices
