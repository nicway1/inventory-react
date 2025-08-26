# Audit API Documentation

## Overview
This document describes the REST API endpoints for the Inventory Audit feature designed for iOS app integration.

## Base URL
All endpoints use the base URL: `/api/v1`

## Authentication
All audit endpoints require JWT authentication via the `Authorization` header:
```
Authorization: Bearer <jwt_token>
```

Get a JWT token using the `/api/v1/auth/login` endpoint.

## Permissions
Users must have the appropriate audit permissions:
- `can_access_inventory_audit` - Required for all audit operations
- `can_start_inventory_audit` - Required to start new audits
- `can_view_audit_reports` - Required to view audit details

## API Endpoints

### 1. Get Audit Status
**GET** `/api/v1/audit/status`

Returns the current active audit session if one exists.

**Response:**
```json
{
  "data": {
    "current_audit": {
      "id": "audit_1640995200",
      "country": "SINGAPORE",
      "total_assets": 150,
      "scanned_count": 75,
      "missing_count": 10,
      "unexpected_count": 2,
      "completion_percentage": 50.0,
      "started_at": "2023-12-31T12:00:00Z",
      "started_by": 123,
      "is_active": true
    }
  },
  "success": true,
  "message": "Active audit session retrieved"
}
```

If no active audit:
```json
{
  "data": {
    "current_audit": null
  },
  "success": true,
  "message": "No active audit session"
}
```

### 2. Get Available Countries
**GET** `/api/v1/audit/countries`

Returns list of countries the user can audit based on their permissions.

**Response:**
```json
{
  "data": {
    "countries": ["SINGAPORE", "MALAYSIA", "THAILAND"]
  },
  "success": true,
  "message": "Available countries retrieved"
}
```

### 3. Start Audit
**POST** `/api/v1/audit/start`

Starts a new audit session for the specified country.

**Request Body:**
```json
{
  "country": "SINGAPORE"
}
```

**Response:**
```json
{
  "data": {
    "audit": {
      "id": "audit_1640995200",
      "country": "SINGAPORE",
      "total_assets": 150,
      "scanned_count": 0,
      "missing_count": 0,
      "unexpected_count": 0,
      "completion_percentage": 0,
      "started_at": "2023-12-31T12:00:00Z",
      "started_by": 123,
      "is_active": true
    }
  },
  "success": true,
  "message": "Audit started successfully for SINGAPORE"
}
```

### 4. Scan Asset
**POST** `/api/v1/audit/scan`

Scans an asset during an active audit session.

**Request Body:**
```json
{
  "identifier": "ASSET_TAG_001"
}
```

**Response (Expected Asset Found):**
```json
{
  "data": {
    "status": "found_expected",
    "message": "Asset ASSET_TAG_001 scanned successfully",
    "asset": {
      "id": 456,
      "asset_tag": "ASSET_TAG_001",
      "serial_num": "SN123456",
      "name": "Dell Laptop",
      "model": "Latitude 5520",
      "status": "DEPLOYED",
      "location": "Singapore Office",
      "company": "Company ABC"
    },
    "progress": {
      "total_assets": 150,
      "scanned_count": 76,
      "unexpected_count": 2,
      "completion_percentage": 50.67
    }
  },
  "success": true,
  "message": "Asset scan processed"
}
```

**Response (Unexpected Asset):**
```json
{
  "data": {
    "status": "unexpected",
    "message": "Asset UNKNOWN_TAG not found in expected inventory (recorded as unexpected)",
    "asset": {
      "identifier": "UNKNOWN_TAG",
      "scanned_at": "2023-12-31T12:30:00",
      "type": "unexpected"
    },
    "progress": {
      "total_assets": 150,
      "scanned_count": 75,
      "unexpected_count": 3,
      "completion_percentage": 50.0
    }
  },
  "success": true,
  "message": "Asset scan processed"
}
```

### 5. End Audit
**POST** `/api/v1/audit/end`

Ends the current active audit session and generates a final report.

**Response:**
```json
{
  "data": {
    "final_report": {
      "audit_id": "audit_1640995200",
      "country": "SINGAPORE",
      "started_at": "2023-12-31T12:00:00Z",
      "completed_at": "2023-12-31T15:00:00Z",
      "summary": {
        "total_expected": 150,
        "total_scanned": 140,
        "total_missing": 10,
        "total_unexpected": 3,
        "completion_percentage": 93.33
      }
    }
  },
  "success": true,
  "message": "Audit session ended successfully"
}
```

### 6. Get Asset Details
**GET** `/api/v1/audit/details/{detail_type}`

Returns detailed lists of assets from the current audit.

**Parameters:**
- `detail_type`: One of `total`, `scanned`, `missing`, `unexpected`

**Response:**
```json
{
  "data": {
    "detail_type": "missing",
    "title": "Missing Assets (10)",
    "count": 10,
    "assets": [
      {
        "id": 789,
        "asset_tag": "MISSING_001",
        "serial_num": "SN789012",
        "name": "HP Monitor",
        "model": "E243i",
        "status": "DEPLOYED",
        "location": "Singapore Office",
        "company": "Company ABC"
      }
    ]
  },
  "success": true,
  "message": "Retrieved missing asset details"
}
```

## Error Responses

All endpoints return standardized error responses:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": {
      "timestamp": "2023-12-31T12:00:00Z"
    }
  }
}
```

### Common Error Codes
- `MISSING_TOKEN` (401): Authorization header missing
- `INVALID_TOKEN` (401): Invalid or expired JWT token
- `INSUFFICIENT_PERMISSIONS` (403): User lacks required permissions
- `VALIDATION_ERROR` (400): Invalid request data
- `NO_ACTIVE_AUDIT` (400): No active audit session found
- `AUDIT_ALREADY_ACTIVE` (400): Cannot start audit when one is already active
- `ALREADY_SCANNED` (400): Asset has already been scanned
- `INTERNAL_ERROR` (500): Server error

## Usage Flow

1. **Login**: Use `/auth/login` to get JWT token
2. **Check Status**: Call `/audit/status` to see if audit is running
3. **Get Countries**: Call `/audit/countries` to see available countries
4. **Start Audit**: Call `/audit/start` with selected country
5. **Scan Assets**: Repeatedly call `/audit/scan` for each asset
6. **Monitor Progress**: Check `/audit/status` for real-time progress
7. **View Details**: Use `/audit/details/{type}` to see asset lists
8. **End Audit**: Call `/audit/end` when finished

## iOS Integration Notes

- All timestamps are in ISO 8601 format with 'Z' suffix (UTC)
- Asset identifiers can be asset tags or serial numbers
- Progress percentages are decimal values (0-100)
- The API handles both expected assets and unexpected finds
- Real-time updates available through repeated status calls
- All responses follow the same structure for easy parsing