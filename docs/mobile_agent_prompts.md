# Mobile Agent Prompts for Ticket Creation

This document contains the prompts and required fields for each ticket category that can be created via the iOS mobile app.

## API Endpoints

- **Base URL**: `/api/v1`
- **Create Ticket**: `POST /api/v1/tickets/create`
- **Get Categories**: `GET /api/v1/tickets/categories`
- **Search Assets**: `GET /api/v1/assets/search?q={query}`
- **Get Customers**: `GET /api/v1/customers`
- **Get Queues**: `GET /api/v1/queues`

## Authentication

All endpoints support dual authentication:

**iOS App (Recommended):**
```
Headers:
  X-API-Key: xAQhm3__ZH6MvRIPMIBSDRAsIa1w2Slh5uaCtc4NurM
  Authorization: Bearer <jwt_token>
  Content-Type: application/json
```

**JWT Only:**
```
Headers:
  Authorization: Bearer <jwt_token>
  Content-Type: application/json
```

## Success Response Format

All ticket creation endpoints return:
```json
{
  "success": true,
  "message": "Ticket created successfully",
  "data": {
    "ticket_id": 123,
    "display_id": "TKT-000123",
    "subject": "PIN Request for MacBook Pro (ABC123)",
    "status": "open"
  }
}
```

---

## 1. PIN Request

**Purpose**: Request PIN code for a locked device (MDM lock, activation lock, etc.)

### Required Fields
| Field | Type | Description |
|-------|------|-------------|
| `category` | string | Must be `"PIN_REQUEST"` |
| `serial_number` | string | Device serial number (scan barcode or enter manually) |
| `lock_type` | string | Type of lock (e.g., "MDM Lock", "Activation Lock", "BIOS Lock", "Firmware Lock") |
| `queue_id` | integer | Queue ID to assign the ticket |

### Optional Fields
| Field | Type | Description |
|-------|------|-------------|
| `priority` | string | "Low", "Medium", "High", or "Critical" (default: "Medium") |
| `notes` | string | Additional notes or context |

### Example Request
```json
{
  "category": "PIN_REQUEST",
  "serial_number": "C02XL0GTJGH5",
  "lock_type": "MDM Lock",
  "queue_id": 1,
  "priority": "High",
  "notes": "Customer needs urgent access"
}
```

### Prompt for Mobile Agent
```
To create a PIN Request ticket, I need:
1. The device serial number (you can scan the barcode or enter it manually)
2. What type of lock is on the device? (MDM Lock, Activation Lock, BIOS Lock, Firmware Lock)
3. Which queue should this be assigned to?
4. What priority level? (Low/Medium/High/Critical)
5. Any additional notes?
```

---

## 2. Asset Repair

**Purpose**: Report device damage and request repair assessment or service

### Required Fields
| Field | Type | Description |
|-------|------|-------------|
| `category` | string | Must be `"ASSET_REPAIR"` |
| `serial_number` | string | Device serial number |
| `damage_description` | string | Detailed description of the damage/issue |
| `queue_id` | integer | Queue ID to assign the ticket |

### Optional Fields
| Field | Type | Description |
|-------|------|-------------|
| `apple_diagnostics` | string | Apple diagnostics code if available |
| `country` | string | Country where device is located |
| `priority` | string | "Low", "Medium", "High", or "Critical" |
| `notes` | string | Additional notes |

### Example Request
```json
{
  "category": "ASSET_REPAIR",
  "serial_number": "C02XL0GTJGH5",
  "damage_description": "Screen is cracked in the top left corner, display flickering intermittently",
  "queue_id": 2,
  "apple_diagnostics": "ADP123456",
  "country": "Singapore",
  "priority": "High",
  "notes": "Customer reported device was dropped"
}
```

### Prompt for Mobile Agent
```
To create an Asset Repair ticket, I need:
1. The device serial number (scan or enter manually)
2. Describe the damage or issue in detail - what's wrong with the device?
3. Do you have an Apple diagnostics code? (optional)
4. Which country is the device located in?
5. Which queue should this be assigned to?
6. Priority level? (Low/Medium/High/Critical)
7. Any additional notes about how the damage occurred?
```

---

## 3. Asset Checkout (claw)

**Purpose**: Deploy/ship a device to a customer

### Required Fields
| Field | Type | Description |
|-------|------|-------------|
| `category` | string | Must be `"ASSET_CHECKOUT_CLAW"` |
| `serial_number` | string | Device serial number to checkout |
| `customer_id` | integer | Customer ID receiving the device |
| `shipping_address` | string | Full shipping address |
| `queue_id` | integer | Queue ID to assign the ticket |

### Optional Fields
| Field | Type | Description |
|-------|------|-------------|
| `shipping_tracking` | string | Tracking number if already shipped |
| `priority` | string | "Low", "Medium", "High", or "Critical" |
| `notes` | string | Special shipping instructions or notes |

### Example Request
```json
{
  "category": "ASSET_CHECKOUT_CLAW",
  "serial_number": "C02XL0GTJGH5",
  "customer_id": 42,
  "shipping_address": "123 Tech Park, #05-01, Singapore 123456",
  "queue_id": 3,
  "shipping_tracking": "SG123456789",
  "priority": "Medium",
  "notes": "Leave at reception if not available"
}
```

### Prompt for Mobile Agent
```
To create an Asset Checkout ticket, I need:
1. The device serial number (scan or enter manually)
2. Which customer is receiving this device? (search by name or email)
3. What is the full shipping address?
4. Do you have a tracking number? (optional - can add later)
5. Which queue should this be assigned to?
6. Priority level? (Low/Medium/High/Critical)
7. Any special shipping instructions?
```

---

## 4. Asset Return (claw)

**Purpose**: Process a device return from a customer

### Required Fields
| Field | Type | Description |
|-------|------|-------------|
| `category` | string | Must be `"ASSET_RETURN_CLAW"` |
| `customer_id` | integer | Customer returning the device |
| `return_address` | string | Address to pick up from / return address |
| `queue_id` | integer | Queue ID to assign the ticket |

### Optional Fields
| Field | Type | Description |
|-------|------|-------------|
| `subject` | string | Custom subject line |
| `outbound_tracking` | string | Outbound/pickup tracking number |
| `inbound_tracking` | string | Inbound/return tracking number |
| `damage_description` | string | Any reported issues with the device |
| `return_description` | string | Description of device condition |
| `priority` | string | "Low", "Medium", "High", or "Critical" |
| `notes` | string | Additional notes |

### Example Request
```json
{
  "category": "ASSET_RETURN_CLAW",
  "customer_id": 42,
  "return_address": "123 Tech Park, #05-01, Singapore 123456",
  "queue_id": 4,
  "damage_description": "Customer reports battery not holding charge",
  "return_description": "Device in good physical condition",
  "priority": "Medium",
  "notes": "Customer available 9am-5pm weekdays"
}
```

### Prompt for Mobile Agent
```
To create an Asset Return ticket, I need:
1. Which customer is returning a device? (search by name or email)
2. What is the pickup/return address?
3. Are there any reported issues with the device? (optional)
4. What is the condition of the device being returned? (optional)
5. Which queue should this be assigned to?
6. Priority level? (Low/Medium/High/Critical)
7. Any notes about pickup availability or special instructions?
```

---

## 5. Asset Intake

**Purpose**: Receive new assets into inventory

### Required Fields
| Field | Type | Description |
|-------|------|-------------|
| `category` | string | Must be `"ASSET_INTAKE"` |
| `title` | string | Title/subject for the intake |
| `description` | string | Description of assets being received |
| `queue_id` | integer | Queue ID to assign the ticket |

### Optional Fields
| Field | Type | Description |
|-------|------|-------------|
| `priority` | string | "Low", "Medium", "High", or "Critical" |
| `notes` | string | Additional notes |

### Example Request
```json
{
  "category": "ASSET_INTAKE",
  "title": "New MacBook Pro shipment - Q4 2024",
  "description": "Receiving 50 MacBook Pro 14\" M3 Pro units from Apple reseller. PO#: 2024-1234",
  "queue_id": 5,
  "priority": "Medium",
  "notes": "Expected delivery date: Dec 28, 2024"
}
```

### Prompt for Mobile Agent
```
To create an Asset Intake ticket, I need:
1. What is the title for this intake? (e.g., "New MacBook shipment - Dec 2024")
2. Describe what assets are being received (quantity, type, source, PO number if applicable)
3. Which queue should this be assigned to?
4. Priority level? (Low/Medium/High/Critical)
5. Any additional notes? (expected delivery date, special handling, etc.)
```

---

## 6. Internal Transfer

**Purpose**: Transfer device between customers/locations

### Required Fields
| Field | Type | Description |
|-------|------|-------------|
| `category` | string | Must be `"INTERNAL_TRANSFER"` |
| `offboarding_customer_id` | integer | Customer giving up the device |
| `offboarding_details` | string | Device details being transferred |
| `offboarding_address` | string | Pickup address |
| `onboarding_customer_id` | integer | Customer receiving the device |
| `onboarding_address` | string | Delivery address |
| `queue_id` | integer | Queue ID to assign the ticket |

### Optional Fields
| Field | Type | Description |
|-------|------|-------------|
| `serial_number` | string | Device serial number if known |
| `transfer_tracking` | string | Shipping/courier tracking link |
| `priority` | string | "Low", "Medium", "High", or "Critical" |
| `notes` | string | Additional notes |

### Example Request
```json
{
  "category": "INTERNAL_TRANSFER",
  "offboarding_customer_id": 42,
  "offboarding_details": "MacBook Pro 14\" M3 Pro, 18GB RAM, 512GB SSD",
  "offboarding_address": "123 Old Office, #05-01, Singapore 123456",
  "onboarding_customer_id": 55,
  "onboarding_address": "456 New Office, #10-02, Singapore 654321",
  "queue_id": 6,
  "serial_number": "C02XL0GTJGH5",
  "priority": "Medium",
  "notes": "Employee transfer between departments"
}
```

### Prompt for Mobile Agent
```
To create an Internal Transfer ticket, I need:

OFFBOARDING (device coming from):
1. Which customer is giving up the device?
2. What device is being transferred? (model, specs, serial number if known)
3. What is the pickup address?

ONBOARDING (device going to):
4. Which customer will receive the device?
5. What is the delivery address?

GENERAL:
6. Which queue should this be assigned to?
7. Priority level? (Low/Medium/High/Critical)
8. Any additional notes? (reason for transfer, timeline, etc.)
```

---

## 7. Bulk Delivery Quote

**Purpose**: Request quote for bulk device delivery

### Required Fields
| Field | Type | Description |
|-------|------|-------------|
| `category` | string | Must be `"BULK_DELIVERY_QUOTATION"` |
| `subject` | string | Subject/title for the quote request |
| `description` | string | Details of the bulk delivery needed |
| `queue_id` | integer | Queue ID to assign the ticket |

### Optional Fields
| Field | Type | Description |
|-------|------|-------------|
| `priority` | string | "Low", "Medium", "High", or "Critical" |
| `notes` | string | Additional notes |

### Example Request
```json
{
  "category": "BULK_DELIVERY_QUOTATION",
  "subject": "Bulk delivery quote - 100 MacBooks to 5 locations",
  "description": "Need quote for delivering 100 MacBook Air M2 units to 5 different office locations in Singapore. Locations: Raffles Place (30), Marina Bay (25), Orchard (20), Jurong (15), Changi (10). Preferred delivery window: Jan 15-20, 2025.",
  "queue_id": 7,
  "priority": "Medium",
  "notes": "Budget approval needed by Jan 5"
}
```

### Prompt for Mobile Agent
```
To create a Bulk Delivery Quote request, I need:
1. What is the subject/title for this quote?
2. Describe the bulk delivery requirements:
   - How many devices?
   - What type of devices?
   - How many locations?
   - What are the delivery addresses and quantities per location?
   - Preferred delivery timeline?
3. Which queue should this be assigned to?
4. Priority level? (Low/Medium/High/Critical)
5. Any additional notes? (budget constraints, special requirements, etc.)
```

---

## 8. Repair Quote

**Purpose**: Request quote for device repair

### Required Fields
| Field | Type | Description |
|-------|------|-------------|
| `category` | string | Must be `"REPAIR_QUOTE"` |
| `subject` | string | Subject/title for the repair quote |
| `description` | string | Details of the repair needed |
| `queue_id` | integer | Queue ID to assign the ticket |

### Optional Fields
| Field | Type | Description |
|-------|------|-------------|
| `serial_number` | string | Device serial number if known |
| `priority` | string | "Low", "Medium", "High", or "Critical" |
| `notes` | string | Additional notes |

### Example Request
```json
{
  "category": "REPAIR_QUOTE",
  "subject": "Repair quote - MacBook Pro screen replacement",
  "description": "Need quote for screen replacement on MacBook Pro 14\" M3. Screen has vertical lines and dead pixels. Device is out of warranty.",
  "queue_id": 8,
  "serial_number": "C02XL0GTJGH5",
  "priority": "Medium",
  "notes": "Customer wants to compare repair cost vs replacement"
}
```

### Prompt for Mobile Agent
```
To create a Repair Quote request, I need:
1. What is the subject/title for this quote?
2. Describe the repair needed:
   - What device?
   - What is the issue/damage?
   - Is it under warranty?
3. Do you have the device serial number? (optional)
4. Which queue should this be assigned to?
5. Priority level? (Low/Medium/High/Critical)
6. Any additional notes?
```

---

## 9. ITAD Quote (IT Asset Disposal)

**Purpose**: Request quote for IT asset disposal

### Required Fields
| Field | Type | Description |
|-------|------|-------------|
| `category` | string | Must be `"ITAD_QUOTE"` |
| `subject` | string | Subject/title for the ITAD quote |
| `description` | string | Details of assets for disposal |
| `queue_id` | integer | Queue ID to assign the ticket |

### Optional Fields
| Field | Type | Description |
|-------|------|-------------|
| `priority` | string | "Low", "Medium", "High", or "Critical" |
| `notes` | string | Additional notes |

### Example Request
```json
{
  "category": "ITAD_QUOTE",
  "subject": "ITAD Quote - End of life MacBooks and accessories",
  "description": "Need quote for secure disposal and data destruction of: 25 MacBook Pro (2018-2020 models), 30 MacBook Air (2019 models), 50 USB-C docks, 75 external keyboards. All devices contain sensitive corporate data - require certificate of destruction.",
  "queue_id": 9,
  "priority": "Medium",
  "notes": "Compliance requirement - need destruction certificates for audit"
}
```

### Prompt for Mobile Agent
```
To create an ITAD (IT Asset Disposal) Quote request, I need:
1. What is the subject/title for this quote?
2. Describe the assets for disposal:
   - What types of devices/equipment?
   - How many of each?
   - Age/model years?
   - Do they contain sensitive data?
   - Do you need certificates of destruction?
3. Which queue should this be assigned to?
4. Priority level? (Low/Medium/High/Critical)
5. Any compliance or audit requirements?
```

---

## Helper Endpoints

### Search Assets
```
GET /api/v1/assets/search?q={serial_or_tag}
```
Use this to find assets by serial number or asset tag before creating tickets that require an asset.

### Get Customers
```
GET /api/v1/customers?search={name_or_email}
```
Use this to find customers before creating tickets that require customer selection.

### Get Queues
```
GET /api/v1/queues
```
Use this to get the list of available queues for ticket assignment.

### Get Categories
```
GET /api/v1/tickets/categories
```
Returns full list of categories with their required and optional fields.

---

## Error Handling

All endpoints return errors in this format:
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Serial number is required for PIN Request"
  }
}
```

Common error codes:
- `AUTH_ERROR` - Authentication failed
- `VALIDATION_ERROR` - Required field missing or invalid
- `RESOURCE_NOT_FOUND` - Asset or customer not found
- `INTERNAL_ERROR` - Server error
