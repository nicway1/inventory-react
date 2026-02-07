# Jinja2 Template Inventory for React Migration

**Generated:** 2026-02-07
**Total Templates:** 236
**Analysis Purpose:** React migration planning and component extraction

---

## Executive Summary

This document provides a comprehensive inventory of all 236 Jinja2 templates in the Asset Management System. The templates are organized into functional modules, rated for migration difficulty, and analyzed for reusable component patterns.

### Key Findings
- **Base template:** 1,906 lines with significant JavaScript (global search, notifications, theme switching)
- **Largest template:** `tickets/view.html` at 790KB (~15,000+ lines) - CRITICAL complexity
- **Total API calls identified:** 356+ fetch/AJAX calls across 64 templates
- **Modal dialogs:** 1,986+ modal-related elements across 51 templates
- **Form elements:** 1,827+ form/input elements across 159 templates

### External Dependencies
| Library | Usage Count | Purpose |
|---------|-------------|---------|
| Tailwind CSS (CDN) | All templates | Styling framework |
| Chart.js | 12 templates | Data visualization |
| Select2 | 6 templates | Enhanced dropdowns |
| FullCalendar | 2 templates | Calendar scheduling |
| Font Awesome | All templates | Icons |
| Leaflet | 1 template | Maps |
| jQuery | 1 template | Select2 dependency |
| SortableJS | 1 template | Drag-and-drop |

---

## Template Directory Structure

```
templates/
├── base.html (1,906 lines) - MASTER TEMPLATE
├── Root templates (11 files)
├── admin/ (33 files + 1 subdirectory)
│   ├── companies/ (1 file)
│   └── ticket_categories/ (6 files)
├── assets/ (4 files)
├── auth/ (4 files)
├── blog/ (3 files)
├── chatbot/ (2 files)
├── dashboard/ (1 file)
├── data_loader/ (2 files)
├── debug/ (1 file)
├── development/ (29 files)
├── documents/ (6 files)
├── feedback/ (3 files)
├── import_manager/ (3 files)
├── intake/ (4 files)
├── inventory/ (41 files + 1 subdirectory)
│   └── includes/ (1 file)
├── knowledge/ (6 files + 1 subdirectory)
│   └── admin/ (3 files)
├── parcel_tracking/ (1 file)
├── reports/ (7 files)
├── shipments/ (6 files)
├── sla/ (2 files)
├── tickets/ (18 files + 1 subdirectory)
│   └── partials/ (1 file)
├── users/ (3 files)
└── widgets/ (33 files)
```

---

## Module-by-Module Analysis

### 1. Root Templates (11 files)

| Template | Size | Lines | Features | Difficulty |
|----------|------|-------|----------|------------|
| base.html | 82KB | ~1,906 | Navigation, Search, Notifications, Theme Toggle, Toast System | **COMPLEX** |
| home.html | 76KB | ~1,800 | Dashboard widgets, Stats, Quick actions | Hard |
| home_v2.html | 88KB | ~2,100 | Widget grid, Chart.js, SortableJS, Drag-drop | Hard |
| maps.html | 302KB | ~7,000 | Leaflet maps, Multiple markers, Fullscreen | **COMPLEX** |
| profile.html | 26KB | ~600 | User profile, Stats charts, Activity feed | Medium |
| device_specs.html | 24KB | ~550 | Device specs collector, Form | Medium |
| change_password.html | 3KB | ~80 | Simple password form | Easy |
| edit_profile.html | 4KB | ~100 | Profile edit form | Easy |
| error.html | 1KB | ~27 | Error display | **Quick Win** |
| debug_permissions.html | 4KB | ~100 | Debug table | Easy |
| ticket_import_preview.html | 24KB | ~550 | Data table, Preview | Medium |

**Key JavaScript:**
- Global search with live suggestions
- Notification system with toast popups
- Theme switching (Light/Dark/Liquid Glass/UI 2.0)
- XHR/Fetch interception for port handling

**API Calls (base.html):**
- `/inventory/search/suggestions` - Search autocomplete
- `/tickets/notifications` - Notification fetching
- `/tickets/notifications/{id}/mark-read` - Mark as read
- `/tickets/notifications/mark-all-read` - Mark all read
- `/tickets/notifications/unread-count` - Badge count

---

### 2. Tickets Module (18 files + 1 partial)

**Total Size:** ~1.5MB | **Highest Complexity Module**

| Template | Size | Difficulty | Key Features |
|----------|------|------------|--------------|
| view.html | **791KB** | **COMPLEX** | Full ticket view, Comments, @mentions, Assets, Tracking, Issues, Attachments, History |
| list_sf.html | 186KB | **COMPLEX** | Salesforce-style list, Filters, Charts, Bulk actions |
| create.html | 191KB | **COMPLEX** | Multi-category forms, Select2, Customer search, Queue selection |
| list.html | 147KB | Hard | Ticket list with filtering |
| extract_assets.html | 67KB | Hard | Asset extraction interface |
| manager.html | 34KB | Hard | Queue management |
| remediate_assets.html | 26KB | Medium | Asset remediation |
| bulk_import_preview.html | 23KB | Medium | CSV preview |
| tracking_refresh_report.html | 15KB | Medium | Tracking history |
| retool_import.html | 14KB | Medium | Import interface |
| debug_view.html | 12KB | Medium | Debug display |
| bulk_import_1stbase.html | 11KB | Medium | Import form |
| bulk_import_asset_return.html | 11KB | Medium | Return import |
| queue_view.html | 9KB | Easy | Single queue view |
| composer.html | 9KB | Medium | Email composer |
| bulk_import_result.html | 9KB | Easy | Import results |
| tracking_refresh_history.html | 4KB | Easy | History list |
| queues.html | 4KB | Easy | Queue list |
| **partials/queue_manager.html** | 15KB | Medium | Modal for queue management (iOS-style) |

**JavaScript Features:**
- @mention system with live search
- Real-time comment submission
- PDF preview handling
- 17TRACK integration (SingPost)
- Issue reporting system
- Asset attachment management
- Tab navigation system

**API Calls (view.html - 114+ calls):**
- `/tickets/{id}/comments` - CRUD comments
- `/tickets/{id}/issues` - Issue management
- `/tickets/{id}/assets` - Asset operations
- `/tickets/api/mention-suggestions` - @mention autocomplete
- `/tickets/{id}/tracking/refresh` - Tracking updates
- Many more for status, assignment, documents

---

### 3. Inventory Module (41 files + 1 include)

**Total Size:** ~1MB

| Template | Size | Difficulty | Key Features |
|----------|------|------------|--------------|
| view.html | 147KB | **COMPLEX** | Full inventory view, Charts, Filters |
| view_sf.html | 114KB | **COMPLEX** | Salesforce-style inventory, Charts, Filters |
| view_accessory_sf.html | 71KB | Hard | Accessory detail view |
| view_asset_sf.html | 74KB | Hard | Asset detail view |
| asset_details.html | 67KB | Hard | Asset details with transactions |
| accessories.html | 43KB | Hard | Accessories list |
| import.html | 41KB | Medium | CSV import wizard |
| view_customer_user.html | 36KB | Medium | Customer user detail |
| search_results.html | 36KB | Medium | Search results display |
| audit.html | 31KB | Medium | Audit interface |
| audit_remediation.html | 31KB | Medium | Remediation workflow |
| accessory_details.html | 31KB | Medium | Accessory details |
| edit_asset.html | 29KB | Medium | Asset edit form (30 fields) |
| add_asset.html | 28KB | Medium | Asset creation form |
| view_asset.html | 23KB | Medium | Legacy asset view |
| customer_users.html | 18KB | Medium | Customer users list |
| view_inventory.html | 18KB | Medium | Simple inventory view |
| audit_report_detail.html | 16KB | Medium | Audit report detail |
| tech_assets.html | 15KB | Easy | Tech assets list |
| audit_report.html | 13KB | Easy | Audit report summary |
| import_customers.html | 10KB | Easy | Customer import |
| add_accessory.html | 10KB | Easy | Add accessory form |
| item_details.html | 8KB | Easy | Item details |
| edit_accessory.html | 8KB | Easy | Edit accessory |
| view_tech_assets.html | 8KB | Easy | Tech assets view |
| import_results.html | 7KB | Easy | Import results |
| audit_reports_list.html | 7KB | Easy | Audit list |
| edit_customer_user.html | 6KB | Easy | Edit customer user |
| view_accessories.html | 6KB | Easy | Accessories list |
| add_customer_user.html | 6KB | Easy | Add customer user (Select2) |
| _tech_asset_preview.html | 6KB | Easy | Partial - asset preview |
| asset_history.html | 4KB | Easy | History list |
| checkout_accessory.html | 3KB | Easy | Checkout form |
| edit_item.html | 3KB | Easy | Edit item |
| add_accessory_stock.html | 3KB | Easy | Add stock |
| import_preview.html | 3KB | Easy | Import preview |
| index.html | 4KB | Easy | Index page |
| add_item.html | 3KB | Easy | Add item |
| asset_transactions.html | 2KB | **Quick Win** | Transaction list |
| manage.html | 1KB | **Quick Win** | Simple redirect |
| _accessory_preview.html | 4KB | Easy | Partial - accessory preview |
| **includes/checkout_modal.html** | 3KB | Easy | Modal for checkout |

**Reusable Component Candidates:**
- Asset card/preview component
- Accessory card component
- Customer user card
- Checkout modal
- Import wizard stepper
- Filter sidebar
- Data table with sorting/filtering

---

### 4. Admin Module (33 files)

**Total Size:** ~800KB

| Template | Size | Difficulty | Key Features |
|----------|------|------------|--------------|
| asset_checkout_import.html | 107KB | **COMPLEX** | Multi-step import wizard |
| csv_import.html | 92KB | Hard | CSV import with preview |
| user_overview.html | 73KB | Hard | User analytics dashboard |
| system_config.html | 64KB | Hard | System configuration (32 inputs) |
| edit_user.html | 53KB | Hard | User edit form (30 fields) |
| users.html | 53KB | Hard | User management list |
| create_user.html | 39KB | Medium | User creation form |
| company_grouping.html | 35KB | Medium | Company hierarchy |
| queue_notifications.html | 32KB | Medium | Notification settings |
| theme_settings.html | 25KB | Medium | Theme customization |
| changelog.html | 24KB | Medium | Changelog display |
| manage_groups.html | 22KB | Medium | Group management |
| permission_management.html | 21KB | Medium | Permission matrix |
| billing_generator.html | 21KB | Medium | Billing forms |
| mass_create_users.html | 20KB | Medium | Bulk user creation |
| notification_user_groups.html | 20KB | Medium | Notification groups |
| manage_ticket_statuses.html | 19KB | Medium | Status management |
| permissions.html | 19KB | Medium | Permission grid |
| api_management.html | 18KB | Medium | API key management |
| api_documentation.html | 18KB | Medium | API docs display |
| customer_company_grouping.html | 15KB | Easy | Customer groupings |
| history.html | 15KB | Easy | Audit history |
| api_key_usage.html | 14KB | Easy | Usage stats |
| customer_permissions.html | 13KB | Easy | Customer perms |
| queue_permissions_new.html | 12KB | Easy | Queue permissions |
| create_api_key.html | 10KB | Easy | API key form |
| manage_user.html | 10KB | Easy | User quick edit |
| unified_permissions.html | 9KB | Easy | Unified perms |
| widget_preview.html | 8KB | Easy | Widget preview |
| queue_permissions.html | 7KB | Easy | Queue perms (legacy) |
| test_email.html | 7KB | Easy | Email test form |
| companies.html | 5KB | **Quick Win** | Company list |
| create_company.html | 5KB | **Quick Win** | Company form |

**ticket_categories/ subdirectory (6 files):**
| Template | Size | Difficulty |
|----------|------|------------|
| preview.html | 19KB | Medium |
| manage_all.html | 16KB | Medium |
| list.html | 9KB | Easy |
| edit.html | 8KB | Easy |
| edit_predefined.html | 7KB | Easy |
| create.html | 7KB | Easy |

**companies/ subdirectory (1 file):**
| Template | Size | Difficulty |
|----------|------|------------|
| list.html | 5KB | Easy |

---

### 5. Development Module (29 files)

**Total Size:** ~600KB

| Template | Size | Difficulty | Key Features |
|----------|------|------------|--------------|
| action_items.html | 63KB | Hard | Action items list with modals |
| dashboard.html | 59KB | Hard | Development dashboard |
| bug_view.html | 53KB | Hard | Bug detail view |
| feature_view.html | 35KB | Hard | Feature detail view |
| dev_changelog.html | 29KB | Medium | Developer changelog |
| analytics.html | 28KB | Medium | Analytics charts |
| schedule.html | 26KB | Medium | FullCalendar schedule |
| release_view.html | 21KB | Medium | Release detail |
| bug_form.html | 20KB | Medium | Bug report form |
| work_plan.html | 20KB | Medium | Work plan interface |
| user_profile_detail.html | 18KB | Medium | User profile |
| user_profiles.html | 19KB | Medium | User list |
| feature_form.html | 18KB | Medium | Feature form |
| meetings_list.html | 17KB | Medium | Meetings list |
| user_activity.html | 16KB | Medium | Activity tracking |
| admin_work_plan.html | 16KB | Medium | Admin work plan |
| releases.html | 16KB | Medium | Releases list |
| bugs.html | 14KB | Easy | Bugs list |
| release_form.html | 12KB | Easy | Release form |
| feature_test_cases.html | 12KB | Easy | Test cases |
| execute_test_case.html | 10KB | Easy | Test execution |
| execute_feature_test_case.html | 10KB | Easy | Feature testing |
| features.html | 10KB | Easy | Features list |
| admin_schedule.html | 9KB | Easy | Admin schedule |
| feature_test_case_form.html | 8KB | Easy | Test case form |
| test_case_form.html | 8KB | Easy | Test case form |
| testers.html | 8KB | Easy | Testers list |
| test_cases.html | 7KB | Easy | Test cases list |
| changelog.html | 7KB | Easy | Public changelog |

---

### 6. Widgets Module (33 files)

**Total Size:** ~85KB | **Excellent Quick Win Candidates**

| Template | Size | Difficulty | Reusable Component |
|----------|------|------------|-------------------|
| mass_create_users.html | 16KB | Medium | User creation form |
| launchpad.html | 9KB | Easy | App launcher grid |
| case_manager_sla.html | 7KB | Easy | SLA status card |
| shipments_list.html | 5KB | Easy | Shipment list card |
| system_management.html | 4KB | Easy | System links card |
| quick_actions.html | 3KB | Easy | Action buttons |
| report_issue.html | 3KB | Easy | Issue form |
| view_inventory.html | 3KB | Easy | Inventory link card |
| inventory_audit.html | 3KB | Easy | Audit status card |
| view_tickets.html | 3KB | Easy | Tickets link card |
| device_specs_collector.html | 2KB | **Quick Win** | Device info collector |
| action_items_link.html | 2KB | **Quick Win** | Action items link |
| blog_manager.html | 2KB | **Quick Win** | Blog link card |
| billing_generator.html | 2KB | **Quick Win** | Billing link card |
| import_manager_link.html | 2KB | **Quick Win** | Import link card |
| development_console.html | 2KB | **Quick Win** | Dev console link |
| documents_link.html | 2KB | **Quick Win** | Documents link |
| view_customers.html | 2KB | **Quick Win** | Customers link |
| knowledge_base_link.html | 2KB | **Quick Win** | KB link card |
| reports_link.html | 2KB | **Quick Win** | Reports link |
| shipment_history.html | 2KB | **Quick Win** | Shipment history |
| customer_stats.html | 2KB | **Quick Win** | Customer stats |
| queue_stats.html | 1KB | **Quick Win** | Queue stats |
| import_assets.html | 1KB | **Quick Win** | Import assets link |
| inventory_import_link.html | 1KB | **Quick Win** | Import link |
| import_tickets.html | 1KB | **Quick Win** | Import tickets link |
| weekly_tickets_chart.html | 1KB | **Quick Win** | Chart widget |
| user_overview.html | 1KB | **Quick Win** | User overview |
| recent_activities.html | 1KB | **Quick Win** | Activity feed |
| asset_status_chart.html | 0.5KB | **Quick Win** | Status chart |
| clock.html | 0.4KB | **Quick Win** | Clock display |
| ticket_stats.html | 0.4KB | **Quick Win** | Ticket stats |
| inventory_stats.html | 0.4KB | **Quick Win** | Inventory stats |

**All widgets are excellent React component candidates!**

---

### 7. Reports Module (7 files)

**Total Size:** ~290KB

| Template | Size | Difficulty | Key Features |
|----------|------|------------|--------------|
| dashboard_builder.html | 96KB | **COMPLEX** | Drag-drop dashboard builder |
| case_reports_builder.html | 75KB | Hard | Report builder, Chart.js |
| index.html | 52KB | Hard | Reports listing, Sidebar |
| asset_reports.html | 23KB | Medium | Asset reports, Charts |
| case_reports.html | 20KB | Medium | Case reports |
| dashboards.html | 16KB | Medium | Dashboard list |
| assets_by_model.html | 10KB | Easy | Model breakdown |

---

### 8. Knowledge Module (6 files + 3 admin)

**Total Size:** ~175KB

| Template | Size | Difficulty | Key Features |
|----------|------|------------|--------------|
| admin/edit_article.html | 45KB | Hard | Rich text editor, Markdown |
| article_detail.html | 40KB | Medium | Article view, Related |
| index.html | 20KB | Medium | KB homepage, Search |
| category_view.html | 17KB | Medium | Category listing |
| admin/manage_articles.html | 13KB | Medium | Article management |
| admin/dashboard.html | 11KB | Easy | Admin dashboard |
| system_doc.html | 10KB | Easy | System docs view |
| system_docs_list.html | 10KB | Easy | System docs list |
| search_results.html | 9KB | Easy | Search results |

---

### 9. Documents Module (6 files)

**Total Size:** ~80KB

| Template | Size | Difficulty | Key Features |
|----------|------|------------|--------------|
| commercial_invoice_form.html | 23KB | Medium | Multi-step form (36 inputs) |
| commercial_invoice_preview.html | 22KB | Medium | Invoice preview |
| packing_list_preview.html | 10KB | Easy | Packing list preview |
| saved_invoices.html | 10KB | Easy | Invoice list |
| dashboard.html | 8KB | Easy | Documents dashboard |
| packing_list_form.html | 7KB | Easy | Packing list form |

---

### 10. SLA Module (2 files)

**Total Size:** ~94KB

| Template | Size | Difficulty | Key Features |
|----------|------|------------|--------------|
| dashboard.html | 75KB | Hard | SLA dashboard, Chart.js, Complex charts |
| manage.html | 18KB | Medium | SLA configuration |

---

### 11. Shipments Module (6 files)

**Total Size:** ~38KB

| Template | Size | Difficulty | Key Features |
|----------|------|------------|--------------|
| history.html | 17KB | Medium | Shipment history table |
| history_bulk.html | 9KB | Easy | Bulk history |
| view.html | 5KB | Easy | Shipment detail |
| list.html | 3KB | **Quick Win** | Shipment list |
| create.html | 2KB | **Quick Win** | Create shipment form |
| tracking.html | 2KB | **Quick Win** | Tracking display |

---

### 12. Auth Module (4 files)

**Total Size:** ~29KB

| Template | Size | Difficulty | Key Features |
|----------|------|------------|--------------|
| users.html | 14KB | Easy | User list |
| login.html | 11KB | Medium | Login page, Theme switcher |
| create_user.html | 3KB | **Quick Win** | User creation form |
| register.html | 0.4KB | **Quick Win** | Minimal form |

---

### 13. Other Modules

**Intake (4 files, ~28KB):**
| Template | Size | Difficulty |
|----------|------|------------|
| preview_assets.html | 12KB | Easy |
| view_ticket.html | 9KB | Easy |
| list_tickets.html | 4KB | **Quick Win** |
| create_ticket.html | 3KB | **Quick Win** |

**Blog (3 files, ~58KB):**
| Template | Size | Difficulty |
|----------|------|------------|
| admin_edit.html | 25KB | Medium |
| admin_dashboard.html | 17KB | Medium |
| admin_create.html | 16KB | Medium |

**Feedback (3 files, ~34KB):**
| Template | Size | Difficulty |
|----------|------|------------|
| view_bug.html | 12KB | Easy |
| my_reports.html | 11KB | Easy |
| report_bug.html | 10KB | Easy |

**Import Manager (3 files, ~34KB):**
| Template | Size | Difficulty |
|----------|------|------------|
| session_detail.html | 15KB | Medium |
| dashboard.html | 14KB | Easy |
| select.html | 6KB | Easy |

**Data Loader (2 files, ~10KB):**
| Template | Size | Difficulty |
|----------|------|------------|
| results.html | 7KB | Easy |
| preview.html | 3KB | **Quick Win** |

**Chatbot (2 files, ~40KB):**
| Template | Size | Difficulty |
|----------|------|------------|
| widget.html | 27KB | Medium - Floating widget with chat interface |
| admin_logs.html | 12KB | Easy |

**Parcel Tracking (1 file, 39KB):**
| Template | Difficulty |
|----------|------------|
| index.html | Hard - Complex tracking interface |

**Accessories (1 file, 14KB):**
| Template | Difficulty |
|----------|------------|
| list.html | Easy |

**Assets Labels (4 files, ~46KB):**
| Template | Size | Difficulty |
|----------|------|------------|
| labels_dashboard.html | 18KB | Medium |
| bulk_labels_preview.html | 10KB | Easy |
| bulk_labels.html | 10KB | Easy |
| label_preview.html | 8KB | Easy |

**Users (3 files, ~16KB):**
| Template | Size | Difficulty |
|----------|------|------------|
| profile.html | 7KB | Easy |
| manage.html | 6KB | Easy |
| create.html | 3KB | **Quick Win** |

**Dashboard (1 file, 77KB):**
| Template | Difficulty |
|----------|------------|
| widget_showcase.html | Hard - Widget demo page |

**Debug (1 file, 10KB):**
| Template | Difficulty |
|----------|------------|
| documents.html | Easy |

---

## Common UI Patterns Identified

### 1. Salesforce-Style Cards (sf-card)
```html
<div class="sf-card">
  <div class="sf-card-header">
    <h2 class="sf-card-title">Title</h2>
  </div>
  <div class="sf-card-body">Content</div>
</div>
```
**Found in:** 50+ templates
**React Component:** `<SfCard title="..." />`

### 2. Data Tables with Filtering
- Sortable columns
- Search filter
- Pagination
- Row selection
**Found in:** 40+ templates
**React Component:** `<DataTable columns={} data={} />`

### 3. Modal Dialogs
- Confirmation modals
- Form modals
- Preview modals
- iOS-style queue manager
**Found in:** 51 templates
**React Component:** `<Modal isOpen={} onClose={} />`

### 4. Form Patterns
- Multi-step wizards
- Select2 dropdowns
- File upload with preview
- @mention input
**Found in:** 159 templates
**React Components:** `<FormWizard />`, `<SearchableSelect />`, `<FileUpload />`, `<MentionInput />`

### 5. Status Badges
```html
<span class="sf-badge sf-badge-success">Active</span>
```
**Found in:** All list views
**React Component:** `<StatusBadge status="active" />`

### 6. Navigation/Tabs
- SF-style tabs
- Section tabs
- Sidebar navigation
**React Component:** `<TabNavigation tabs={} />`

### 7. Charts
- Pie charts (status distribution)
- Line charts (trends)
- Bar charts (comparisons)
**React Component:** `<Chart type="pie" data={} />`

### 8. Notification Toast
- Success/error/warning/info
- Auto-dismiss
- Click to navigate
**React Component:** `<Toast message={} type={} />`

---

## Shared Partials/Includes

| Partial | Location | Used By |
|---------|----------|---------|
| chatbot/widget.html | Included in base.html | All authenticated pages |
| inventory/includes/checkout_modal.html | Inventory module | Asset views |
| tickets/partials/queue_manager.html | Tickets module | Ticket creation/view |
| inventory/asset_transactions.html | Inventory module | Asset details |

---

## Quick Wins for Initial Migration

These templates are simple, self-contained, and can build team momentum:

### Tier 1 - Start Here (< 1KB, Minimal JS)
1. `error.html` - 27 lines, pure display
2. `auth/register.html` - 11 lines, simple form
3. `widgets/clock.html` - 9 lines, simple display
4. `widgets/inventory_stats.html` - 8 lines
5. `widgets/ticket_stats.html` - 8 lines
6. `inventory/manage.html` - ~30 lines

### Tier 2 - Easy Forms (< 5KB)
1. `change_password.html` - Simple 3-field form
2. `edit_profile.html` - Basic form
3. `admin/create_company.html` - Simple create form
4. `auth/create_user.html` - User form
5. `users/create.html` - User form
6. `intake/create_ticket.html` - Simple intake form
7. `shipments/create.html` - Shipment form
8. `shipments/list.html` - Simple list
9. `shipments/tracking.html` - Tracking display

### Tier 3 - Widget Components (~20 files)
All files in `widgets/` directory are standalone components with minimal dependencies.

---

## Migration Difficulty Summary

| Rating | Count | Description |
|--------|-------|-------------|
| **Quick Win** | 32 | < 3KB, minimal JS, can be done in hours |
| **Easy** | 89 | < 15KB, some forms/lists, 1-2 days each |
| **Medium** | 72 | 15-50KB, moderate complexity, 3-5 days each |
| **Hard** | 31 | 50-100KB, significant JS, 1-2 weeks each |
| **Complex** | 12 | > 100KB, massive JS, 2-4 weeks each |

---

## Recommended Migration Order

### Phase 1: Foundation (Weeks 1-2)
1. Set up React project with Tailwind
2. Create base layout component (from base.html)
3. Implement shared components: Button, Card, Badge, Modal, Toast
4. Migrate all widgets (32 components)

### Phase 2: Simple Pages (Weeks 3-4)
1. Error pages
2. Auth pages (login, register)
3. Profile pages
4. Simple lists (shipments, accessories)

### Phase 3: Core Lists (Weeks 5-8)
1. Inventory list views
2. Ticket list views
3. User management
4. Admin lists

### Phase 4: Detail Views (Weeks 9-14)
1. Inventory detail views
2. Ticket detail views (most complex - 3-4 weeks)
3. Knowledge base

### Phase 5: Advanced Features (Weeks 15-20)
1. Report builder
2. Dashboard builder
3. Maps integration
4. Bulk import wizards

---

## Technical Debt Notes

1. **Inline Styles:** Many templates use inline `style=""` attributes instead of Tailwind classes
2. **Mixed Patterns:** Some templates use SF-style classes, others use plain Tailwind
3. **Duplicate Code:** Similar table/form patterns repeated across templates
4. **Large Files:** Several files exceed 100KB and should be split
5. **Legacy Backups:** `.bak`, `.original`, `.fullbackup` files should be removed
6. **jQuery Dependency:** Still used for Select2 in some templates

---

## API Endpoints Inventory

The templates make calls to approximately 100+ unique API endpoints. Key categories:

- `/tickets/*` - Ticket CRUD, comments, attachments, tracking
- `/inventory/*` - Asset CRUD, accessories, audits
- `/admin/*` - User management, permissions, configuration
- `/api/*` - External API endpoints
- `/knowledge/*` - Article management
- `/reports/*` - Report generation

A full API inventory should be created as part of migration planning.

---

*Document generated by frontend analysis of /Users/123456/inventory/templates/*
