## 📊 Detailed Technical Specifications

### Database Architecture

**40+ Database Tables** organized into logical groups:

#### Core System Tables (8 tables)
1. **users**: User accounts with authentication
2. **companies**: Company/organization management
3. **permissions**: Role-based permission definitions
4. **user_company_permissions**: User access to specific companies
5. **user_country_permissions**: User access to specific countries
6. **company_queue_permissions**: Company access to ticket queues
7. **company_customer_permissions**: Company access to customer data
8. **locations**: Physical location management

#### Asset Management Tables (6 tables)
9. **assets**: Main asset inventory table
10. **asset_history**: Complete audit trail for assets
11. **asset_transactions**: Checkout/checkin transactions
12. **accessories**: Accessory inventory
13. **accessory_history**: Accessory change tracking
14. **accessory_transactions**: Accessory movements

#### Ticketing System Tables (10 tables)
15. **tickets**: Main ticket table
16. **ticket_assets**: Many-to-many ticket-asset relationships
17. **ticket_accessories**: Accessories included in tickets
18. **ticket_attachments**: File uploads for tickets
19. **ticket_issues**: Issue tracking within tickets
20. **ticket_category_config**: Custom category configurations
21. **comments**: Ticket comments and discussions
22. **queue_notifications**: Queue-based notifications
23. **notifications**: User notification system
24. **queues**: Ticket queue definitions

#### Customer Management Tables (2 tables)
25. **customer_users**: Customer contact information
26. **intake_tickets**: Asset intake/receiving tickets

#### Logistics Tables (3 tables)
27. **tracking_history**: Shipment tracking events
28. **package_items**: Items in multi-package shipments
29. **shipments**: Shipment records (legacy)

#### Knowledge Base Tables (6 tables)
30. **knowledge_articles**: Article content
31. **knowledge_categories**: Article categories
32. **knowledge_tags**: Tagging system
33. **article_tags**: Many-to-many article-tag relationships
34. **knowledge_feedback**: User ratings and feedback
35. **knowledge_attachments**: Article file attachments

#### API Management Tables (2 tables)
36. **api_keys**: API key definitions
37. **api_usage**: API request logging

#### Collaboration Tables (3 tables)
38. **groups**: User groups for mentions
39. **group_memberships**: User-group relationships
40. **activities**: System activity feed

#### Development Workflow Tables (10 tables)
41. **feature_requests**: Feature request tracking
42. **feature_comments**: Comments on features
43. **feature_test_cases**: Test cases for features
44. **feature_tester_assignments**: Tester assignments
45. **bug_reports**: Bug tracking
46. **bug_comments**: Bug discussion
47. **bug_tester_assignments**: Bug testing assignments
48. **test_cases**: Detailed test cases
49. **testers**: Tester profiles
50. **releases**: Release management
51. **changelog_entries**: Changelog tracking

#### Configuration Tables (2 tables)
52. **system_settings**: System-wide settings
53. **firecrawl_keys**: API keys for external services

### Technology Stack Details

#### Backend Framework
- **Python 3.8+**: Modern Python with type hints
- **Flask 2.x**: Lightweight, flexible web framework
- **SQLAlchemy 1.4+**: Powerful ORM with relationship management
- **Flask-Login**: User session management
- **Flask-WTF**: Form handling and CSRF protection
- **Flask-Mail**: Email sending capabilities
- **Flask-CORS**: Cross-origin resource sharing
- **Flask-Migrate**: Database migration management

#### Database Options
- **SQLite**: Default for development and small deployments
- **MySQL/MariaDB**: Production-ready for larger deployments
- **PostgreSQL**: Supported for enterprise deployments
- **Connection Pooling**: Efficient database connections
- **Migration System**: Alembic-based schema versioning

#### Email Integration
- **Microsoft 365 OAuth2**: Primary email system
  - Client credentials flow
  - Graph API integration
  - Corporate email sending
- **Gmail SMTP**: Fallback email system
  - App password authentication
  - TLS encryption
  - Reliable delivery

#### Frontend Technologies
- **Jinja2 Templates**: Server-side rendering
- **Tailwind CSS 3.x**: Modern utility-first CSS
- **Vanilla JavaScript**: No heavy frameworks, fast loading
- **AJAX**: Dynamic updates without page refresh
- **Chart.js**: Data visualization (planned)
- **DataTables**: Advanced table features (planned)

#### File Processing
- **Pandas**: CSV import/export, data manipulation
- **openpyxl**: Excel file generation
- **PyPDF2**: PDF text extraction
- **Pillow**: Image processing
- **python-magic**: File type detection

#### API & Integration
- **JWT (PyJWT)**: Token-based authentication
- **Requests**: HTTP client for external APIs
- **python-dotenv**: Environment variable management
- **Werkzeug**: WSGI utilities and security

### Performance Characteristics

#### Response Times
- **Page Load**: < 500ms for most pages
- **API Endpoints**: < 200ms average response
- **Search Queries**: < 100ms for indexed searches
- **Report Generation**: < 5 seconds for standard reports
- **Bulk Import**: ~1,000 records per minute

#### Scalability Metrics
- **Concurrent Users**: Tested up to 100 simultaneous users
- **Database Size**: Handles 100,000+ assets efficiently
- **API Rate Limit**: 1,000 requests per minute per key
- **File Upload**: Up to 50MB per file
- **Session Timeout**: 2 hours of inactivity

#### Resource Requirements
- **Minimum Server**: 2 CPU cores, 4GB RAM
- **Recommended Server**: 4 CPU cores, 8GB RAM
- **Database Storage**: ~100MB per 10,000 assets
- **File Storage**: Depends on attachments/uploads
- **Bandwidth**: ~1GB per 1,000 API requests

---

## 💼 Detailed Use Case Scenarios

### Use Case 1: IT Asset Management Company

**Company Profile**:
- 50 employees
- Manages 5,000 client assets
- Operates in Singapore, India, Philippines
- 20 client companies
- 500 asset movements per month

**How TrueLog Helps**:

1. **Asset Intake Process**:
   - Client ships 100 laptops to warehouse
   - Create "Asset Intake" ticket
   - Upload packing list PDF
   - System extracts asset details
   - Bulk import via CSV
   - All assets tagged and tracked
   - **Time Saved**: 8 hours → 30 minutes

2. **Client Deployment**:
   - Client requests 50 laptops for new employees
   - Create "Asset Checkout (claw)" ticket
   - Assign 50 assets from inventory
   - Split into 5 packages (10 laptops each)
   - Add tracking numbers for each package
   - System sends notifications
   - Client tracks all 5 packages
   - **Time Saved**: 4 hours → 45 minutes

3. **Return Processing**:
   - Client returns 30 laptops
   - Create "Asset Return (claw)" ticket
   - Scan returned items
   - Document condition with photos
   - Update asset status automatically
   - Generate return report
   - **Time Saved**: 3 hours → 30 minutes

4. **Monthly Billing**:
   - Generate billing report
   - Filter by client company
   - Export to Excel
   - Send to accounting
   - **Time Saved**: 6 hours → 15 minutes

**Monthly Time Savings**: 84 hours = **$2,100 at $25/hour**

### Use Case 2: Corporate IT Department

**Company Profile**:
- 200 employees
- 250 laptops, 300 accessories
- 3 office locations
- 50 new hires per year
- 100 support tickets per month

**How TrueLog Helps**:

1. **New Employee Onboarding**:
   - HR notifies IT of new hire
   - IT creates checkout ticket
   - Assign laptop, mouse, keyboard, charger
   - Add shipping to employee's home
   - Track delivery
   - Employee confirms receipt
   - **Time Saved**: 2 hours → 20 minutes per employee

2. **Equipment Repair**:
   - Employee reports broken laptop
   - Create "Asset Repair" ticket
   - Document issue with photos
   - Send to repair center
   - Track repair status
   - Return to employee
   - **Time Saved**: 1 hour → 15 minutes per repair

3. **Asset Audit**:
   - Quarterly asset verification
   - Export all deployed assets
   - Email employees for confirmation
   - Update asset locations
   - Generate audit report
   - **Time Saved**: 16 hours → 2 hours per quarter

4. **Accessory Management**:
   - Track 300 accessories
   - Monitor stock levels
   - Reorder when low
   - Prevent over-ordering
   - **Cost Savings**: $5,000/year in reduced waste

**Annual Time Savings**: 200 hours = **$5,000 at $25/hour**

### Use Case 3: Equipment Rental Company

**Company Profile**:
- 30 employees
- 1,000 rental devices
- 50 active customers
- 200 rentals per month
- Multi-country operations

**How TrueLog Helps**:

1. **Rental Management**:
   - Customer requests 20 iPads
   - Check availability in system
   - Create checkout ticket
   - Assign devices to customer
   - Set expected return date
   - Track rental duration
   - **Time Saved**: 1 hour → 10 minutes per rental

2. **Return Processing**:
   - Customer returns devices
   - Scan each device
   - Check condition
   - Document any damage
   - Update availability
   - Generate return report
   - **Time Saved**: 2 hours → 30 minutes per return

3. **Utilization Tracking**:
   - View asset utilization reports
   - Identify underutilized devices
   - Optimize inventory levels
   - Reduce idle inventory
   - **Cost Savings**: $20,000/year in reduced inventory

4. **Customer Billing**:
   - Generate rental invoices
   - Calculate rental fees
   - Track payment status
   - Send automated reminders
   - **Time Saved**: 10 hours → 1 hour per month

**Annual Time Savings**: 240 hours = **$6,000 at $25/hour**

### Use Case 4: Third-Party Logistics (3PL) Provider

**Company Profile**:
- 100 employees
- 10,000 client assets in warehouse
- 15 client companies
- 1,000 shipments per month
- Multi-carrier operations

**How TrueLog Helps**:

1. **Warehouse Receiving**:
   - Client ships 500 devices
   - Create intake ticket
   - Scan and verify each item
   - Update inventory
   - Notify client of receipt
   - **Time Saved**: 8 hours → 2 hours per shipment

2. **Order Fulfillment**:
   - Client orders 100 devices
   - Pick items from warehouse
   - Create checkout ticket
   - Pack into multiple boxes
   - Add tracking for each box
   - Update inventory
   - **Time Saved**: 4 hours → 1 hour per order

3. **Multi-Carrier Management**:
   - Use DHL for international
   - Use local carriers for domestic
   - Track all shipments in one place
   - Provide clients with tracking
   - **Time Saved**: 20 hours → 2 hours per month

4. **Client Reporting**:
   - Generate inventory reports
   - Show current stock levels
   - Track inbound/outbound
   - Provide monthly summaries
   - **Time Saved**: 16 hours → 2 hours per month

**Annual Time Savings**: 600 hours = **$15,000 at $25/hour**

---

## 🔌 Detailed API Integration Examples

### Example 1: Automated Asset Sync from ERP

**Scenario**: Sync new asset purchases from ERP to TrueLog

**Integration Flow**:
1. ERP creates purchase order
2. Assets received and entered in ERP
3. Webhook triggers to TrueLog API
4. TrueLog creates assets automatically
5. Confirmation sent back to ERP

**API Calls**:
```python
import requests

# Authenticate
auth_response = requests.post(
    'https://inventory.truelog.com.sg/api/mobile/v1/auth/login',
    json={
        'username': 'api_user@company.com',
        'password': 'secure_password'
    }
)
token = auth_response.json()['token']

# Create assets from ERP data
headers = {'Authorization': f'Bearer {token}'}
for asset in erp_assets:
    response = requests.post(
        'https://inventory.truelog.com.sg/api/v1/inventory',
        headers=headers,
        json={
            'serial_number': asset['serial'],
            'model': asset['model'],
            'manufacturer': asset['manufacturer'],
            'cost_price': asset['cost'],
            'purchase_order': asset['po_number'],
            'status': 'in_stock',
            'country': asset['location']
        }
    )
    print(f"Created asset: {response.json()['id']}")
```

### Example 2: Customer Portal Integration

**Scenario**: Allow customers to view their assets via custom portal

**Integration Flow**:
1. Customer logs into your portal
2. Portal calls TrueLog API
3. Retrieve customer's assets
4. Display in portal UI
5. Allow ticket creation from portal

**API Calls**:
```javascript
// Get customer's assets
const response = await fetch(
    'https://inventory.truelog.com.sg/api/v1/inventory?customer_id=123',
    {
        headers: {
            'Authorization': `Bearer ${apiToken}`
        }
    }
);
const assets = await response.json();

// Display assets in portal
assets.data.forEach(asset => {
    displayAsset(asset);
});

// Create support ticket
const ticketResponse = await fetch(
    'https://inventory.truelog.com.sg/api/v1/tickets',
    {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${apiToken}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            subject: 'Device Issue',
            description: 'Laptop not turning on',
            category': 'ASSET_REPAIR',
            asset_id: asset.id,
            priority: 'HIGH'
        })
    }
);
```

### Example 3: Automated Shipping Notifications

**Scenario**: Send SMS/WhatsApp when tracking is added

**Integration Flow**:
1. Admin adds tracking number to ticket
2. TrueLog triggers webhook
3. Your system receives webhook
4. Send SMS/WhatsApp to customer
5. Customer tracks shipment

**Webhook Payload**:
```json
{
    "event": "ticket.tracking_added",
    "ticket_id": 1234,
    "tracking_number": "1Z999AA10123456784",
    "carrier": "UPS",
    "customer": {
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+65 9123 4567"
    },
    "timestamp": "2025-11-12T10:30:00Z"
}
```

### Example 4: Inventory Sync to E-commerce

**Scenario**: Sync available assets to e-commerce platform

**Integration Flow**:
1. Query available assets from TrueLog
2. Update product availability on e-commerce
3. Customer purchases on e-commerce
4. Create checkout ticket in TrueLog
5. Update inventory automatically

**API Calls**:
```python
# Get available assets
response = requests.get(
    'https://inventory.truelog.com.sg/api/v1/inventory',
    headers={'Authorization': f'Bearer {token}'},
    params={'status': 'available', 'limit': 100}
)
available_assets = response.json()['data']

# Update e-commerce inventory
for asset in available_assets:
    update_ecommerce_product(
        sku=asset['model'],
        quantity=1,
        price=asset['cost_price'] * 1.3  # 30% markup
    )

# When customer purchases
def on_ecommerce_purchase(order):
    # Create checkout ticket
    ticket_response = requests.post(
        'https://inventory.truelog.com.sg/api/v1/tickets',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'subject': f'E-commerce Order {order.id}',
            'category': 'ASSET_CHECKOUT_DHL',
            'customer_id': order.customer_id,
            'shipping_address': order.shipping_address
        }
    )
    ticket_id = ticket_response.json()['id']
    
    # Assign asset to ticket
    # ... (additional API calls)
```

---

## 🎨 User Interface Walkthrough

### Dashboard Overview

**Main Dashboard Elements**:
1. **Activity Feed** (Left Column):
   - Recent ticket updates
   - Asset assignments
   - System notifications
   - @mentions
   - Scrollable, real-time updates

2. **Quick Stats** (Top Row):
   - Total Assets: 5,234
   - Available: 1,456
   - Deployed: 3,234
   - In Repair: 234
   - Open Tickets: 45
   - Pending Approvals: 12

3. **Recent Tickets** (Center):
   - Last 10 tickets
   - Status indicators (color-coded)
   - Quick actions (view, edit, close)
   - Filter by status

4. **My Assignments** (Right Column):
   - Tickets assigned to me
   - Assets I manage
   - Pending tasks
   - Due dates highlighted

### Asset Management Interface

**Asset List View**:
- **Grid Layout**: Cards with asset images
- **Table Layout**: Detailed list with sortable columns
- **Filters Sidebar**:
  - Status (multi-select)
  - Company (multi-select)
  - Country (multi-select)
  - Model (dropdown)
  - Date Range (calendar picker)
  - Condition (multi-select)

**Asset Detail View** (Tabs):
1. **Overview Tab**:
   - Asset photo
   - Key specifications
   - Current status
   - Location
   - Assignment info

2. **Specifications Tab**:
   - Hardware details
   - CPU, RAM, Storage
   - Condition details
   - Accessories included

3. **History Tab**:
   - Timeline view
   - All changes logged
   - User who made change
   - Before/after values

4. **Transactions Tab**:
   - Checkout history
   - Return history
   - Transfer history
   - Repair history

5. **Related Tickets Tab**:
   - All tickets for this asset
   - Quick ticket creation
   - Ticket status overview

### Ticket Management Interface

**Ticket List View**:
- **Kanban Board**: Drag-and-drop by status
- **List View**: Sortable table
- **Calendar View**: Tickets by due date (planned)

**Ticket Detail View** (Tabs):
1. **Overview Tab**:
   - Ticket summary
   - Status and priority
   - Assigned user
   - Customer info
   - Quick actions

2. **Customer Information Tab**:
   - Name and contact
   - Company
   - Address
   - Previous tickets

3. **Tech Assets Tab**:
   - Assigned assets list
   - Asset details
   - Add/remove assets
   - Asset status

4. **Case Progress Tab**:
   - Visual progress bar
   - Completed steps (green checkmarks)
   - Pending steps (gray)
   - Timestamps for each step

5. **Tracking Tab**:
   - Shipping tracking
   - Return tracking
   - Replacement tracking
   - Tracking history timeline

6. **Comments Tab**:
   - Threaded discussions
   - @mention users/groups
   - File attachments
   - Email notifications

7. **Attachments Tab**:
   - All uploaded files
   - Preview images
   - Download files
   - Upload new files

### Admin Panel Interface

**User Management**:
- User list with search
- Create new user form
- Edit user details
- Reset password
- Assign permissions
- View user activity

**Company Management**:
- Company list
- Create/edit companies
- Upload logos
- Set parent-child relationships
- Manage permissions

**Permission Management**:
- Role-based permissions
- User-specific permissions
- Company permissions
- Country permissions
- Queue permissions

**API Management**:
- API key list
- Generate new keys
- Set permissions per key
- View usage statistics
- Revoke keys

**System Configuration**:
- Email settings
- Notification settings
- Ticket categories
- Custom fields (planned)
- System settings

---

*Document continues with CRM/VRM recommendations and additional technical details...*
