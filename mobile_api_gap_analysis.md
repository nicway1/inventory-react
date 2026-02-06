# TrueLog Mobile API Gap Analysis Report

**Report Date:** February 6, 2026
**Document Version:** 1.0
**Prepared for:** iOS App Development Team

---

## 1. Executive Summary

This report provides a comprehensive analysis of functionality gaps between the TrueLog mobile API (65 endpoints) and the web application (400+ features). The mobile API currently supports read-heavy operations focused on ticket viewing, asset/accessory browsing, and tracking management. However, significant gaps exist in ticket lifecycle management, asset transfers, accessory checkout, customer management, and administrative functions.

### Key Findings

| Category | Mobile API | Web App | Gap Level |
|----------|-----------|---------|-----------|
| Ticket Management | View + Add Assets | Full CRUD + Workflow | **CRITICAL** |
| Asset Management | Create + View + Images | Full CRUD + Transfer + Bulk | **HIGH** |
| Accessory Management | View + Search + Images | Full CRUD + Checkout/Checkin | **HIGH** |
| Customer Management | None | Full CRUD | **CRITICAL** |
| Tracking | View + Mark Received | Full CRUD + Multi-carrier | **MEDIUM** |
| Comments | Read Only | Full CRUD | **HIGH** |
| Reporting | None | Full Analytics | **MEDIUM** |
| Admin Functions | None | Full Management | **LOW** (intentional) |

### Quick Win Opportunity
**16 critical features can be immediately enabled** by allowing the iOS app to use existing API v2 endpoints with JWT authentication. No new backend development required.

---

## 2. Critical Missing Features (HIGH PRIORITY)

These features are essential for daily operations and should be prioritized for implementation.

### 2.1 Ticket Lifecycle Management

| Missing Feature | Impact | Business Need |
|-----------------|--------|---------------|
| **Create Ticket** | CRITICAL | Field technicians cannot create service requests |
| **Edit Ticket** | CRITICAL | Cannot update ticket details or correct errors |
| **Change Ticket Status** | CRITICAL | Cannot progress tickets through workflow |
| **Assign/Reassign Ticket** | HIGH | Cannot delegate work in the field |
| **Add Comments** | CRITICAL | Cannot communicate updates or notes |
| **Delete Ticket** | MEDIUM | Less common, but needed for corrections |

**Current Mobile API Ticket Endpoints:**
- `GET /tickets` - List tickets (paginated)
- `GET /tickets/<id>` - View ticket detail
- `GET /tickets/<id>/assets` - View ticket assets
- `POST /tickets/<id>/assets` - Add asset to ticket

**Missing Operations:**
- `POST /tickets` - Create new ticket
- `PUT /tickets/<id>` - Update ticket
- `POST /tickets/<id>/status` - Change status
- `POST /tickets/<id>/assign` - Assign ticket
- `POST /tickets/<id>/comments` - Add comment
- `DELETE /tickets/<id>` - Delete ticket

### 2.2 Customer Management

| Missing Feature | Impact | Business Need |
|-----------------|--------|---------------|
| **List Customers** | HIGH | Cannot look up customer information |
| **Create Customer** | CRITICAL | Cannot onboard new customers in field |
| **View Customer** | HIGH | Cannot see customer details |
| **Edit Customer** | MEDIUM | Cannot update customer information |
| **Search Customers** | HIGH | Cannot find customers quickly |

**Current Mobile API:** No customer endpoints exist.

### 2.3 Comment Management

| Missing Feature | Impact | Business Need |
|-----------------|--------|---------------|
| **Add Comment** | CRITICAL | Cannot log work notes or updates |
| **Edit Comment** | MEDIUM | Cannot correct comment errors |
| **Delete Comment** | LOW | Rarely needed |
| **@Mention Users** | MEDIUM | Cannot notify team members |

**Current Status:** Comments are read-only (returned in ticket detail but cannot be created).

---

## 3. Important Missing Features (MEDIUM PRIORITY)

These features significantly impact productivity but have workarounds.

### 3.1 Asset Management Gaps

| Missing Feature | Impact | Currently Available |
|-----------------|--------|---------------------|
| **Edit Asset** | HIGH | View, Create, Search, Images |
| **Delete/Archive Asset** | MEDIUM | Cannot remove erroneous entries |
| **Transfer Asset** | HIGH | Cannot reassign to different customer |
| **Bulk Operations** | MEDIUM | Cannot check in/out multiple assets |
| **Asset History** | LOW | Cannot view change log |

**Current Mobile API Asset Endpoints:**
- `GET /inventory` - List assets with filters
- `POST /assets` - Create new asset
- `GET /assets/search` - Search assets
- `GET /assets/<id>/label` - Generate label
- `POST/GET/DELETE /assets/<id>/image` - Manage images

**Missing Operations:**
- `PUT /assets/<id>` - Update asset
- `DELETE /assets/<id>` - Delete/archive asset
- `POST /assets/<id>/transfer` - Transfer to customer

### 3.2 Accessory Management Gaps

| Missing Feature | Impact | Currently Available |
|-----------------|--------|---------------------|
| **Create Accessory** | HIGH | View, Search, Images |
| **Edit Accessory** | MEDIUM | Cannot update quantities or details |
| **Delete Accessory** | LOW | Cannot remove entries |
| **Checkout Accessory** | CRITICAL | Cannot assign to customers |
| **Checkin Accessory** | CRITICAL | Cannot return from customers |

**Current Mobile API Accessory Endpoints:**
- `GET /accessories` - List accessories with filters
- `GET /accessories/<id>` - View accessory detail
- `GET /accessories/search` - Search accessories
- `POST/GET/DELETE /accessories/<id>/image` - Manage images

**Missing Operations:**
- `POST /accessories` - Create accessory
- `PUT /accessories/<id>` - Update accessory
- `DELETE /accessories/<id>` - Delete accessory
- `POST /accessories/<id>/checkout` - Checkout to customer
- `POST /accessories/<id>/checkin` - Checkin from customer

### 3.3 Tracking Management Gaps

| Missing Feature | Impact | Currently Available |
|-----------------|--------|---------------------|
| **Add Tracking Number** | HIGH | View, Mark Received, Refresh |
| **Edit Tracking** | MEDIUM | Cannot correct tracking numbers |
| **Delete Tracking** | LOW | Cannot remove incorrect entries |

**Current Mobile API Tracking Endpoints:**
- `GET /tracking/outbound` - List outbound tracking
- `GET /tracking/return` - List return tracking
- `POST /tracking/outbound/<id>/mark-received` - Mark delivered
- `POST /tracking/return/<id>/mark-received` - Mark received
- `POST /tracking/lookup` - Lookup tracking number
- `GET/POST /tickets/<id>/tracking/*` - Various tracking operations

**Missing Operations:**
- `POST /tickets/<id>/tracking` - Add tracking number
- `PUT /tickets/<id>/tracking` - Update tracking
- `DELETE /tickets/<id>/tracking` - Remove tracking

---

## 4. Nice-to-Have Features (LOW PRIORITY)

These features would enhance the experience but are not essential for core operations.

### 4.1 Reporting & Analytics
- Dashboard widgets with custom metrics
- Report generation and export
- Asset utilization reports
- Ticket performance metrics
- SLA compliance reports

### 4.2 Administrative Functions
- User management
- Company management
- Queue management
- Permission management
- System settings

### 4.3 Knowledge Base
- Search knowledge articles
- View troubleshooting guides
- Create/edit articles (admin)

### 4.4 Queue Management
- View queues
- Move tickets between queues
- Queue assignment rules

### 4.5 Advanced Features
- Bulk asset checkout
- Bulk accessory checkout
- Import/export functionality
- Barcode batch scanning
- Offline mode support

---

## 5. API Cross-Compatibility Table

The following table shows which missing mobile features can be immediately enabled using existing API v2 endpoints. All API v2 endpoints support JWT authentication via the `dual_auth_required` decorator.

### 5.1 Features Available via API v2 (Quick Wins)

| Missing Feature | API v2 Endpoint | Auth Method | Ready to Use |
|-----------------|-----------------|-------------|--------------|
| **Create Ticket** | `POST /api/v2/tickets` | JWT Bearer | YES |
| **Update Ticket** | `PUT /api/v2/tickets/<id>` | JWT Bearer | YES |
| **Assign Ticket** | `POST /api/v2/tickets/<id>/assign` | JWT Bearer | YES |
| **Change Status** | `POST /api/v2/tickets/<id>/status` | JWT Bearer | YES |
| **Update Asset** | `PUT /api/v2/assets/<id>` | JWT Bearer | YES |
| **Delete Asset** | `DELETE /api/v2/assets/<id>` | JWT Bearer | YES |
| **Transfer Asset** | `POST /api/v2/assets/<id>/transfer` | JWT Bearer | YES |
| **Create Accessory** | `POST /api/v2/accessories` | JWT Bearer | YES |
| **Update Accessory** | `PUT /api/v2/accessories/<id>` | JWT Bearer | YES |
| **Delete Accessory** | `DELETE /api/v2/accessories/<id>` | JWT Bearer | YES |
| **Return Accessory** | `POST /api/v2/accessories/<id>/return` | JWT Bearer | YES |
| **Checkin Accessory** | `POST /api/v2/accessories/<id>/checkin` | JWT Bearer | YES |
| **List Customers** | `GET /api/v2/customers` | JWT Bearer | YES |
| **Create Customer** | `POST /api/v2/customers` | JWT Bearer | YES |
| **Update Customer** | `PUT /api/v2/customers/<id>` | JWT Bearer | YES |
| **Delete Customer** | `DELETE /api/v2/customers/<id>` | JWT Bearer | YES |

### 5.2 API v2 Endpoints Reference

#### Tickets (api_v2/tickets.py)
```
GET    /api/v2/tickets              - List tickets with pagination/filtering
POST   /api/v2/tickets              - Create new ticket
PUT    /api/v2/tickets/<id>         - Update ticket
POST   /api/v2/tickets/<id>/assign  - Assign to user
POST   /api/v2/tickets/<id>/status  - Change status
```

#### Assets (api_v2/assets.py)
```
POST   /api/v2/assets               - Create asset
PUT    /api/v2/assets/<id>          - Update asset
DELETE /api/v2/assets/<id>          - Delete/archive asset
POST   /api/v2/assets/<id>/image    - Upload image
POST   /api/v2/assets/<id>/transfer - Transfer to customer
```

#### Accessories (api_v2/accessories.py)
```
POST   /api/v2/accessories              - Create accessory
PUT    /api/v2/accessories/<id>         - Update accessory
DELETE /api/v2/accessories/<id>         - Delete accessory
POST   /api/v2/accessories/<id>/return  - Return accessory
POST   /api/v2/accessories/<id>/checkin - Checkin from customer
```

#### Customers (api_v2/customers.py)
```
GET    /api/v2/customers            - List customers
POST   /api/v2/customers            - Create customer
GET    /api/v2/customers/<id>       - Get customer
PUT    /api/v2/customers/<id>       - Update customer
DELETE /api/v2/customers/<id>       - Delete customer
GET    /api/v2/customers/<id>/tickets - Get customer tickets
```

#### Service Records (api_v2/service_records.py)
```
GET    /api/v2/tickets/<id>/service-records      - List records
POST   /api/v2/tickets/<id>/service-records      - Create record
PUT    /api/v2/tickets/<id>/service-records/<id> - Update record
DELETE /api/v2/tickets/<id>/service-records/<id> - Delete record
```

#### Attachments (api_v2/attachments.py)
```
POST   /api/v2/tickets/<id>/attachments - Upload attachment
GET    /api/v2/tickets/<id>/attachments - List attachments
DELETE /api/v2/tickets/<id>/attachments/<id> - Delete attachment
```

### 5.3 Features NOT Available in API v2 (Require New Development)

| Missing Feature | Status | Recommended Action |
|-----------------|--------|-------------------|
| Add Comment | Not in v2 | Create new endpoint |
| Add Tracking Number | Not in v2 | Create new endpoint |
| Edit Tracking Number | Not in v2 | Create new endpoint |
| Accessory Checkout | Not in v2 | Create new endpoint |
| Queue Management | Admin only | Consider mobile admin role |
| Knowledge Base | Not exposed | Lower priority |

---

## 6. Recommended New Mobile Endpoints

The following endpoints should be developed to fill critical gaps not covered by API v2.

### 6.1 Comment Management (Priority: CRITICAL)

```
POST   /api/mobile/v1/tickets/<id>/comments
       Body: { "content": "...", "is_internal": false }
       Response: { "success": true, "comment": {...} }

PUT    /api/mobile/v1/tickets/<id>/comments/<comment_id>
       Body: { "content": "..." }
       Response: { "success": true, "comment": {...} }

DELETE /api/mobile/v1/tickets/<id>/comments/<comment_id>
       Response: { "success": true }
```

### 6.2 Tracking Number Management (Priority: HIGH)

```
POST   /api/mobile/v1/tickets/<id>/tracking
       Body: {
           "tracking_number": "...",
           "carrier": "SingPost",
           "type": "outbound",  // or "return"
           "slot": 1  // 1-5
       }
       Response: { "success": true, "tracking": {...} }

PUT    /api/mobile/v1/tickets/<id>/tracking/<slot>
       Body: { "tracking_number": "...", "carrier": "..." }
       Response: { "success": true, "tracking": {...} }

DELETE /api/mobile/v1/tickets/<id>/tracking/<slot>
       Response: { "success": true }
```

### 6.3 Accessory Checkout (Priority: HIGH)

```
POST   /api/mobile/v1/accessories/<id>/checkout
       Body: {
           "customer_id": 123,
           "quantity": 1,
           "notes": "...",
           "ticket_id": 456  // optional
       }
       Response: {
           "success": true,
           "transaction": {...},
           "accessory": {...}
       }
```

### 6.4 Ticket Delete (Priority: MEDIUM)

```
DELETE /api/mobile/v1/tickets/<id>
       Query: ?mode=soft  // or "hard" for admin
       Response: { "success": true }
```

---

## 7. Quick Wins - Immediate Implementation

The iOS app can immediately use the following API v2 endpoints with the existing JWT token from mobile login. **No backend changes required.**

### 7.1 Implementation Steps

1. **Use same JWT token** - The mobile API JWT token works with API v2 endpoints
2. **Change base URL** - Use `/api/v2/` instead of `/api/mobile/v1/`
3. **Handle response format** - API v2 uses `{ success, data, message, meta }` format

### 7.2 Priority Quick Wins (Week 1)

| Feature | Endpoint | Effort |
|---------|----------|--------|
| Create Ticket | `POST /api/v2/tickets` | Low |
| Update Ticket | `PUT /api/v2/tickets/<id>` | Low |
| Change Status | `POST /api/v2/tickets/<id>/status` | Low |
| Assign Ticket | `POST /api/v2/tickets/<id>/assign` | Low |

### 7.3 Secondary Quick Wins (Week 2)

| Feature | Endpoint | Effort |
|---------|----------|--------|
| Update Asset | `PUT /api/v2/assets/<id>` | Low |
| Delete Asset | `DELETE /api/v2/assets/<id>` | Low |
| Transfer Asset | `POST /api/v2/assets/<id>/transfer` | Low |
| Customer CRUD | `/api/v2/customers/*` | Low |

### 7.4 Tertiary Quick Wins (Week 3)

| Feature | Endpoint | Effort |
|---------|----------|--------|
| Create Accessory | `POST /api/v2/accessories` | Low |
| Update Accessory | `PUT /api/v2/accessories/<id>` | Low |
| Checkin Accessory | `POST /api/v2/accessories/<id>/checkin` | Low |
| Return Accessory | `POST /api/v2/accessories/<id>/return` | Low |

---

## 8. Summary

### Current State
- Mobile API: **65 endpoints** focused on read operations
- Web App: **400+ features** with full CRUD and workflow support
- Coverage: Approximately **16% functional parity**

### Recommended Actions

1. **Immediate (Week 1-2):** Enable 16 API v2 endpoints in iOS app
   - Ticket create/update/status/assign
   - Asset update/delete/transfer
   - Customer CRUD
   - Accessory update/checkin

2. **Short-term (Week 3-4):** Develop 4 new mobile endpoints
   - Comment CRUD
   - Tracking number management
   - Accessory checkout

3. **Medium-term (Month 2):** Enhance mobile features
   - Bulk operations
   - Offline mode
   - Push notifications

### Expected Outcome

After implementing quick wins and new endpoints:
- Mobile API: **~80 endpoints** (current 65 + 16 v2 direct use)
- Functional parity: **~35%** (up from 16%)
- Critical daily operations: **100% covered**

---

## Appendix A: Current Mobile API Endpoint Summary

### Authentication (2 endpoints)
- `POST /auth/login`
- `GET /auth/me`

### Tickets (12 endpoints)
- `GET /tickets`
- `GET /tickets/<id>`
- `GET /tickets/<id>/assets`
- `POST /tickets/<id>/assets`
- `GET /tickets/<id>/attachments`
- `POST /tickets/<id>/attachments`
- `DELETE /tickets/<id>/attachments/<id>`
- `GET /tickets/<id>/attachments/<id>/download`
- `POST /tickets/<id>/checkin`
- `GET /tickets/<id>/checkin-status`
- `GET /tickets/<id>/intake-assets`
- `POST /tickets/<id>/undo-checkin/<asset_id>`
- `POST /tickets/<id>/update-serial-checkin`
- `POST /tickets/<id>/create-assets-from-text`

### Assets (9 endpoints)
- `POST /assets`
- `GET /assets/search`
- `GET /assets/<id>/label`
- `GET /assets/<id>/image`
- `POST /assets/<id>/image`
- `DELETE /assets/<id>/image`
- `GET /assets/<id>/service-records`

### Accessories (6 endpoints)
- `GET /accessories`
- `GET /accessories/<id>`
- `GET /accessories/search`
- `GET /accessories/<id>/image`
- `POST /accessories/<id>/image`
- `DELETE /accessories/<id>/image`

### Tracking (10 endpoints)
- `GET /tracking/outbound`
- `GET /tracking/return`
- `POST /tracking/outbound/<id>/mark-received`
- `POST /tracking/return/<id>/mark-received`
- `POST /tracking/lookup`
- `GET /tickets/<id>/tracking`
- `POST /tickets/<id>/tracking/refresh`
- `POST /tickets/<id>/tracking/outbound/received`
- `POST /tickets/<id>/tracking/return/received`

### Inventory (1 endpoint)
- `GET /inventory`

### Dashboard (1 endpoint)
- `GET /dashboard`

### Specs/Device Integration (5 endpoints)
- `GET /specs`
- `GET /specs/<id>`
- `POST /specs/<id>/create-asset`
- `POST /specs/<id>/mark-processed`
- `GET /specs/<id>/find-tickets`
- `POST /specs/<id>/create-asset-with-ticket`

### Service Records (5 endpoints)
- `GET /tickets/<id>/service-records`
- `POST /tickets/<id>/service-records`
- `GET /tickets/<id>/service-records/<id>`
- `PUT /tickets/<id>/service-records/<id>/status`
- `DELETE /tickets/<id>/service-records/<id>`

### Intake/PDF Processing (4 endpoints)
- `GET /intake/tickets/<id>/pdf-attachments`
- `GET /intake/tickets/<id>/extract-assets`
- `POST /intake/tickets/<id>/import-assets`
- `GET /intake/extract-single-pdf/<attachment_id>`

### Utilities (5 endpoints)
- `GET /health`
- `GET /debug/routes`
- `POST /extract-assets-from-text`
- `GET /companies`
- `GET /next-asset-tag`
- `POST /create-assets`

---

## Appendix B: API v2 Endpoints Available for Mobile Use

All API v2 endpoints use `dual_auth_required` decorator and support JWT Bearer authentication.

### Admin (api_v2/admin.py) - Requires SUPER_ADMIN/DEVELOPER
- User CRUD
- Company CRUD
- Queue CRUD
- Ticket Category CRUD

### Tickets (api_v2/tickets.py)
- `GET /api/v2/tickets`
- `POST /api/v2/tickets`
- `PUT /api/v2/tickets/<id>`
- `POST /api/v2/tickets/<id>/assign`
- `POST /api/v2/tickets/<id>/status`

### Assets (api_v2/assets.py)
- `POST /api/v2/assets`
- `PUT /api/v2/assets/<id>`
- `DELETE /api/v2/assets/<id>`
- `POST /api/v2/assets/<id>/image`
- `POST /api/v2/assets/<id>/transfer`

### Accessories (api_v2/accessories.py)
- `POST /api/v2/accessories`
- `PUT /api/v2/accessories/<id>`
- `DELETE /api/v2/accessories/<id>`
- `POST /api/v2/accessories/<id>/return`
- `POST /api/v2/accessories/<id>/checkin`

### Customers (api_v2/customers.py)
- `GET /api/v2/customers`
- `POST /api/v2/customers`
- `GET /api/v2/customers/<id>`
- `PUT /api/v2/customers/<id>`
- `DELETE /api/v2/customers/<id>`
- `GET /api/v2/customers/<id>/tickets`

### Service Records (api_v2/service_records.py)
- Full CRUD operations

### Attachments (api_v2/attachments.py)
- Upload/List/Delete operations

### Reports (api_v2/reports.py)
- Report template listing
- Report generation

### Dashboard (api_v2/dashboard.py)
- Widget listing
- Widget data retrieval

### System Settings (api_v2/system_settings.py)
- Settings management
- Issue type configuration

---

*End of Report*
