# Queue API Testing Guide

## Overview

This guide helps you test the queue functionality that was added to the mobile API. After pulling the latest code from GitHub to PythonAnywhere, use these tests to verify everything is working.

---

## Prerequisites

1. ✅ Latest code deployed to PythonAnywhere
2. ✅ Web app reloaded on PythonAnywhere
3. ✅ Valid API key with `tickets:read` permission
4. ✅ At least one queue configured in the system
5. ✅ At least one ticket in the system

---

## Quick Test (Command Line)

### Option 1: Using the Test Script

```bash
# Make script executable (first time only)
chmod +x test_queue_api_simple.sh

# Run the test
./test_queue_api_simple.sh
```

When prompted, enter your API key. The script will test all queue-related endpoints and show you the results.

### Option 2: Using Python Script

```bash
# Run the comprehensive Python test
python3 test_queue_api.py
```

This will test all endpoints and verify that queue fields are present in responses.

---

## Manual Testing with cURL

### 1. Test GET /api/v1/queues

**Request:**
```bash
curl -X GET \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  "https://inventory.truelog.com.sg/api/v1/queues"
```

**Expected Response (200 OK):**
```json
{
  "success": true,
  "message": "Retrieved 3 queues",
  "data": [
    {
      "id": 1,
      "name": "General Support",
      "description": null
    },
    {
      "id": 2,
      "name": "IT Support",
      "description": null
    },
    {
      "id": 3,
      "name": "Shipping",
      "description": null
    }
  ]
}
```

**What to Check:**
- ✅ Status code is 200
- ✅ `success` is `true`
- ✅ `data` contains an array of queues
- ✅ Each queue has `id`, `name`, and `description` fields

---

### 2. Test GET /api/v1/tickets (with queue fields)

**Request:**
```bash
curl -X GET \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  "https://inventory.truelog.com.sg/api/v1/tickets?per_page=5"
```

**Expected Response (200 OK):**
```json
{
  "success": true,
  "message": "Retrieved 5 tickets",
  "data": [
    {
      "id": 123,
      "subject": "Need new laptop",
      "description": "Current laptop is broken",
      "status": "Open",
      "priority": "High",
      "category": "Hardware",
      "queue_id": 2,
      "queue_name": "IT Support",
      "customer_id": 45,
      "customer_name": "John Doe",
      "customer_email": "john@example.com",
      "assigned_to_id": 10,
      "assigned_to_name": "Sarah Tech",
      "created_at": "2025-01-15T10:30:00",
      "updated_at": "2025-01-15T14:20:00"
    }
  ],
  "metadata": {
    "pagination": {
      "page": 1,
      "per_page": 5,
      "total": 25,
      "pages": 5
    }
  }
}
```

**What to Check:**
- ✅ Status code is 200
- ✅ Each ticket has `queue_id` field (can be null)
- ✅ Each ticket has `queue_name` field (can be null)
- ✅ Queue name matches the queue ID

---

### 3. Test GET /api/v1/tickets with Queue Filter

**Request:**
```bash
curl -X GET \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  "https://inventory.truelog.com.sg/api/v1/tickets?queue_id=2&per_page=5"
```

**Expected Response:**
- ✅ Status code is 200
- ✅ Only tickets with `queue_id: 2` are returned
- ✅ All returned tickets have `queue_name: "IT Support"` (or whatever queue 2 is named)

---

### 4. Test GET /api/v1/tickets/{id}

**Request:**
```bash
# Replace 123 with an actual ticket ID from your system
curl -X GET \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  "https://inventory.truelog.com.sg/api/v1/tickets/123"
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Retrieved ticket 123",
  "data": {
    "id": 123,
    "subject": "Need new laptop",
    "queue_id": 2,
    "queue_name": "IT Support",
    "comments": [...],
    "attachments": [...]
  }
}
```

**What to Check:**
- ✅ Status code is 200
- ✅ Ticket has `queue_id` field
- ✅ Ticket has `queue_name` field

---

### 5. Test GET /api/v1/sync/tickets (Updated Endpoint)

**Request:**
```bash
curl -X GET \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  "https://inventory.truelog.com.sg/api/v1/sync/tickets?limit=5"
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Retrieved 5 tickets for sync",
  "data": [
    {
      "id": 123,
      "subject": "Need new laptop",
      "status": "Open",
      "priority": "High",
      "category": "Hardware",
      "queue_id": 2,
      "queue_name": "IT Support",
      "customer_id": 45,
      "customer_name": "John Doe",
      "assigned_to_id": 10,
      "assigned_to_name": "Sarah Tech",
      "created_at": "2025-01-15T10:30:00",
      "updated_at": "2025-01-15T14:20:00",
      "sync_timestamp": "2025-01-15T15:00:00"
    }
  ],
  "metadata": {
    "next_sync_timestamp": "2025-01-15T14:20:00",
    "has_more": false
  }
}
```

**What to Check (NEW FIELDS):**
- ✅ Each ticket has `queue_name` field (this is NEW)
- ✅ Each ticket has `category` field (this is NEW)
- ✅ Each ticket has `customer_name` field (this is NEW)
- ✅ Each ticket has `assigned_to_name` field (this is NEW)

---

## Common Issues and Solutions

### Issue 1: 404 Not Found on /api/v1/queues

**Problem:** Endpoint doesn't exist

**Solution:**
1. Make sure you pulled the latest code: `git pull origin main`
2. Reload your PythonAnywhere web app
3. Clear any Python cache: `find . -name "*.pyc" -delete`

---

### Issue 2: 401 Unauthorized

**Problem:** Invalid or missing API key

**Solution:**
1. Verify your API key is valid
2. Check that the API key has `tickets:read` permission
3. Make sure you're using the correct header: `Authorization: Bearer YOUR_KEY`

---

### Issue 3: Queue fields are null

**Problem:** Tickets don't have queue assignments

**Solution:**
1. This is normal if tickets haven't been assigned to queues yet
2. Test with tickets that have queue assignments
3. Or assign some tickets to queues through the web interface

---

### Issue 4: queue_name missing in sync endpoint

**Problem:** Old code is still running

**Solution:**
1. Pull latest code: `git pull origin main`
2. Reload PythonAnywhere web app
3. Clear browser cache
4. Test again

---

## Verification Checklist

Use this checklist to verify all queue functionality is working:

- [ ] `/api/v1/queues` endpoint returns 200 OK
- [ ] Queues list contains at least one queue
- [ ] Each queue has `id`, `name`, and `description` fields
- [ ] `/api/v1/tickets` includes `queue_id` and `queue_name` in response
- [ ] Filtering by `queue_id` parameter works correctly
- [ ] Single ticket endpoint includes queue fields
- [ ] Sync endpoint includes new fields: `queue_name`, `category`, `customer_name`, `assigned_to_name`
- [ ] All endpoints return proper JSON responses
- [ ] No 500 Internal Server Errors
- [ ] API key authentication works

---

## Testing from Mobile App

Once API tests pass, test from your mobile app:

### 1. Test Queue Fetching
```dart
final queues = await apiService.fetchQueues();
print('Fetched ${queues.length} queues');
```

**Expected:** Should return list of Queue objects

### 2. Test Ticket Listing with Queue Data
```dart
final tickets = await apiService.fetchTickets();
print('First ticket queue: ${tickets.first.queueName}');
```

**Expected:** Tickets should have queueName populated

### 3. Test Queue Filtering
```dart
final tickets = await apiService.fetchTickets(queueId: 2);
print('Filtered ${tickets.length} tickets for queue 2');
```

**Expected:** Only tickets from queue 2 should be returned

---

## Support

If you encounter any issues:

1. Check the error message in the API response
2. Verify PythonAnywhere error logs
3. Ensure latest code is deployed
4. Verify database has queue data
5. Check API key permissions

---

## Quick Reference

| Endpoint | Method | Purpose | New? |
|----------|--------|---------|------|
| `/api/v1/queues` | GET | List all queues | ✅ NEW |
| `/api/v1/tickets` | GET | List tickets (includes queue fields) | Updated |
| `/api/v1/tickets?queue_id=X` | GET | Filter by queue | Existing |
| `/api/v1/tickets/{id}` | GET | Get ticket (includes queue fields) | Updated |
| `/api/v1/sync/tickets` | GET | Sync tickets (enhanced fields) | ✅ Updated |

**All endpoints require:** `Authorization: Bearer YOUR_API_KEY`

**All endpoints return:** JSON with `success`, `message`, and `data` fields

---

**Last Updated:** 2025-01-15
**API Version:** 1.0.0
