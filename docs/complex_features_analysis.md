# Complex Features Analysis for React Migration

This document provides a comprehensive analysis of complex interactive features in the inventory management system that require special attention during the React migration.

---

## Table of Contents

1. [Template Overview](#template-overview)
2. [tickets/view.html Analysis](#ticketsviewhtml-analysis)
3. [tickets/list.html Analysis](#ticketslisthtml-analysis)
4. [inventory/view.html Analysis](#inventoryviewhtml-analysis)
5. [home_v2.html Analysis](#home_v2html-analysis)
6. [React Implementation Recommendations](#react-implementation-recommendations)
7. [API Requirements](#api-requirements)
8. [State Management Strategy](#state-management-strategy)
9. [Performance Considerations](#performance-considerations)

---

## Template Overview

| Template | Lines | Complexity | Priority |
|----------|-------|------------|----------|
| `tickets/view.html` | 13,945 | Very High | Critical |
| `tickets/list.html` | 3,799 | High | High |
| `inventory/view.html` | 3,276 | High | High |
| `home_v2.html` | 2,778 | Medium-High | Medium |

---

## tickets/view.html Analysis

**File**: `/Users/123456/inventory/templates/tickets/view.html`
**Lines**: 13,945
**Complexity**: Very High

### Interactive Features Identified

#### 1. @Mentions System
**Location**: Comment system, Issue reporting form, Service record assignment

**Current Implementation**:
```javascript
// Key functions
triggerMentionSearch(query)      // Searches for users to mention
selectMention(username, userId)  // Inserts selected mention
checkMention(textarea)           // Monitors input for @ character
checkIssueMention(textarea)      // Monitors issue description for @
```

**Features**:
- Triggers on `@` character input
- Real-time user search via API
- Dropdown with user avatars and names (email hidden per recent update)
- Insert `@username` into text
- Creates notification for mentioned user
- Works in multiple contexts: comments, issue reports, service records

**React Implementation**:
- Use `@tiptap/react` with `@tiptap/extension-mention` for rich text mentions
- Or use `react-mentions` package for simpler implementation
- Custom hook: `useMentionSearch` for debounced API calls

#### 2. Comment System (Messenger-Style)
**Location**: Comments section

**Current Implementation**:
```javascript
// Messenger-style textarea with auto-resize
textarea.style.height = 'auto';
textarea.style.height = textarea.scrollHeight + 'px';

// Enter key handling
if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    submitComment();
}
```

**Features**:
- Auto-resizing textarea
- Enter to submit, Shift+Enter for new line
- @mention integration
- Real-time comment posting via fetch API
- Comment threading (if applicable)
- Edit/delete capabilities

**React Implementation**:
- Custom `useAutoResize` hook for textarea
- Controlled textarea component with keyboard event handling
- Optimistic UI updates for instant feedback

#### 3. Multi-Modal System
**Location**: Throughout ticket view

**Modals Identified**:
| Modal | Purpose | Complexity |
|-------|---------|------------|
| Add Asset Modal | Link assets to ticket | Medium |
| Add Shipment Modal | Create shipment tracking | Medium |
| Add Package Modal | Multi-package tracking (up to 5) | High |
| Assign Item to Package Modal | Assign assets/accessories to packages | Medium |
| Add Return Tracking Modal | Return shipment tracking | Medium |
| Add Outbound Tracking Modal | Outbound shipment tracking | Medium |
| Service Record Modal | Create/edit service records | High |
| Queue Change Modal | Change ticket queue | Low |
| Issue Report Form | Report issues with @mention | Medium |
| Delete Confirmation Modal | Confirm delete actions | Low |

**React Implementation**:
- Use `@headlessui/react` Dialog component or Radix UI Dialog
- Custom `useModal` hook for state management
- Portal-based rendering for proper z-index handling
- Focus trap implementation

#### 4. Case Progress Bar
**Location**: Case Progress section

**Current Implementation**:
- 5-stage progress bar (Case Created -> Item Packed -> Tracking Created -> Customer Received -> Complete)
- Visual indicators with color-coded states (green for complete, gray for pending)
- Clickable "Mark Packed" button for stage progression
- Issue indicator badge with count
- Days open counter with live calculation

**Features**:
- Dynamic status calculation based on ticket state
- Conditional rendering based on ticket category (ASSET_CHECKOUT_CLAW, ASSET_RETURN_CLAW)
- Real-time status updates

**React Implementation**:
- `ProgressStepper` component with configurable stages
- Custom hook `useTicketProgress` to calculate current stage
- Animation transitions between stages using Framer Motion

#### 5. Multi-Package Tracking System
**Location**: Asset Checkout (claw) tickets

**Current Implementation**:
```javascript
// Up to 5 packages per ticket
packages = ticket.get_all_packages()  // Returns list of packages

// Package operations
showAddPackageModal()
editPackage(packageNumber)
removePackage(packageNumber)
showAddItemModal(packageNumber)
refreshPackageTracking(packageNumber)
```

**Features**:
- Maximum 5 packages per ticket
- Each package has: tracking number, carrier, status
- Package items: Assets or accessories with quantities
- Real-time tracking status refresh
- Professional timeline display for tracking events

**React Implementation**:
- `PackageTracker` component with sub-components
- `usePackages` hook for package CRUD operations
- `useTrackingRefresh` hook for polling/SSE updates

#### 6. Embedded Iframes (Shipping Portal)
**Location**: Shipping Portal section

**Features**:
- Tab-based interface (SingPost/Ezy2Ship, Retool 3PL Orders)
- Lazy loading of iframe content
- Fullscreen toggle
- Refresh functionality
- Popup window option for external login sessions

**React Implementation**:
- Use React portals for fullscreen mode
- Lazy iframe loading with `IntersectionObserver`
- Custom `useIframeLoader` hook

#### 7. PDF Preview
**Location**: Attached documents section

**Current Implementation**:
```javascript
function pdfLoaded() { /* handle successful load */ }
function pdfError() { /* handle load error */ }
```

**React Implementation**:
- Use `react-pdf` package
- Fallback to native browser PDF viewer
- Error boundary for failed loads

#### 8. Service Records CRUD
**Location**: Service Records section

**Features**:
- Create, Read, Update, Delete service records
- @mention for technician assignment
- Date/time tracking
- Notes with rich text potential
- Status updates

**React Implementation**:
- Form component with validation (React Hook Form + Zod)
- Inline editing capability
- Optimistic updates

#### 9. Asset Management Actions
**Location**: Assets table section

**Features**:
- View asset details
- Unlink asset from ticket
- Asset check-in with serial number scanning
- Bulk asset operations

**React Implementation**:
- `AssetTable` component with react-table
- `useBulkSelection` hook
- Scanner integration component

#### 10. Real-Time Status Updates
**Location**: Throughout view

**Endpoints**:
- `fetchShippingTracking()` - Refresh shipping status
- `fetchReturnTracking()` - Refresh return tracking
- Package tracking refresh per package number
- Issue status updates

**React Implementation**:
- React Query for data fetching and caching
- Optional: WebSocket/SSE for real-time updates
- Polling fallback with configurable intervals

---

## tickets/list.html Analysis

**File**: `/Users/123456/inventory/templates/tickets/list.html`
**Lines**: 3,799
**Complexity**: High

### Interactive Features Identified

#### 1. Tab-Based Navigation
**Current Implementation**:
- Multiple category tabs (All, New, In Progress, On Hold, Resolved, etc.)
- Tab state maintained in URL or session
- Badge counts per tab

**React Implementation**:
- React Router with nested routes
- `useSearchParams` for tab state
- Custom `useTabs` hook

#### 2. Queue Management System
**Features**:
- Create new queues
- Edit queue properties
- Delete queues
- Assign tickets to queues

**React Implementation**:
- CRUD forms with React Hook Form
- Confirmation dialogs for delete actions
- Optimistic UI updates

#### 3. Bulk Search Functionality
**Current Implementation**:
```javascript
// Toggle between single and bulk search
toggleBulkSearch()

// Bulk search accepts multiple IDs
bulkSearchTickets(idList)
```

**Features**:
- Single search mode: one query
- Bulk search mode: comma/newline separated IDs
- Parse and validate multiple inputs

**React Implementation**:
- `SearchInput` component with mode toggle
- Custom parser for bulk input
- Debounced search with `useDeferredValue`

#### 4. Table Sorting and Filtering
**Features**:
- Column-based sorting (click to sort)
- Multiple filter dropdowns (status, category, date range, assignee)
- Persistent filter state
- Clear filters action

**React Implementation**:
- Use `@tanstack/react-table` (TanStack Table)
- Custom filter components
- `useFilters` hook with URL sync

#### 5. Export Wizard
**Features**:
- Multi-step export process
- Filter selection
- Column selection
- Preview before export
- CSV/Excel download

**React Implementation**:
- Multi-step form wizard component
- File download via Blob API
- Loading states and progress indication

#### 6. Pagination Controls
**Features**:
- Page number navigation
- Items per page selector
- Total count display
- Previous/Next buttons

**React Implementation**:
- `Pagination` component
- Integrate with TanStack Table pagination
- URL-synced page state

#### 7. Action Menus (Dropdowns)
**Features**:
- Per-row action menus
- Contextual actions based on ticket state
- Quick actions (assign, change status, delete)

**React Implementation**:
- Use `@headlessui/react` Menu component
- Or `@radix-ui/react-dropdown-menu`
- Keyboard navigation support

---

## inventory/view.html Analysis

**File**: `/Users/123456/inventory/templates/inventory/view.html`
**Lines**: 3,276
**Complexity**: High

### Interactive Features Identified

#### 1. View Switching (Assets/Accessories)
**Current Implementation**:
```javascript
function switchToAssetsView() {
    currentView = 'assets';
    // Update UI, filters, table visibility
}

function switchToAccessoriesView() {
    currentView = 'accessories';
    // Update UI, filters, table visibility
}
```

**Features**:
- Toggle between Tech Assets and Accessories views
- Different filter sets per view
- Different table columns per view
- Shared search functionality

**React Implementation**:
- React Router tabs or state-based toggle
- Context for view state
- Conditional rendering of table components

#### 2. Bulk Selection System
**Current Implementation**:
```javascript
let selectedAssetIds = [];
let selectedAccessoryIds = [];

function handleAssetSelection(checkbox) { }
function handleAccessorySelection(checkbox) { }
function updateButtonStates() { }
```

**Features**:
- Select all checkbox (header)
- Individual row checkboxes
- Selection persists across pagination
- Bulk action buttons (Delete, Add to Checkout, Erase)

**React Implementation**:
- `useBulkSelection` custom hook
- Checkbox components with state sync
- Floating action bar for bulk actions

#### 3. Checkout List System
**Current Implementation**:
```javascript
// CheckoutListManager class or object
window.checkoutManager = {
    items: [],
    addItem(item) { },
    removeItem(id, type) { },
    clearItems() { },
    showModal() { },
    renderItems() { }
}

// LocalStorage persistence
localStorage.setItem('checkoutItems', JSON.stringify(items));
```

**Features**:
- Add assets/accessories to checkout list
- Quantity management
- Customer selection
- Persist across page refreshes (localStorage)
- Modal display of items
- Process checkout action

**React Implementation**:
- Use Zustand or Context + useReducer for state
- `useLocalStorage` hook for persistence
- `CheckoutListProvider` context
- `CheckoutModal` component

#### 4. Filter System
**Current Implementation**:
```javascript
// Asset filters
statusFilter, companyFilter, modelFilter, countryFilter,
erasedFilter, dateFromFilter, dateToFilter

// Accessory filters
accessoryCategoryFilter, accessoryStatusFilter,
accessoryCountryFilter, accessoryManufacturerFilter
```

**Features**:
- Multiple dropdown filters
- Date range filter
- Filter combination (AND logic)
- Clear filters action
- Filter state persistence

**React Implementation**:
- `FilterPanel` component
- Custom hooks per filter type
- `useFilters` for combined state
- URL parameter sync

#### 5. Pagination with Server-Side Loading
**Current Implementation**:
```javascript
async function loadTechAssets(filters = {}, resetPage = false) {
    const response = await fetchWithSession(url, { method, body });
    updateTable(data);
    updatePaginationControls(data);
}
```

**Features**:
- Server-side pagination
- 50 items per page
- Previous/Next navigation
- Page info display (1-50 of 1000)

**React Implementation**:
- React Query with pagination
- `usePagination` hook
- Infinite scroll option

#### 6. Erase Status Modal
**Features**:
- Update erase status (COMPLETED, EWASTE)
- Per-asset action
- Confirmation before update

**React Implementation**:
- Controlled modal component
- Form with radio buttons
- API mutation with feedback

#### 7. Delete Confirmation Modal
**Features**:
- Confirm before bulk delete
- Display count of items to delete
- Cancel option

**React Implementation**:
- Reusable `ConfirmDialog` component
- Destructive action styling

#### 8. CSV Export
**Features**:
- Export current view/filtered data
- Download as CSV file

**React Implementation**:
- Export utility function
- Blob download handler
- Progress indication for large exports

---

## home_v2.html Analysis

**File**: `/Users/123456/inventory/templates/home_v2.html`
**Lines**: 2,778
**Complexity**: Medium-High

### Interactive Features Identified

#### 1. Drag-and-Drop Widget Dashboard
**Current Implementation**:
```javascript
// Using SortableJS
new Sortable(widgetContainer, {
    animation: 150,
    handle: '.widget-handle',
    onEnd: function(evt) {
        saveWidgetLayout();
    }
});
```

**Features**:
- Drag widgets to reorder
- Widget handles for drag initiation
- Smooth animation
- Layout persistence

**React Implementation**:
- Use `@dnd-kit/core` and `@dnd-kit/sortable`
- Or `react-beautiful-dnd` (deprecated but stable)
- Custom `useSortableWidgets` hook

#### 2. Widget System
**Widget Types Identified**:
| Widget | Purpose | Complexity |
|--------|---------|------------|
| Stats Widget | Display key metrics | Low |
| Clock Widget | Display time with themes | Low |
| Chart Widget | Data visualization | High |
| Table Widget | Recent items | Medium |
| Quick Actions | Action buttons | Low |

**Features**:
- Add/remove widgets
- Widget settings panel
- Widget info modal
- Resize widgets (if implemented)
- Edit mode toggle

**React Implementation**:
- Widget registry pattern
- Dynamic component loading
- `WidgetProvider` context
- Individual widget components

#### 3. Edit Mode Toggle
**Features**:
- Toggle dashboard edit mode
- Show/hide widget controls
- Enable/disable drag-and-drop
- Save layout on exit edit mode

**React Implementation**:
- Context for edit mode state
- Conditional rendering of controls
- Auto-save on mode exit

#### 4. Widget Settings Panel
**Features**:
- Slide-out settings panel
- Widget-specific settings
- Theme selection (for clock widgets)
- Data source selection (for chart widgets)

**React Implementation**:
- Drawer component (Headless UI or custom)
- Dynamic form based on widget type
- Settings persistence

#### 5. Chart.js Integration
**Current Implementation**:
- Line charts, bar charts, doughnut charts
- Dynamic data loading
- Responsive sizing
- Theme-aware colors

**React Implementation**:
- Use `react-chartjs-2`
- Custom `useChart` hook for data formatting
- Chart wrapper component with loading states

#### 6. Layout Persistence
**Features**:
- Save widget order to backend
- Load saved layout on page load
- Default layout for new users

**API Endpoint**:
- `POST /api/dashboard/layout` - Save layout
- `GET /api/dashboard/layout` - Load layout

**React Implementation**:
- React Query for layout data
- Debounced save on layout change
- Optimistic updates

---

## React Implementation Recommendations

### Recommended Libraries

#### Core Libraries
| Purpose | Library | Reason |
|---------|---------|--------|
| UI Components | `@headlessui/react` or `@radix-ui` | Accessible, unstyled primitives |
| Forms | `react-hook-form` + `zod` | Performance, validation |
| Data Fetching | `@tanstack/react-query` | Caching, mutations, optimistic updates |
| Tables | `@tanstack/react-table` | Headless, flexible, performant |
| Routing | `react-router-dom` v6 | Industry standard |

#### Feature-Specific Libraries
| Feature | Library | Notes |
|---------|---------|-------|
| @Mentions | `@tiptap/react` or `react-mentions` | Rich text or simple mentions |
| Drag & Drop | `@dnd-kit/core` + `@dnd-kit/sortable` | Modern, accessible |
| Charts | `react-chartjs-2` + `chart.js` | Matches current implementation |
| PDF Viewing | `react-pdf` | Native PDF rendering |
| Date Picking | `react-day-picker` | Lightweight, accessible |
| Modals/Dialogs | `@headlessui/react` | Focus trap, accessibility |
| Toast/Notifications | `react-hot-toast` | Simple, customizable |

### Custom Hooks Needed

```typescript
// Data fetching and state
useMentionSearch(query: string)      // Debounced user search
useTicketData(ticketId: string)       // Ticket with related data
usePackages(ticketId: string)         // Package CRUD operations
useComments(ticketId: string)         // Comment CRUD with optimistic updates
useCheckoutList()                     // Checkout list management
useBulkSelection<T>()                 // Generic bulk selection
useFilters<T>()                       // Filter state with URL sync
usePagination()                       // Pagination state
useTrackingRefresh(trackingNumber)   // Polling for tracking updates

// UI utilities
useAutoResize(textareaRef)           // Textarea auto-resize
useModal()                           // Modal open/close state
useDebounce<T>(value, delay)         // Debounced value
useLocalStorage<T>(key)              // Persistent storage
useDashboardLayout()                 // Widget layout management
```

### State Management Strategy

**Recommended: React Query + Context + Local State**

```
Global State (Context):
- User authentication
- Feature flags
- Theme preferences
- Checkout list

Server State (React Query):
- Tickets data
- Assets/Accessories
- Users list for @mentions
- Dashboard layout

Local State (useState/useReducer):
- Modal open/close
- Form state
- UI toggles (edit mode, view type)
- Selection state
```

---

## API Requirements

### Existing Endpoints (to be maintained)

#### Ticket APIs
```
GET    /api/v1/tickets                    # List tickets with filters
GET    /api/v1/tickets/:id                # Get single ticket
POST   /api/v1/tickets                    # Create ticket
PUT    /api/v1/tickets/:id                # Update ticket
DELETE /api/v1/tickets/:id                # Delete ticket

POST   /api/v1/tickets/:id/comments       # Add comment
GET    /api/v1/tickets/:id/comments       # List comments
DELETE /api/v1/tickets/:id/comments/:cid  # Delete comment

POST   /api/v1/tickets/:id/issues         # Report issue
GET    /api/v1/tickets/:id/issues         # List issues

POST   /api/v1/tickets/:id/packages       # Add package
PUT    /api/v1/tickets/:id/packages/:num  # Update package
DELETE /api/v1/tickets/:id/packages/:num  # Remove package
POST   /api/v1/tickets/:id/packages/:num/items  # Add item to package

POST   /api/v1/tickets/:id/tracking/refresh     # Refresh tracking
POST   /api/v1/tickets/:id/mark-packed          # Mark item packed
POST   /api/v1/tickets/:id/begin-processing     # Begin processing
```

#### Inventory APIs
```
GET    /api/v1/assets                     # List assets with filters
GET    /api/v1/assets/:id                 # Get single asset
POST   /api/v1/assets                     # Create asset
PUT    /api/v1/assets/:id                 # Update asset
DELETE /api/v1/assets                     # Bulk delete assets

POST   /api/v1/assets/:id/erase-status    # Update erase status

GET    /api/v1/accessories                # List accessories
POST   /api/v1/accessories                # Create accessory
PUT    /api/v1/accessories/:id            # Update accessory
DELETE /api/v1/accessories                # Bulk delete accessories
```

#### User/Search APIs
```
GET    /api/v1/users/search?q=            # Search users for @mention
GET    /api/v1/customers                  # List customers
GET    /api/v1/queues                     # List queues
```

#### Dashboard APIs
```
GET    /api/v1/dashboard/layout           # Get saved layout
POST   /api/v1/dashboard/layout           # Save layout
GET    /api/v1/dashboard/stats            # Get dashboard stats
GET    /api/v1/dashboard/widgets/:type    # Get widget data
```

### Real-Time Data Requirements

| Feature | Current Method | Recommended |
|---------|---------------|-------------|
| Tracking Updates | Manual refresh | Polling (30s) or WebSocket |
| Comment Notifications | Page refresh | WebSocket/SSE |
| Status Changes | Manual refresh | WebSocket/SSE |
| Checkout List Sync | localStorage | Could use WebSocket for multi-tab |

### Batch Operations

```
POST   /api/v1/assets/bulk-delete         # Delete multiple assets
POST   /api/v1/assets/bulk-erase          # Update erase status for multiple
POST   /api/v1/assets/bulk-checkout       # Checkout multiple to customer
POST   /api/v1/tickets/bulk-update        # Update multiple ticket fields
```

---

## Performance Considerations

### 1. Large Data Sets
- **Problem**: Inventory can have 10,000+ assets
- **Solution**:
  - Implement virtual scrolling for tables (`@tanstack/react-virtual`)
  - Server-side pagination (already implemented)
  - Debounced search/filtering
  - Column virtualization for wide tables

### 2. @Mention Search
- **Problem**: Frequent API calls while typing
- **Solution**:
  - Debounce search (300ms delay)
  - Cache user list in React Query
  - Limit results to 10 users

### 3. Modal Performance
- **Problem**: Multiple modals can bloat DOM
- **Solution**:
  - Lazy load modal content
  - Use portals for proper DOM placement
  - Unmount modals when closed

### 4. Chart Rendering
- **Problem**: Multiple charts on dashboard
- **Solution**:
  - Lazy load charts below fold
  - Use `IntersectionObserver` for visibility
  - Memoize chart data transformations

### 5. Image/PDF Loading
- **Problem**: Large attachments slow page load
- **Solution**:
  - Lazy load images and PDFs
  - Progressive image loading
  - PDF thumbnail generation

### 6. Bundle Size
- **Solution**:
  - Code splitting per route
  - Dynamic imports for heavy libraries (Chart.js, PDF viewer)
  - Tree-shaking unused components

### 7. Form Performance
- **Solution**:
  - Use `react-hook-form` (uncontrolled inputs)
  - Avoid re-renders with proper memoization
  - Isolate form state from parent components

---

## Migration Priority Matrix

| Feature | Complexity | Business Value | Priority |
|---------|------------|----------------|----------|
| Ticket View with Comments | Very High | Critical | 1 |
| @Mentions System | High | High | 2 |
| Asset/Accessory Tables | High | Critical | 3 |
| Checkout System | Medium | High | 4 |
| Package Tracking | High | High | 5 |
| Dashboard Widgets | Medium | Medium | 6 |
| Export Functionality | Low | Medium | 7 |
| Drag-and-Drop Dashboard | Medium | Low | 8 |

---

## Next Steps

1. **Phase 1**: Create base component library (buttons, inputs, modals, tables)
2. **Phase 2**: Implement authentication and routing structure
3. **Phase 3**: Build ticket view page with comments and @mentions
4. **Phase 4**: Build inventory management with bulk operations
5. **Phase 5**: Create dashboard with widgets
6. **Phase 6**: Implement real-time features (WebSocket/SSE)
7. **Phase 7**: Performance optimization and testing

---

*Document generated: 2026-02-07*
*Analysis performed on: inventory management system templates*
