# Workflow Patterns Analysis for React Migration

**Analysis Date:** 2026-02-07
**Prepared by:** ServiceNow Developer / React Migration Team
**Application:** Inventory Management System (Flask/Jinja2)

---

## Executive Summary

This document analyzes the workflow and form patterns in the current Flask/Jinja2 application to guide the React migration. The application follows many ServiceNow-style conventions, including activity streams, status-based workflows, queue management, and progressive disclosure patterns.

---

## 1. Ticket Lifecycle Workflows

### 1.1 State Transitions

The application uses a dual-status system combining standard and custom statuses:

#### Standard Statuses (Enum-based)
```
NEW -> IN_PROGRESS -> ON_HOLD -> RESOLVED -> RESOLVED_DELIVERED
```

| Status | Description | Color Indicator |
|--------|-------------|-----------------|
| NEW | Freshly created ticket | Blue badge |
| IN_PROGRESS | Work has started | Yellow badge |
| ON_HOLD | Waiting for external input | Red/Warning badge |
| RESOLVED | Work completed | Green badge |
| RESOLVED_DELIVERED | Delivery confirmed | Green badge |

#### Custom Statuses (Database-driven)
- Configurable per organization
- Support custom colors (blue, green, yellow, red)
- Display names separate from internal names
- Grouped in `<optgroup>` in dropdowns

#### React Recommendation
```typescript
// Use discriminated unions for type safety
type TicketStatus =
  | { type: 'standard'; value: StandardStatus }
  | { type: 'custom'; value: string; config: CustomStatusConfig };

interface CustomStatusConfig {
  name: string;
  displayName: string;
  color: 'blue' | 'green' | 'yellow' | 'red';
}
```

### 1.2 Category-Specific Workflows

The application has category-aware workflows with distinct processing paths:

#### Asset Checkout Workflow (ASSET_CHECKOUT_CLAW)
```
Case Created -> Item Packed -> Tracking Created -> Customer Received
```

**UI Pattern:** Visual progress stepper with milestone circles and connecting lines.

#### Asset Return Workflow (ASSET_RETURN_CLAW)
```
Case Created -> [Outbound Shipped] -> Return Shipped -> Return Received -> [Replacement Shipped] -> Complete
```

**Additional Fields:**
- Return tracking number
- Return status
- Replacement tracking/status
- Damage description

#### Asset Intake Workflow (ASSET_INTAKE)
```
Case Created -> Assets Assigned -> Check-in Process -> All Checked In -> Resolved
```

**Special Feature:** Serial number scanning with real-time validation.

### 1.3 Progress Indicators

**Pattern Observed:** Multi-step visual progress bar with:
- Circular step indicators (completed: green, current: blue, pending: gray)
- Connecting progress lines
- Timestamp display for completed steps
- Dynamic "Mark as [Next Step]" action buttons

**React Implementation Recommendation:**
```typescript
interface WorkflowStep {
  id: string;
  label: string;
  status: 'completed' | 'current' | 'pending';
  completedAt?: Date;
  action?: () => Promise<void>;
}

// Use a reusable ProgressStepper component
<ProgressStepper
  steps={workflowSteps}
  orientation="horizontal"
  onStepAction={handleStepAction}
/>
```

---

## 2. Form Patterns Analysis

### 2.1 Input Types Used

| Input Type | Usage | Validation |
|------------|-------|------------|
| `text` | Names, IDs, serial numbers | Required, pattern matching |
| `email` | Customer email | Email format validation |
| `tel` | Phone numbers | Phone format (varies by country) |
| `date` | Receiving dates, deadlines | Date range validation |
| `select` | Status, priority, category, queue | Required selection |
| `textarea` | Descriptions, notes, addresses | Optional, max length |
| `file` | Attachments, images | File type, size limits |
| `checkbox` | Legal hold, create ticket option | Boolean flags |
| `datalist` | Models, customers, conditions | Autocomplete with suggestions |

### 2.2 Conditional Field Patterns

**Category-Based Field Display:**
```javascript
// Current pattern: Show/hide field groups based on category
function onCategoryChange() {
    const category = document.getElementById('category').value;

    // Hide all category-specific fields
    document.getElementById('pinRequestFields').classList.add('hidden');
    document.getElementById('repairFields').classList.add('hidden');
    document.getElementById('assetCheckoutFields').classList.add('hidden');

    // Show relevant fields
    if (category === 'PIN_REQUEST') {
        document.getElementById('pinRequestFields').classList.remove('hidden');
    }
    // ...
}
```

**React Recommendation:**
```typescript
// Use react-hook-form with conditional rendering
const categoryFields: Record<CategoryType, FieldConfig[]> = {
  ASSET_CHECKOUT: ['customer_id', 'shipping_address', 'assets'],
  ASSET_RETURN: ['return_tracking', 'damage_description'],
  PIN_REQUEST: ['lock_type', 'serial_number'],
  // ...
};

<form>
  <CategorySelect control={control} />
  {categoryFields[selectedCategory].map(field => (
    <DynamicField key={field} name={field} control={control} />
  ))}
</form>
```

### 2.3 Dynamic Form Sections

**Observed Patterns:**
1. **Collapsible sections** - Edit forms hidden by default, toggled on demand
2. **Modal forms** - Customer creation, location addition
3. **Inline editing** - Quick status updates without page reload
4. **Progressive disclosure** - Show more fields as user progresses

### 2.4 Validation Patterns

**Client-Side Validation:**
- HTML5 `required` attribute
- Pattern matching for serial numbers
- Email format validation
- Custom JavaScript validation on submit

**Server-Side Validation:**
- CSRF token verification
- Business rule validation (duplicate detection)
- Permission checks

**React Recommendation:**
```typescript
// Use Zod for schema validation
const ticketSchema = z.object({
  category: z.enum(['ASSET_CHECKOUT', 'ASSET_RETURN', ...]),
  customer_id: z.number().positive(),
  subject: z.string().min(5).max(200),
  description: z.string().optional(),
  priority: z.enum(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']),
  // Conditional validation
  damage_description: z.string().optional().refine(
    (val, ctx) => {
      if (ctx.parent.category === 'ASSET_RETURN' && !val) {
        return false;
      }
      return true;
    },
    { message: 'Damage description required for returns' }
  ),
});
```

---

## 3. ServiceNow-Style UI Patterns

### 3.1 Activity Streams / Timelines

**Comments Section Pattern:**
- Chronological display (newest first or last)
- @mention support with dropdown autocomplete
- Enter to submit, Shift+Enter for newline
- Real-time mention suggestions via API

**Current Implementation:**
```javascript
// @mention detection
function checkMention(textarea) {
    const mentionMatch = textBeforeCursor.match(/@([a-zA-Z0-9._@-]*)$/);
    if (mentionMatch) {
        triggerMentionSearch(textarea, mentionMatch[1], cursorPos);
    }
}
```

**React Recommendation:**
```typescript
// Use a mention library like react-mentions or tribute
import { MentionsInput, Mention } from 'react-mentions';

<MentionsInput value={comment} onChange={handleChange}>
  <Mention
    trigger="@"
    data={fetchUsers}
    displayTransform={(id, display) => `@${display}`}
    renderSuggestion={(entry) => <UserSuggestion user={entry} />}
  />
</MentionsInput>
```

### 3.2 Work Notes vs Comments

**Current Pattern:**
- Single comment stream with visibility options
- Comments support @mentions for notifications
- Issue reports tracked separately with status (resolved/unresolved)

**Enhancement Recommendation:**
- Separate work notes (internal) from customer-visible comments
- Activity timeline combining all events (status changes, comments, attachments)

### 3.3 Related Records Display

**Pattern:** SF-style cards showing related entities:
- Customer Information card
- Tech Assets table with add/import actions
- Accessories assignment
- Tracking history timeline

**Card Structure:**
```html
<div class="sf-card">
  <div class="sf-card-header">
    <h2 class="sf-card-title">Related Records</h2>
    <div class="sf-action-buttons">...</div>
  </div>
  <div class="sf-card-body">
    <!-- Field rows or data table -->
  </div>
</div>
```

### 3.4 Quick Actions

**Patterns Observed:**
1. **Inline status update** - Select dropdown with immediate save
2. **Assign to** - Change owner with notes
3. **Mark as [Step]** - Workflow progression buttons
4. **Bulk actions** - Multi-select with batch operations

**Quick Action Bar Example:**
```html
<div class="sf-action-buttons">
  <button onclick="toggleUpdateForm()">Edit</button>
  <button onclick="toggleAssignForm()">Assign</button>
  <button onclick="showAddCommentModal()">Add Comment</button>
</div>
```

### 3.5 Bulk Operations

**Ticket Manager Features:**
- Multi-select with checkboxes
- Select all (visible rows)
- Bulk assign to queue
- Bulk assign to user
- Bulk status update
- Filter + bulk operation combination

**React Recommendation:**
```typescript
// Use react-table or TanStack Table for selection
const [selectedRows, setSelectedRows] = useState<Set<number>>(new Set());

const bulkActions = [
  { label: 'Assign Queue', action: bulkAssignQueue },
  { label: 'Assign User', action: bulkAssignUser },
  { label: 'Update Status', action: bulkUpdateStatus },
];

<DataTable
  data={tickets}
  enableRowSelection
  onSelectionChange={setSelectedRows}
  bulkActions={bulkActions}
/>
```

---

## 4. Asset Workflow Patterns

### 4.1 Asset Check-in Process

**Serial Scan Workflow:**
1. Focus on scan input field
2. Scan/enter serial number
3. Validate against ticket's assigned assets
4. Mark as checked in with timestamp
5. Update progress bar
6. Auto-close ticket when all checked in

**UI Components:**
- Scan input with "Check In" button
- "Fix O->0" button for OCR correction
- Assets table with check-in status
- Progress bar showing completion percentage

### 4.2 Asset Assignment

**Add to Ticket Patterns:**
1. Search existing assets by serial number
2. Create new asset inline
3. Import from external source (specs collector)
4. Bulk import from CSV

### 4.3 Tracking Integration

**Features:**
- Auto-detect carrier from tracking number prefix
- Embedded tracking widgets (17TRACK for SingPost)
- Status polling and update
- Multiple tracking numbers per ticket (outbound, return, replacement)

---

## 5. Form Libraries Recommendation

### 5.1 Form Management: React Hook Form

**Justification:**
- Uncontrolled components for performance
- Built-in validation integration
- DevTools for debugging
- TypeScript support
- Smaller bundle size than Formik

```typescript
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

const { control, handleSubmit, watch, formState } = useForm({
  resolver: zodResolver(ticketSchema),
  defaultValues: ticket,
});

// Watch for conditional fields
const category = watch('category');
```

### 5.2 Validation: Zod

**Justification:**
- TypeScript-first design
- Composable schemas
- Runtime validation
- Schema inference for types
- Better error messages than Yup

```typescript
const assetSchema = z.object({
  asset_tag: z.string().regex(/^SG-R\d{3,4}$/, 'Invalid asset tag format'),
  serial_num: z.string().min(5).max(50),
  model: z.string(),
  status: z.enum(['IN_STOCK', 'CHECKED_OUT', 'IN_REPAIR', ...]),
  legal_hold: z.boolean().default(false),
});

type Asset = z.infer<typeof assetSchema>;
```

### 5.3 Multi-Step Forms

**Current Pattern:** Category-based conditional sections

**React Pattern:**
```typescript
// Use a state machine for complex workflows
import { useMachine } from '@xstate/react';
import { createMachine } from 'xstate';

const ticketWizardMachine = createMachine({
  initial: 'selectCategory',
  states: {
    selectCategory: {
      on: { NEXT: [
        { target: 'assetDetails', cond: 'isAssetCategory' },
        { target: 'customerDetails', cond: 'isCheckoutCategory' },
        { target: 'basicDetails' },
      ]},
    },
    customerDetails: { on: { NEXT: 'assetDetails', BACK: 'selectCategory' }},
    assetDetails: { on: { NEXT: 'review', BACK: 'customerDetails' }},
    review: { on: { SUBMIT: 'submitting', BACK: 'assetDetails' }},
    submitting: { /* async submission */ },
  },
});
```

---

## 6. Component Architecture Recommendations

### 6.1 Core Form Components

```
/components/forms/
  FormField.tsx          # Generic field wrapper with label/error
  TextField.tsx          # Text input with datalist support
  SelectField.tsx        # Dropdown with option groups
  TextAreaField.tsx      # Multiline with auto-resize
  DateField.tsx          # Date picker
  FileUpload.tsx         # Drag-drop file upload
  MentionInput.tsx       # @mention textarea
  SearchableSelect.tsx   # Async search dropdown (Select2 replacement)
```

### 6.2 Workflow Components

```
/components/workflow/
  ProgressStepper.tsx    # Visual workflow progress
  StatusBadge.tsx        # Colored status indicators
  PriorityBadge.tsx      # Priority indicators
  TimelineActivity.tsx   # Activity stream item
  ActivityFeed.tsx       # Complete activity timeline
  QuickActions.tsx       # Action button bar
  BulkActionBar.tsx      # Floating bulk action bar
```

### 6.3 ServiceNow-Style Components

```
/components/sf/
  SFCard.tsx             # Card with header/body
  SFFieldRow.tsx         # Label/value display row
  SFDataTable.tsx        # Sortable, filterable table
  SFModal.tsx            # Modal dialog
  SFToast.tsx            # Toast notifications
  SFSidebar.tsx          # Collapsible filter sidebar
  SFSummaryCard.tsx      # Dashboard metric card
```

---

## 7. State Management Recommendations

### 7.1 Server State: TanStack Query

```typescript
// Ticket queries
const { data: ticket } = useQuery({
  queryKey: ['ticket', ticketId],
  queryFn: () => fetchTicket(ticketId),
});

// Mutations with optimistic updates
const updateStatus = useMutation({
  mutationFn: (newStatus) => updateTicketStatus(ticketId, newStatus),
  onMutate: async (newStatus) => {
    await queryClient.cancelQueries(['ticket', ticketId]);
    const previous = queryClient.getQueryData(['ticket', ticketId]);
    queryClient.setQueryData(['ticket', ticketId], old => ({
      ...old,
      status: newStatus,
    }));
    return { previous };
  },
  onError: (err, newStatus, context) => {
    queryClient.setQueryData(['ticket', ticketId], context.previous);
  },
});
```

### 7.2 UI State: Zustand or Context

```typescript
// For complex UI state (filters, selections)
const useTicketFilters = create((set) => ({
  filters: {
    status: [],
    queue: null,
    assignee: null,
    dateRange: { from: null, to: null },
  },
  setFilter: (key, value) => set((state) => ({
    filters: { ...state.filters, [key]: value },
  })),
  clearFilters: () => set({ filters: initialFilters }),
}));
```

---

## 8. Migration Priority Matrix

| Component | Complexity | Business Value | Priority |
|-----------|------------|----------------|----------|
| Ticket View | High | Critical | P0 |
| Ticket List (SF-style) | High | Critical | P0 |
| Ticket Create | Medium | Critical | P0 |
| Bulk Import Preview | Medium | High | P1 |
| Asset Check-in | Medium | High | P1 |
| Progress Steppers | Low | Medium | P1 |
| Queue Management | Low | Medium | P2 |
| Ticket Manager (Bulk) | Medium | Medium | P2 |
| Comments/Mentions | Medium | Medium | P2 |
| Template Composer | Low | Low | P3 |

---

## 9. File Attachments Pattern

### Current Implementation
- Multiple file upload support
- Accepted formats: PDF, JPG, JPEG, PNG
- Server-side storage with download endpoints
- PDF inline preview with iframe

### React Recommendation
```typescript
// Use react-dropzone for file uploads
import { useDropzone } from 'react-dropzone';

const { getRootProps, getInputProps } = useDropzone({
  accept: {
    'application/pdf': ['.pdf'],
    'image/*': ['.jpg', '.jpeg', '.png'],
  },
  maxSize: 10 * 1024 * 1024, // 10MB
  onDrop: handleFileDrop,
});
```

---

## 10. Signature Captures

**Current Status:** Not observed in analyzed templates.

**Future Consideration:** If needed, use:
```typescript
import SignaturePad from 'react-signature-canvas';

<SignaturePad
  ref={signaturePadRef}
  canvasProps={{ className: 'signature-canvas' }}
/>
```

---

## 11. SLA Tracking UI

### Current Patterns
- "Days Open" counter (calculated from created_at)
- Visual indicators for aging tickets
- No explicit SLA definitions observed

### Enhancement Recommendation
```typescript
interface SLAConfig {
  priority: Priority;
  responseTimeHours: number;
  resolutionTimeHours: number;
  warningThreshold: number; // percentage
}

// SLA Timer component
<SLATimer
  createdAt={ticket.createdAt}
  priority={ticket.priority}
  status={ticket.status}
  slaConfig={slaConfigs[ticket.priority]}
/>
```

---

## 12. Dark Mode Support

**Current Implementation:** CSS-based with `body.dark-theme` class toggle.

**React Recommendation:**
```typescript
// Use CSS variables with theme context
const ThemeProvider = ({ children }) => {
  const [theme, setTheme] = useState<'light' | 'dark'>('light');

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};
```

---

## 13. Summary of Key Patterns

1. **Salesforce-Inspired UI**: Cards, field rows, badges, summary cards
2. **Category-Driven Forms**: Show/hide sections based on ticket type
3. **Multi-Status Workflows**: Standard + custom status system
4. **Visual Progress Steppers**: Multi-step workflow visualization
5. **@Mention System**: Real-time user search in comments
6. **Bulk Operations**: Multi-select with batch actions
7. **Inline Editing**: Toggle edit forms without navigation
8. **Real-Time Updates**: Tracking status polling
9. **Role-Based UI**: Admin-only features conditionally rendered
10. **Mobile-Responsive**: Tailwind CSS breakpoints throughout

---

## Appendix A: Template File Inventory

### Tickets Module
- `/templates/tickets/view.html` - Main ticket detail view (772KB - very complex)
- `/templates/tickets/create.html` - Ticket creation form
- `/templates/tickets/list_sf.html` - Salesforce-style list view
- `/templates/tickets/manager.html` - Bulk ticket management
- `/templates/tickets/composer.html` - Template builder
- `/templates/tickets/queues.html` - Queue management
- `/templates/tickets/bulk_import_preview.html` - Bulk import wizard

### Inventory Module
- `/templates/inventory/add_asset.html` - Asset creation form
- `/templates/inventory/edit_asset.html` - Asset edit form
- `/templates/inventory/checkout_accessory.html` - Accessory checkout

### Intake Module
- `/templates/intake/create_ticket.html` - Intake ticket creation
- `/templates/intake/view_ticket.html` - Intake ticket detail

### Shipments Module
- `/templates/shipments/create.html` - Shipment creation
- `/templates/shipments/view.html` - Shipment tracking view

---

## Appendix B: Recommended NPM Packages

| Package | Purpose | Alternative |
|---------|---------|-------------|
| react-hook-form | Form management | Formik |
| zod | Schema validation | Yup |
| @tanstack/react-query | Server state | SWR |
| @tanstack/react-table | Data tables | react-table |
| react-mentions | @mention input | tribute.js |
| react-dropzone | File uploads | - |
| date-fns | Date formatting | dayjs |
| zustand | Client state | Jotai, Redux |
| xstate | Workflow state machines | - |
| cmdk | Command palette | - |

---

*Document Version: 1.0*
*Last Updated: 2026-02-07*
