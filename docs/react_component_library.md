# React Component Library Specification

## Inventory Management System - Flask to React Migration

**Version:** 1.0.0
**Date:** February 2026
**Design System:** Salesforce Lightning Design System (SLDS) Patterns with Tailwind CSS

---

## Table of Contents

1. [Design Philosophy](#design-philosophy)
2. [Directory Structure](#directory-structure)
3. [Design Tokens](#design-tokens)
4. [Component Specifications](#component-specifications)
5. [Salesforce Lightning Patterns](#salesforce-lightning-patterns)
6. [Accessibility Guidelines](#accessibility-guidelines)
7. [Migration Strategy](#migration-strategy)

---

## Design Philosophy

### Core Principles

1. **Atomic Design Methodology** - Components are organized from smallest (atoms) to largest (pages)
2. **Salesforce Lightning Consistency** - Familiar patterns for enterprise users
3. **Tailwind-First Styling** - Utility classes for rapid development
4. **Dark Mode Native** - All components support light, dark, and liquid-glass themes
5. **Mobile Responsive** - Touch-friendly, adaptive layouts
6. **Accessibility First** - WCAG 2.1 AA compliance

### Current Design Language

The existing system uses:
- **Salesforce-inspired components** (sf-button, sf-card, sf-badge, sf-data-table)
- **TrueLog brand colors** (Primary blue #385CF2, Cyan accent #0E9ED5)
- **Three theme modes**: Light, Dark, Liquid Glass
- **Font Awesome icons** with Tailwind utility classes
- **Gradient-based visual hierarchy**

---

## Directory Structure

```
src/
├── components/
│   ├── atoms/
│   │   ├── Button/
│   │   │   ├── Button.tsx
│   │   │   ├── Button.stories.tsx
│   │   │   ├── Button.test.tsx
│   │   │   └── index.ts
│   │   ├── Input/
│   │   ├── Badge/
│   │   ├── Icon/
│   │   ├── Avatar/
│   │   ├── Spinner/
│   │   ├── Tooltip/
│   │   └── index.ts
│   │
│   ├── molecules/
│   │   ├── FormGroup/
│   │   ├── Card/
│   │   ├── Dropdown/
│   │   ├── SearchInput/
│   │   ├── Pagination/
│   │   ├── Breadcrumb/
│   │   ├── ActionMenu/
│   │   ├── TabGroup/
│   │   └── index.ts
│   │
│   ├── organisms/
│   │   ├── DataTable/
│   │   ├── Modal/
│   │   ├── Toast/
│   │   ├── Sidebar/
│   │   ├── Header/
│   │   ├── Form/
│   │   ├── RecordDetail/
│   │   ├── RelatedList/
│   │   └── index.ts
│   │
│   ├── templates/
│   │   ├── PageLayout/
│   │   ├── ListViewLayout/
│   │   ├── RecordLayout/
│   │   ├── SplitViewLayout/
│   │   └── index.ts
│   │
│   └── pages/
│       ├── Dashboard/
│       ├── TicketList/
│       ├── TicketDetail/
│       ├── AssetList/
│       ├── AssetDetail/
│       └── index.ts
│
├── design-tokens/
│   ├── colors.ts
│   ├── typography.ts
│   ├── spacing.ts
│   ├── shadows.ts
│   ├── borders.ts
│   └── index.ts
│
├── hooks/
│   ├── useTheme.ts
│   ├── useToast.ts
│   ├── useModal.ts
│   ├── useTable.ts
│   └── index.ts
│
├── context/
│   ├── ThemeContext.tsx
│   ├── ToastContext.tsx
│   └── index.ts
│
└── utils/
    ├── classNames.ts
    ├── formatters.ts
    └── index.ts
```

---

## Design Tokens

### Color Palette

```typescript
// design-tokens/colors.ts

export const colors = {
  // Brand Colors (from current Tailwind config)
  primary: {
    50: '#eef2ff',
    100: '#e0e7ff',
    200: '#c7d2fe',
    300: '#a5b4fc',
    400: '#818cf8',
    500: '#385CF2',  // Main brand blue
    600: '#2d4ac2',
    700: '#243d9e',
    800: '#1e3380',
    900: '#1a2a66',
    950: '#0f1a40',
  },

  accent: {
    cyan: '#0E9ED5',      // CTA color
    cyanLight: '#3db8e5',
    cyanDark: '#0b7aa6',
  },

  // TrueLog Brand
  truelog: {
    light: '#A5C5E9',
    DEFAULT: '#7BA7DE',
    dark: '#5089D3',
  },

  // Semantic Colors
  success: {
    50: '#ecfdf5',
    100: '#d1fae5',
    500: '#10b981',
    600: '#059669',
    700: '#047857',
  },

  warning: {
    50: '#fffbeb',
    100: '#fef3c7',
    500: '#f59e0b',
    600: '#d97706',
    700: '#b45309',
  },

  danger: {
    50: '#fef2f2',
    100: '#fee2e2',
    500: '#ef4444',
    600: '#dc2626',
    700: '#b91c1c',
  },

  info: {
    50: '#eff6ff',
    100: '#dbeafe',
    500: '#3b82f6',
    600: '#2563eb',
    700: '#1d4ed8',
  },

  // Neutral Colors
  gray: {
    50: '#f9fafb',
    100: '#f3f4f6',
    200: '#e5e7eb',
    300: '#d1d5db',
    400: '#9ca3af',
    500: '#6b7280',
    600: '#4b5563',
    700: '#374151',
    800: '#1f2937',
    900: '#111827',
    950: '#030712',
  },

  // Theme-specific backgrounds
  background: {
    light: '#f4f6f9',           // Salesforce-style light background
    dark: '#1f2937',
    liquidGlass: 'rgba(4, 14, 24, 0.85)',
  },

  // Surface colors (cards, modals)
  surface: {
    light: '#ffffff',
    dark: '#374151',
    liquidGlass: 'rgba(255, 255, 255, 0.15)',
  },
};
```

### Typography Scale

```typescript
// design-tokens/typography.ts

export const typography = {
  fontFamily: {
    sans: ['Salesforce Sans', 'Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
    heading: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
    mono: ['SF Mono', 'Monaco', 'Consolas', 'monospace'],
  },

  fontSize: {
    // Headings (from current config)
    h1: { size: '48px', lineHeight: '1.2', weight: 700 },
    h1Lg: { size: '40px', lineHeight: '1.2', weight: 700 },
    h2: { size: '32px', lineHeight: '1.3', weight: 700 },
    h2Sm: { size: '28px', lineHeight: '1.3', weight: 700 },
    h3: { size: '24px', lineHeight: '1.4', weight: 500 },
    h3Sm: { size: '20px', lineHeight: '1.4', weight: 500 },

    // Body text
    body: { size: '16px', lineHeight: '1.6', weight: 400 },
    bodySm: { size: '14px', lineHeight: '1.6', weight: 400 },
    bodyXs: { size: '12px', lineHeight: '1.5', weight: 400 },

    // UI elements
    button: { size: '14px', lineHeight: '1', weight: 500 },
    buttonSm: { size: '12px', lineHeight: '1', weight: 500 },
    label: { size: '12px', lineHeight: '1.4', weight: 600, letterSpacing: '0.05em' },
    caption: { size: '11px', lineHeight: '1.4', weight: 400 },

    // CTA text
    cta: { size: '16px', lineHeight: '1', weight: 700, letterSpacing: '0.05em' },
    ctaSm: { size: '14px', lineHeight: '1', weight: 700, letterSpacing: '0.05em' },
  },
};
```

### Spacing System

```typescript
// design-tokens/spacing.ts

export const spacing = {
  // Base spacing (4px scale)
  0: '0',
  0.5: '2px',
  1: '4px',
  1.5: '6px',
  2: '8px',
  2.5: '10px',
  3: '12px',
  3.5: '14px',
  4: '16px',
  5: '20px',
  6: '24px',
  7: '28px',
  8: '32px',
  9: '36px',
  10: '40px',
  11: '44px',
  12: '48px',
  14: '56px',
  16: '64px',
  20: '80px',
  24: '96px',

  // Component-specific spacing
  component: {
    cardPadding: '24px',          // 1.5rem - sf-card-body padding
    cardHeaderPadding: '16px 24px', // sf-card-header padding
    buttonPaddingX: '16px',
    buttonPaddingY: '10px',
    inputPaddingX: '12px',
    inputPaddingY: '10px',
    tableCell: '16px',
    modalPadding: '24px',
    toolbarGap: '8px',
  },

  // Layout spacing
  layout: {
    containerPadding: '32px 48px',  // sf-container padding
    sectionGap: '24px',
    cardGap: '24px',
  },
};
```

### Border Radius

```typescript
// design-tokens/borders.ts

export const borders = {
  radius: {
    none: '0',
    sm: '0.125rem',      // 2px
    DEFAULT: '0.25rem',  // 4px - buttons
    md: '0.375rem',      // 6px - cards, inputs
    lg: '0.5rem',        // 8px
    xl: '0.75rem',       // 12px - sf-card
    '2xl': '1rem',       // 16px - liquid glass inputs
    '3xl': '1.5rem',     // 24px - liquid glass container
    '4xl': '2rem',
    '5xl': '2.5rem',
    full: '9999px',      // pills, badges
  },

  width: {
    none: '0',
    DEFAULT: '1px',
    2: '2px',
    4: '4px',
    8: '8px',
  },
};
```

### Shadow Definitions

```typescript
// design-tokens/shadows.ts

export const shadows = {
  // Standard shadows
  sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
  DEFAULT: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
  md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
  lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
  xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
  '2xl': '0 25px 50px -12px rgba(0, 0, 0, 0.25)',

  // Component-specific shadows
  card: '0 1px 3px rgba(0, 0, 0, 0.1)',
  cardHover: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
  modal: '0 25px 45px -12px rgba(0, 0, 0, 0.35), 0 10px 15px -3px rgba(0, 0, 0, 0.2)',
  dropdown: '0 4px 12px rgba(0, 0, 0, 0.08)',
  button: '0 1px 2px rgba(0, 0, 0, 0.05)',
  buttonHover: '0 4px 8px rgba(0, 0, 0, 0.1)',

  // Glow effects (brand colors)
  glow: '0 0 40px -10px rgba(56, 92, 242, 0.4)',
  glowCyan: '0 0 40px -10px rgba(14, 158, 213, 0.4)',
  glowLg: '0 0 60px -15px rgba(56, 92, 242, 0.5)',

  // Button-specific glows
  primaryGlow: '0 4px 8px rgba(59, 130, 246, 0.3)',
  successGlow: '0 4px 8px rgba(34, 197, 94, 0.3)',
  dangerGlow: '0 4px 8px rgba(239, 68, 68, 0.3)',

  // Inner glow
  innerGlow: 'inset 0 0 20px rgba(56, 92, 242, 0.1)',

  // Liquid glass shadows
  liquidGlass: '0 25px 45px -12px rgba(0, 0, 0, 0.35), 0 10px 15px -3px rgba(0, 0, 0, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.1)',
};
```

---

## Component Specifications

### Atoms

#### Button

**Variants:**
- `primary` - Brand blue gradient, white text, glow shadow
- `secondary` - White/transparent background, gray border
- `danger` - Red gradient, destructive actions
- `ghost` - No background, text-only with hover state
- `icon` - Square button with icon only

**Sizes:**
- `sm` - 28px height, 12px padding
- `md` - 32px height (default), 16px padding
- `lg` - 40px height, 20px padding

**States:**
- Default, Hover, Active, Focus, Disabled, Loading

**Props Interface:**
```typescript
interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost' | 'icon';
  size?: 'sm' | 'md' | 'lg';
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  isLoading?: boolean;
  isDisabled?: boolean;
  isFullWidth?: boolean;
  children: React.ReactNode;
  onClick?: () => void;
}
```

**Tailwind Classes (Primary):**
```css
/* Light Mode */
bg-gradient-to-br from-blue-500 to-blue-600
text-white font-medium
px-4 py-2.5 rounded-md
shadow-md hover:shadow-lg
hover:from-blue-600 hover:to-blue-700
focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
transition-all duration-150

/* Dark Mode */
dark:from-blue-600 dark:to-blue-700
dark:hover:from-blue-700 dark:hover:to-blue-800
```

---

#### Input

**Types:**
- `text` - Standard text input
- `email` - Email validation
- `password` - Password with toggle visibility
- `search` - Search with icon and clear button
- `textarea` - Multi-line with auto-resize
- `select` - Dropdown select
- `date` - Date picker
- `number` - Numeric with increment/decrement

**States:**
- Default, Focus, Error, Disabled, Read-only

**Props Interface:**
```typescript
interface InputProps {
  type?: 'text' | 'email' | 'password' | 'search' | 'number' | 'date';
  label?: string;
  placeholder?: string;
  helpText?: string;
  errorText?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  isRequired?: boolean;
  isDisabled?: boolean;
  isReadOnly?: boolean;
  value?: string;
  onChange?: (value: string) => void;
}
```

**Tailwind Classes:**
```css
/* Light Mode */
w-full px-3 py-2.5
bg-white border border-gray-300 rounded-lg
text-gray-900 placeholder-gray-400
focus:ring-2 focus:ring-blue-500 focus:border-blue-500
transition-colors duration-150

/* Dark Mode */
dark:bg-gray-700 dark:border-gray-600
dark:text-white dark:placeholder-gray-400
dark:focus:ring-blue-500 dark:focus:border-blue-500

/* Liquid Glass Mode */
bg-white/20 backdrop-blur-lg
border border-white/30
text-white placeholder-white/60
```

---

#### Badge

**Variants:**
- `default` - Gray background
- `success` - Green (deployed, resolved, closed)
- `warning` - Yellow/amber (pending, in-progress)
- `danger` - Red (high priority, overdue)
- `info` - Blue (new, information)
- `purple` - Purple (assigned, user-related)

**Sizes:**
- `sm` - Small, compact
- `md` - Default
- `lg` - Large, prominent

**Props Interface:**
```typescript
interface BadgeProps {
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info' | 'purple';
  size?: 'sm' | 'md' | 'lg';
  dot?: boolean;      // Show dot indicator
  removable?: boolean;
  onRemove?: () => void;
  children: React.ReactNode;
}
```

**Status Mappings (from current system):**
```typescript
const statusBadgeMap = {
  deployed: 'success',
  deployable: 'info',
  new: 'info',
  'in-progress': 'warning',
  resolved: 'success',
  closed: 'success',
  high: 'danger',
  critical: 'danger',
  medium: 'warning',
  low: 'default',
};
```

---

#### Icon

Wrapper component for Font Awesome icons with consistent sizing.

**Props Interface:**
```typescript
interface IconProps {
  name: string;           // Font Awesome icon name (e.g., 'fa-edit', 'fa-trash')
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  color?: string;
  spin?: boolean;
  pulse?: boolean;
  className?: string;
}
```

---

### Molecules

#### Card

**Structure:**
```
Card
├── CardHeader (optional)
│   ├── CardTitle
│   └── CardActions
├── CardBody
└── CardFooter (optional)
```

**Props Interface:**
```typescript
interface CardProps {
  variant?: 'default' | 'bordered' | 'elevated';
  isCollapsible?: boolean;
  isCollapsed?: boolean;
  onToggle?: () => void;
  children: React.ReactNode;
}

interface CardHeaderProps {
  title?: string;
  subtitle?: string;
  icon?: React.ReactNode;
  actions?: React.ReactNode;
}
```

**Tailwind Classes:**
```css
/* sf-card equivalent */
bg-white rounded-xl border border-gray-200
shadow-sm hover:shadow-md
transition-shadow duration-200

/* Header */
bg-gray-50 border-b border-gray-200
px-6 py-4 rounded-t-xl

/* Body */
p-6
```

---

#### Dropdown

**Types:**
- `menu` - Action menu with options
- `select` - Form select with options
- `multi` - Multi-select with checkboxes

**Props Interface:**
```typescript
interface DropdownProps {
  trigger: React.ReactNode;
  items: DropdownItem[];
  placement?: 'bottom-start' | 'bottom-end' | 'top-start' | 'top-end';
  isOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
}

interface DropdownItem {
  id: string;
  label: string;
  icon?: React.ReactNode;
  shortcut?: string;
  isDanger?: boolean;
  isDisabled?: boolean;
  onClick?: () => void;
}
```

---

#### FormGroup

Combines label, input, help text, and error message.

**Props Interface:**
```typescript
interface FormGroupProps {
  label: string;
  htmlFor: string;
  required?: boolean;
  helpText?: string;
  errorText?: string;
  children: React.ReactNode;  // Input component
}
```

**Layout:**
```
FormGroup
├── Label (with required indicator)
├── Input (child component)
├── HelpText (optional)
└── ErrorText (optional)
```

---

#### SearchInput

Enhanced search input with suggestions dropdown.

**Features:**
- Debounced search
- Keyboard navigation (up/down arrows, enter)
- Recent searches
- Search suggestions grouped by type
- Clear button

**Props Interface:**
```typescript
interface SearchInputProps {
  placeholder?: string;
  value?: string;
  onChange?: (value: string) => void;
  onSearch?: (query: string) => void;
  suggestions?: SearchSuggestion[];
  isLoading?: boolean;
  showRecentSearches?: boolean;
}

interface SearchSuggestion {
  id: string;
  type: 'ticket' | 'asset' | 'user' | 'company';
  title: string;
  subtitle?: string;
  icon?: React.ReactNode;
}
```

---

#### Pagination

**Variants:**
- `simple` - Previous/Next only
- `numbered` - Page numbers with ellipsis
- `compact` - Mobile-friendly

**Props Interface:**
```typescript
interface PaginationProps {
  currentPage: number;
  totalPages: number;
  pageSize?: number;
  totalItems?: number;
  onPageChange: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
  showPageSize?: boolean;
  variant?: 'simple' | 'numbered' | 'compact';
}
```

---

### Organisms

#### DataTable

Full-featured data table with Salesforce Lightning styling.

**Features:**
- Sortable columns
- Column resizing
- Row selection (single/multi)
- Inline editing
- Row actions menu
- Fixed header on scroll
- Column visibility toggle
- Bulk actions toolbar
- Empty state
- Loading state

**Props Interface:**
```typescript
interface DataTableProps<T> {
  data: T[];
  columns: TableColumn<T>[];
  isLoading?: boolean;
  emptyStateMessage?: string;

  // Sorting
  sortColumn?: string;
  sortDirection?: 'asc' | 'desc';
  onSort?: (column: string) => void;

  // Selection
  selectable?: boolean;
  selectedRows?: string[];
  onSelectionChange?: (ids: string[]) => void;

  // Pagination
  pagination?: PaginationProps;

  // Row actions
  rowActions?: (row: T) => DropdownItem[];
  onRowClick?: (row: T) => void;

  // Bulk actions
  bulkActions?: BulkAction[];
}

interface TableColumn<T> {
  id: string;
  header: string;
  accessor: keyof T | ((row: T) => React.ReactNode);
  sortable?: boolean;
  width?: string;
  align?: 'left' | 'center' | 'right';
  cell?: (value: any, row: T) => React.ReactNode;
}
```

**Tailwind Classes:**
```css
/* sf-data-table equivalent */
.table {
  @apply w-full border-collapse bg-white;
}

.th {
  @apply bg-gray-50 text-left px-4 py-3
         text-xs font-bold text-gray-600 uppercase tracking-wide
         border-b border-gray-200
         sticky top-0 z-10
         hover:bg-gray-100 cursor-pointer;
}

.td {
  @apply px-4 py-3 text-sm text-gray-900
         border-b border-gray-100;
}

.tr:hover {
  @apply bg-blue-50;
}
```

---

#### Modal

**Sizes:**
- `sm` - 400px max-width
- `md` - 600px max-width (default)
- `lg` - 800px max-width
- `xl` - 1000px max-width
- `full` - Full screen

**Structure:**
```
Modal
├── ModalOverlay (backdrop)
└── ModalContent
    ├── ModalHeader
    │   ├── ModalTitle
    │   └── CloseButton
    ├── ModalBody
    └── ModalFooter (optional)
```

**Props Interface:**
```typescript
interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  closeOnOverlayClick?: boolean;
  closeOnEsc?: boolean;
  showCloseButton?: boolean;
  footer?: React.ReactNode;
  children: React.ReactNode;
}
```

**Animation:**
```css
/* Enter */
@keyframes modalFadeIn {
  from { opacity: 0; transform: scale(0.95) translateY(-20px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

/* Exit */
@keyframes modalFadeOut {
  from { opacity: 1; transform: scale(1) translateY(0); }
  to { opacity: 0; transform: scale(0.95) translateY(-20px); }
}
```

---

#### Toast / Notification System

**Types:**
- `success` - Green, checkmark icon
- `error` - Red, X icon
- `warning` - Amber, exclamation icon
- `info` - Blue, info icon
- `mention` - Purple, @ icon (for @mentions)

**Positions:**
- `top-right` (default)
- `top-left`
- `top-center`
- `bottom-right`
- `bottom-left`
- `bottom-center`

**Props Interface:**
```typescript
interface ToastProps {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info' | 'mention';
  title?: string;
  message: string;
  duration?: number;  // ms, 0 for persistent
  action?: {
    label: string;
    onClick: () => void;
  };
  onClose?: () => void;
}

// Context hook
interface UseToast {
  toast: (props: Omit<ToastProps, 'id'>) => string;
  success: (message: string, title?: string) => string;
  error: (message: string, title?: string) => string;
  warning: (message: string, title?: string) => string;
  info: (message: string, title?: string) => string;
  dismiss: (id: string) => void;
  dismissAll: () => void;
}
```

**Tailwind Classes:**
```css
/* Toast container */
.toast {
  @apply flex items-start gap-3 p-4
         bg-white rounded-lg shadow-lg
         border-l-4 min-w-[320px] max-w-[420px]
         animate-slide-in;
}

.toast-success { @apply border-l-green-500; }
.toast-error { @apply border-l-red-500; }
.toast-warning { @apply border-l-amber-500; }
.toast-info { @apply border-l-blue-500; }
.toast-mention { @apply border-l-purple-500; }
```

---

#### Navigation Components

##### Sidebar

**Structure:**
```
Sidebar
├── SidebarHeader (logo, collapse button)
├── SidebarNav
│   ├── NavSection
│   │   ├── NavItem
│   │   └── NavItem (with submenu)
│   └── NavSection
└── SidebarFooter (user menu, settings)
```

**Props Interface:**
```typescript
interface SidebarProps {
  isCollapsed?: boolean;
  onCollapse?: (collapsed: boolean) => void;
  logo?: React.ReactNode;
  items: NavItem[];
  footer?: React.ReactNode;
}

interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  href?: string;
  onClick?: () => void;
  badge?: string | number;
  children?: NavItem[];
  isActive?: boolean;
}
```

##### Header

**Structure:**
```
Header
├── Logo/Brand
├── GlobalSearch
├── Navigation (desktop)
├── Actions
│   ├── Notifications
│   ├── Settings
│   └── UserMenu
└── MobileMenuButton
```

##### Breadcrumb

**Props Interface:**
```typescript
interface BreadcrumbProps {
  items: BreadcrumbItem[];
  separator?: React.ReactNode;
  maxItems?: number;  // Show ellipsis if exceeded
}

interface BreadcrumbItem {
  label: string;
  href?: string;
  icon?: React.ReactNode;
}
```

---

## Salesforce Lightning Patterns

### Record Detail Layout

Page layout for viewing/editing a single record (ticket, asset, etc.).

**Structure:**
```
RecordDetailLayout
├── RecordHeader
│   ├── RecordIcon
│   ├── RecordTitle
│   ├── RecordSubtitle
│   └── ActionButtons
├── RecordHighlights (key-value pairs, badges)
├── TabGroup
│   ├── Tab: Details
│   ├── Tab: Activity
│   ├── Tab: Related
│   └── Tab: History
├── MainContent
│   ├── FieldSection
│   │   └── FieldRow (label + value)
│   └── FieldSection
└── RelatedLists (sidebar or bottom)
```

**Props Interface:**
```typescript
interface RecordDetailProps<T> {
  record: T;
  fields: FieldSection[];
  actions: ActionButton[];
  tabs?: TabConfig[];
  relatedLists?: RelatedListConfig[];
  isLoading?: boolean;
  isEditing?: boolean;
  onSave?: (data: Partial<T>) => void;
  onCancel?: () => void;
}

interface FieldSection {
  title: string;
  collapsible?: boolean;
  fields: FieldConfig[];
}

interface FieldConfig {
  name: string;
  label: string;
  type: 'text' | 'date' | 'datetime' | 'currency' | 'lookup' | 'picklist' | 'richtext';
  editable?: boolean;
  required?: boolean;
  options?: { value: string; label: string }[];  // For picklist
}
```

---

### List View Layout

Page layout for displaying records in a table/list format.

**Structure:**
```
ListViewLayout
├── PageHeader
│   ├── Title
│   ├── RecordCount
│   └── ActionButtons (New, Import, Export)
├── Toolbar
│   ├── SearchInput
│   ├── FilterDropdowns
│   ├── ViewToggle (table/card)
│   └── BulkActions (when selected)
├── TabBar (predefined filters/views)
├── DataTable / CardGrid
└── Pagination
```

**Props Interface:**
```typescript
interface ListViewProps<T> {
  title: string;
  data: T[];
  columns: TableColumn<T>[];
  filters?: FilterConfig[];
  views?: ViewConfig[];
  actions?: {
    create?: () => void;
    import?: () => void;
    export?: () => void;
  };
  isLoading?: boolean;
  pagination: PaginationProps;
}

interface FilterConfig {
  id: string;
  label: string;
  type: 'select' | 'multi-select' | 'date-range' | 'search';
  options?: { value: string; label: string }[];
}

interface ViewConfig {
  id: string;
  label: string;
  icon?: React.ReactNode;
  filters: Record<string, any>;
  isDefault?: boolean;
}
```

---

### Related Lists

Component for displaying related records within a detail page.

**Structure:**
```
RelatedList
├── RelatedListHeader
│   ├── Title
│   ├── RecordCount
│   └── Actions (New, View All)
├── RelatedListTable (compact)
└── ViewAllLink
```

**Props Interface:**
```typescript
interface RelatedListProps<T> {
  title: string;
  data: T[];
  columns: TableColumn<T>[];
  maxRows?: number;  // Default 5
  actions?: {
    create?: () => void;
    viewAll?: () => void;
  };
  emptyMessage?: string;
}
```

---

### Action Menus

Dropdown menus for record actions.

**Common Actions:**
```typescript
const ticketActions = [
  { id: 'edit', label: 'Edit', icon: 'fa-edit' },
  { id: 'assign', label: 'Assign', icon: 'fa-user-plus' },
  { id: 'change-status', label: 'Change Status', icon: 'fa-exchange-alt' },
  { id: 'add-comment', label: 'Add Comment', icon: 'fa-comment' },
  { divider: true },
  { id: 'email', label: 'Send Email', icon: 'fa-envelope' },
  { id: 'print', label: 'Print', icon: 'fa-print' },
  { divider: true },
  { id: 'delete', label: 'Delete', icon: 'fa-trash', isDanger: true },
];

const assetActions = [
  { id: 'view', label: 'View Details', icon: 'fa-eye' },
  { id: 'edit', label: 'Edit', icon: 'fa-edit' },
  { id: 'checkout', label: 'Check Out', icon: 'fa-sign-out-alt' },
  { id: 'checkin', label: 'Check In', icon: 'fa-sign-in-alt' },
  { id: 'audit', label: 'Audit', icon: 'fa-clipboard-check' },
  { divider: true },
  { id: 'label', label: 'Print Label', icon: 'fa-tag' },
  { id: 'qrcode', label: 'Generate QR Code', icon: 'fa-qrcode' },
];
```

---

## Accessibility Guidelines

### Keyboard Navigation

- All interactive elements must be focusable
- Tab order follows logical flow
- Escape closes modals/dropdowns
- Arrow keys navigate within menus/tables
- Enter/Space activates buttons and links

### ARIA Attributes

```tsx
// Modal
<div role="dialog" aria-modal="true" aria-labelledby="modal-title">
  <h2 id="modal-title">...</h2>
</div>

// Toast
<div role="alert" aria-live="polite">...</div>

// DataTable
<table role="grid" aria-label="Tickets list">
  <thead>
    <tr>
      <th scope="col" aria-sort="ascending">...</th>
    </tr>
  </thead>
</table>

// Loading states
<div aria-busy="true" aria-live="polite">Loading...</div>
```

### Color Contrast

- Text on backgrounds: minimum 4.5:1 ratio
- Large text (18px+): minimum 3:1 ratio
- Interactive elements: minimum 3:1 ratio
- Focus indicators: clearly visible

### Screen Reader Support

- All images have alt text
- Icons have aria-labels
- Form inputs have associated labels
- Error messages linked to inputs with aria-describedby
- Live regions for dynamic content

---

## Migration Strategy

### Phase 1: Foundation (Weeks 1-2)

1. Set up React project with Vite/Next.js
2. Configure Tailwind CSS with design tokens
3. Create theme provider (light/dark/liquid-glass)
4. Build Atoms: Button, Input, Badge, Icon, Spinner

### Phase 2: Core Components (Weeks 3-4)

1. Build Molecules: Card, Dropdown, FormGroup, SearchInput
2. Build Organisms: DataTable, Modal, Toast system
3. Create Storybook documentation

### Phase 3: Layout Components (Weeks 5-6)

1. Build Navigation: Sidebar, Header, Breadcrumb
2. Build Templates: PageLayout, ListViewLayout, RecordLayout
3. Implement responsive behavior

### Phase 4: Page Migration (Weeks 7-10)

1. Dashboard page
2. Ticket list and detail pages
3. Asset list and detail pages
4. Settings and admin pages

### Phase 5: API Integration (Weeks 11-12)

1. Connect to Flask API endpoints
2. Implement data fetching with React Query/SWR
3. Add real-time updates (WebSocket for notifications)

### Phase 6: Testing & Polish (Weeks 13-14)

1. Unit tests for all components
2. Integration tests for pages
3. Accessibility audit
4. Performance optimization
5. Cross-browser testing

---

## Appendix: Component Quick Reference

| Component | Location | Jinja2 Equivalent |
|-----------|----------|-------------------|
| Button | atoms/Button | `.sf-button`, `.primary-button` |
| Input | atoms/Input | `<input>` with Tailwind classes |
| Badge | atoms/Badge | `.sf-badge`, `.sf-badge-*` |
| Card | molecules/Card | `.sf-card`, `.sf-card-header`, `.sf-card-body` |
| DataTable | organisms/DataTable | `.sf-data-table` |
| Modal | organisms/Modal | `#checkoutListModal` pattern |
| Toast | organisms/Toast | `#toast-container` |
| Tabs | molecules/TabGroup | `.sf-tabs`, `.sf-tab` |
| Toolbar | molecules/Toolbar | `.sf-toolbar` |
| PageHeader | molecules/PageHeader | `.sf-page-header` |

---

## Appendix: Theme Configuration

```typescript
// tailwind.config.js extension for React
module.exports = {
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eef2ff',
          500: '#385CF2',
          600: '#2d4ac2',
          // ... full scale
        },
        accent: {
          cyan: '#0E9ED5',
        },
        truelog: {
          DEFAULT: '#7BA7DE',
        },
      },
      animation: {
        'slide-in': 'slideIn 0.3s ease-out',
        'slide-out': 'slideOut 0.2s ease-in',
        'fade-in': 'fadeIn 0.2s ease-out',
        'scale-in': 'scaleIn 0.2s ease-out',
      },
    },
  },
};
```

---

*Document prepared for the Flask-to-React migration of the TrueLog Inventory Management System.*
