# Salesforce Lightning Design System (SLDS) Guidelines

This document outlines the design patterns and standards for the TrueLog React frontend, following the Salesforce Lightning Design System (SLDS) principles to create a professional, enterprise-grade user interface.

---

## Table of Contents

1. [Design Philosophy](#design-philosophy)
2. [Color Palette](#color-palette)
3. [Typography](#typography)
4. [Page Layout](#page-layout)
5. [Page Headers](#page-headers)
6. [Cards](#cards)
7. [Data Tables](#data-tables)
8. [Forms](#forms)
9. [Buttons](#buttons)
10. [Icons](#icons)
11. [Modals](#modals)
12. [Navigation](#navigation)
13. [Spacing](#spacing)
14. [Responsive Design](#responsive-design)
15. [Accessibility](#accessibility)

---

## Design Philosophy

The TrueLog React UI follows these core SLDS principles:

- **Clarity**: Clear visual hierarchy and intuitive layouts
- **Efficiency**: Minimize cognitive load and streamline workflows
- **Consistency**: Uniform patterns across all components
- **Beauty**: Clean, modern aesthetic with attention to detail
- **Enterprise-Ready**: Professional appearance suitable for business environments

---

## Color Palette

### Primary Colors (SLDS Brand)

| Name | Hex | CSS Variable | Usage |
|------|-----|--------------|-------|
| **Brand** | `#0176D3` | `--slds-brand` | Primary actions, links, active states |
| **Brand Dark** | `#014486` | `--slds-brand-dark` | Hover states, emphasis |
| **Brand Light** | `#1B96FF` | `--slds-brand-light` | Backgrounds, highlights |

### Semantic Colors

| Name | Hex | CSS Variable | Usage |
|------|-----|--------------|-------|
| **Success** | `#2E844A` | `--slds-success` | Positive actions, confirmations |
| **Warning** | `#DD7A01` | `--slds-warning` | Caution states, alerts |
| **Error** | `#C23934` | `--slds-error` | Errors, destructive actions |
| **Info** | `#0176D3` | `--slds-info` | Informational messages |

### Background Colors

| Name | Hex | CSS Variable | Usage |
|------|-----|--------------|-------|
| **Page Background** | `#F3F3F3` | `--slds-bg-page` | Main page background |
| **Card Background** | `#FFFFFF` | `--slds-bg-card` | Cards, panels, modals |
| **Section Background** | `#FAFAFA` | `--slds-bg-section` | Alternating sections |
| **Inverse Background** | `#16325C` | `--slds-bg-inverse` | Dark backgrounds, headers |

### Text Colors

| Name | Hex | CSS Variable | Usage |
|------|-----|--------------|-------|
| **Default** | `#181818` | `--slds-text-default` | Primary body text |
| **Weak** | `#706E6B` | `--slds-text-weak` | Secondary text, labels |
| **Inverse** | `#FFFFFF` | `--slds-text-inverse` | Text on dark backgrounds |
| **Link** | `#0176D3` | `--slds-text-link` | Hyperlinks |

### Border Colors

| Name | Hex | CSS Variable | Usage |
|------|-----|--------------|-------|
| **Default** | `#E5E5E5` | `--slds-border` | Standard borders |
| **Strong** | `#C9C9C9` | `--slds-border-strong` | Emphasis borders |
| **Separator** | `#DDDBDA` | `--slds-border-separator` | Divider lines |

---

## Typography

### Font Family

```css
font-family: 'Salesforce Sans', 'Inter', -apple-system, BlinkMacSystemFont,
             'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
```

### Type Scale

| Element | Size | Weight | Line Height | Letter Spacing |
|---------|------|--------|-------------|----------------|
| **Display** | 2rem (32px) | 700 | 1.25 | -0.02em |
| **Heading 1** | 1.5rem (24px) | 700 | 1.25 | -0.01em |
| **Heading 2** | 1.25rem (20px) | 700 | 1.25 | 0 |
| **Heading 3** | 1rem (16px) | 700 | 1.5 | 0 |
| **Body** | 0.875rem (14px) | 400 | 1.5 | 0 |
| **Body Small** | 0.75rem (12px) | 400 | 1.5 | 0 |
| **Caption** | 0.6875rem (11px) | 400 | 1.5 | 0.02em |

### Font Weights

- **Regular**: 400 - Body text, descriptions
- **Medium**: 500 - Emphasis, labels
- **Semibold**: 600 - Subheadings, buttons
- **Bold**: 700 - Headings, important text

---

## Page Layout

### App Structure

```
+----------------------------------------------------------+
|  Global Header (Navigation Bar)                           |
+----------------------------------------------------------+
|  Page Header (Object Icon + Title + Actions)              |
+----------------------------------------------------------+
|  Page Content                                             |
|  +------------------------------------------------------+ |
|  |  Primary Region (Main content, cards, tables)        | |
|  |                                                      | |
|  |  +------------------+  +------------------+          | |
|  |  |  Card            |  |  Card            |          | |
|  |  +------------------+  +------------------+          | |
|  |                                                      | |
|  +------------------------------------------------------+ |
+----------------------------------------------------------+
```

### Container Widths

- **Full Width**: 100% with max-width of 1440px
- **Standard**: 1280px max-width with auto margins
- **Narrow**: 960px max-width for forms and detail pages

### Grid System

Use a 12-column grid with the following breakpoints:

| Breakpoint | Min Width | Columns |
|------------|-----------|---------|
| **xs** | 0 | 1 |
| **sm** | 480px | 4 |
| **md** | 768px | 8 |
| **lg** | 1024px | 12 |
| **xl** | 1280px | 12 |

---

## Page Headers

Every page should have a consistent header structure:

### Record Page Header

```jsx
<header className="slds-page-header">
  {/* Breadcrumb Navigation */}
  <nav className="slds-breadcrumb">
    <ol>
      <li><a href="/home">Home</a></li>
      <li><a href="/assets">Assets</a></li>
      <li>Asset Detail</li>
    </ol>
  </nav>

  {/* Header Content */}
  <div className="slds-page-header__content">
    {/* Object Icon */}
    <div className="slds-media__figure">
      <span className="slds-icon-container slds-icon-standard-asset">
        <Icon name="asset" />
      </span>
    </div>

    {/* Title and Details */}
    <div className="slds-media__body">
      <h1 className="slds-page-header__title">MacBook Pro 16"</h1>
      <p className="slds-page-header__subtitle">Serial: ABC123456</p>
    </div>

    {/* Action Buttons - Right Aligned */}
    <div className="slds-page-header__actions">
      <Button variant="neutral">Edit</Button>
      <Button variant="brand">Save</Button>
    </div>
  </div>

  {/* Highlights Panel (Optional) */}
  <div className="slds-page-header__highlights">
    <div className="slds-highlight-item">
      <span className="slds-highlight-label">Status</span>
      <span className="slds-highlight-value">Active</span>
    </div>
    <div className="slds-highlight-item">
      <span className="slds-highlight-label">Assigned To</span>
      <span className="slds-highlight-value">John Smith</span>
    </div>
  </div>
</header>
```

### Header Specifications

- **Object Icon**: 40x40px with colored background
- **Title**: 24px, font-weight 700
- **Subtitle**: 14px, color `--slds-text-weak`
- **Breadcrumbs**: 12px, separated by chevron icons
- **Action Buttons**: Right-aligned, primary action on far right

---

## Cards

Cards are the primary content containers in the SLDS system.

### Standard Card Structure

```jsx
<article className="slds-card">
  {/* Card Header */}
  <header className="slds-card__header">
    <div className="slds-card__header-content">
      <span className="slds-card__header-icon">
        <Icon name="standard:account" size="small" />
      </span>
      <h2 className="slds-card__header-title">Card Title</h2>
    </div>
    <div className="slds-card__header-actions">
      <Button variant="icon" title="Collapse">
        <Icon name="chevrondown" />
      </Button>
    </div>
  </header>

  {/* Card Body */}
  <div className="slds-card__body">
    {/* Content goes here */}
  </div>

  {/* Card Footer (Optional) */}
  <footer className="slds-card__footer">
    <a href="#">View All</a>
  </footer>
</article>
```

### Card Specifications

| Property | Value |
|----------|-------|
| **Background** | `#FFFFFF` |
| **Border** | 1px solid `#E5E5E5` |
| **Border Radius** | 4px |
| **Box Shadow** | `0 2px 2px rgba(0,0,0,0.05)` |
| **Header Padding** | 16px |
| **Body Padding** | 0 16px 16px |
| **Minimum Height** | Auto |

### Card Variants

1. **Standard Card**: Default white background with subtle shadow
2. **Raised Card**: Enhanced shadow for emphasis
3. **Flat Card**: No shadow, border only
4. **Interactive Card**: Hover state with cursor pointer

---

## Data Tables

Data tables display structured information in rows and columns.

### Table Structure

```jsx
<table className="slds-table slds-table_bordered slds-table_striped">
  <thead>
    <tr className="slds-table__header-row">
      <th scope="col" className="slds-is-sortable">
        <div className="slds-th__action">
          <span>Name</span>
          <Icon name="arrowdown" size="x-small" />
        </div>
      </th>
      <th scope="col">Status</th>
      <th scope="col">Actions</th>
    </tr>
  </thead>
  <tbody>
    <tr className="slds-table__row">
      <td>MacBook Pro 16"</td>
      <td><Badge variant="success">Active</Badge></td>
      <td>
        <ButtonGroup>
          <Button variant="icon" title="Edit">
            <Icon name="edit" />
          </Button>
          <Button variant="icon" title="Delete">
            <Icon name="delete" />
          </Button>
        </ButtonGroup>
      </td>
    </tr>
  </tbody>
</table>
```

### Table Specifications

| Feature | Implementation |
|---------|----------------|
| **Zebra Striping** | Alternate row backgrounds (`#F3F3F3` / `#FFFFFF`) |
| **Sticky Headers** | `position: sticky; top: 0;` |
| **Column Resizing** | Draggable column dividers |
| **Row Hover** | Background `#F3F3F3` on hover |
| **Inline Actions** | Show on row hover, icon buttons |
| **Sorting** | Click header to sort, show direction icon |
| **Selection** | Checkbox column for multi-select |

### Table Cell Padding

- **Header cells**: 8px 16px
- **Body cells**: 8px 16px
- **Compact variant**: 4px 8px

---

## Forms

Forms follow a stacked layout with labels above inputs.

### Form Structure

```jsx
<form className="slds-form slds-form_stacked">
  {/* Text Input */}
  <div className="slds-form-element">
    <label className="slds-form-element__label" htmlFor="name">
      <abbr className="slds-required" title="required">*</abbr>
      Name
    </label>
    <div className="slds-form-element__control">
      <input
        type="text"
        id="name"
        className="slds-input"
        placeholder="Enter name"
        required
      />
    </div>
    <div className="slds-form-element__help">
      Help text appears here
    </div>
  </div>

  {/* Select Dropdown */}
  <div className="slds-form-element">
    <label className="slds-form-element__label">Status</label>
    <div className="slds-form-element__control">
      <select className="slds-select">
        <option>Active</option>
        <option>Inactive</option>
      </select>
    </div>
  </div>

  {/* Form Actions */}
  <div className="slds-form-element slds-form-actions">
    <Button variant="neutral">Cancel</Button>
    <Button variant="brand">Save</Button>
  </div>
</form>
```

### Form Specifications

| Element | Specification |
|---------|---------------|
| **Label Position** | Above input (stacked layout) |
| **Required Indicator** | Red asterisk (*) before label |
| **Input Height** | 32px (default), 24px (small) |
| **Input Padding** | 8px 12px |
| **Border** | 1px solid `#C9C9C9` |
| **Border Radius** | 4px |
| **Focus State** | 2px border `#0176D3`, box-shadow |
| **Error State** | Red border `#C23934`, error message below |
| **Help Text** | 12px, color `#706E6B` |

### Form Validation

```jsx
{/* Error State */}
<div className="slds-form-element slds-has-error">
  <label className="slds-form-element__label">Email</label>
  <div className="slds-form-element__control">
    <input type="email" className="slds-input" />
  </div>
  <div className="slds-form-element__error">
    Please enter a valid email address
  </div>
</div>
```

### Form Button Placement

- **Single Action Forms**: Submit button right-aligned
- **Edit Forms**: Cancel (left), Save (right)
- **Modal Forms**: Actions in modal footer, right-aligned

---

## Buttons

### Button Variants

| Variant | Usage | Tailwind Classes |
|---------|-------|------------------|
| **Brand** | Primary actions (Save, Submit) | `bg-slds-brand text-white hover:bg-slds-brand-dark` |
| **Neutral** | Secondary actions (Cancel, Back) | `bg-white text-gray-700 border border-gray-300 hover:bg-gray-50` |
| **Outline Brand** | Tertiary actions | `bg-transparent text-slds-brand border border-slds-brand` |
| **Destructive** | Delete, Remove | `bg-slds-error text-white hover:bg-red-700` |
| **Success** | Positive confirmations | `bg-slds-success text-white` |
| **Icon** | Icon-only actions | `p-2 hover:bg-gray-100 rounded` |

### Button Specifications

| Property | Value |
|----------|-------|
| **Height** | 32px (default), 24px (small), 40px (large) |
| **Padding** | 0 16px (default), 0 12px (small) |
| **Font Size** | 14px |
| **Font Weight** | 600 |
| **Border Radius** | 4px |
| **Min Width** | 64px |

### Button Hierarchy

1. **One primary (Brand) button per view**
2. **Primary button on the right**
3. **Destructive actions require confirmation**
4. **Use icon buttons sparingly for inline actions**

---

## Icons

### Icon Sizes

| Size | Dimensions | Usage |
|------|------------|-------|
| **xx-small** | 12px | Inline text icons |
| **x-small** | 16px | Small buttons, badges |
| **small** | 20px | Standard buttons, table actions |
| **medium** | 24px | Card headers, navigation |
| **large** | 32px | Page headers, empty states |
| **x-large** | 40px | Feature icons, illustrations |

### Standard Object Icons

Use consistent icons for object types:

- **Asset**: `fas fa-laptop` or `standard:asset`
- **Ticket**: `fas fa-ticket-alt` or `standard:case`
- **Customer**: `fas fa-user` or `standard:account`
- **User**: `fas fa-user-circle` or `standard:user`
- **Shipment**: `fas fa-shipping-fast` or `standard:shipment`

### Icon Colors

- **Standard Icons**: White icon on colored background
- **Utility Icons**: Gray (`#706E6B`) by default
- **Action Icons**: Match button text color

---

## Modals

### Modal Structure

```jsx
<div className="slds-modal slds-fade-in-open">
  <div className="slds-modal__container">
    {/* Header */}
    <header className="slds-modal__header">
      <h2 className="slds-modal__title">Modal Title</h2>
      <button className="slds-modal__close">
        <Icon name="close" />
      </button>
    </header>

    {/* Content */}
    <div className="slds-modal__content">
      {/* Modal body content */}
    </div>

    {/* Footer */}
    <footer className="slds-modal__footer">
      <Button variant="neutral">Cancel</Button>
      <Button variant="brand">Save</Button>
    </footer>
  </div>
</div>
<div className="slds-backdrop slds-backdrop_open"></div>
```

### Modal Sizes

| Size | Max Width |
|------|-----------|
| **Small** | 400px |
| **Medium** | 640px (default) |
| **Large** | 960px |
| **Full** | 100% - 64px |

### Modal Specifications

- **Backdrop**: Black at 50% opacity
- **Border Radius**: 4px
- **Header**: 16px padding, bottom border
- **Content**: 16px padding, scrollable if needed
- **Footer**: 16px padding, top border, right-aligned buttons

---

## Navigation

### Global Navigation

```jsx
<nav className="slds-global-nav">
  <div className="slds-global-nav__logo">
    <img src="/logo.svg" alt="TrueLog" />
  </div>

  <ul className="slds-global-nav__items">
    <li className="slds-global-nav__item slds-is-active">
      <a href="/dashboard">Dashboard</a>
    </li>
    <li className="slds-global-nav__item">
      <a href="/assets">Assets</a>
    </li>
    <li className="slds-global-nav__item">
      <a href="/tickets">Tickets</a>
    </li>
  </ul>

  <div className="slds-global-nav__actions">
    <Button variant="icon"><Icon name="search" /></Button>
    <Button variant="icon"><Icon name="notification" /></Button>
    <Avatar />
  </div>
</nav>
```

### Breadcrumbs

```jsx
<nav className="slds-breadcrumb" aria-label="Breadcrumb">
  <ol className="slds-breadcrumb__list">
    <li className="slds-breadcrumb__item">
      <a href="/">Home</a>
    </li>
    <li className="slds-breadcrumb__item">
      <a href="/assets">Assets</a>
    </li>
    <li className="slds-breadcrumb__item slds-is-current">
      Asset Details
    </li>
  </ol>
</nav>
```

### Tabs

```jsx
<div className="slds-tabs_default">
  <ul className="slds-tabs_default__nav">
    <li className="slds-tabs_default__item slds-is-active">
      <a href="#tab1">Details</a>
    </li>
    <li className="slds-tabs_default__item">
      <a href="#tab2">History</a>
    </li>
    <li className="slds-tabs_default__item">
      <a href="#tab3">Related</a>
    </li>
  </ul>
  <div className="slds-tabs_default__content">
    {/* Tab content */}
  </div>
</div>
```

---

## Spacing

### Spacing Scale

Use consistent spacing based on a 4px grid:

| Token | Value | CSS Variable |
|-------|-------|--------------|
| **none** | 0 | `--slds-spacing-0` |
| **xxx-small** | 2px | `--slds-spacing-1` |
| **xx-small** | 4px | `--slds-spacing-2` |
| **x-small** | 8px | `--slds-spacing-3` |
| **small** | 12px | `--slds-spacing-4` |
| **medium** | 16px | `--slds-spacing-5` |
| **large** | 24px | `--slds-spacing-6` |
| **x-large** | 32px | `--slds-spacing-7` |
| **xx-large** | 48px | `--slds-spacing-8` |

### Component Spacing

| Component | Internal Padding | External Margin |
|-----------|------------------|-----------------|
| **Card** | 16px | 16px between cards |
| **Form Element** | 0 | 16px between elements |
| **Table Cell** | 8px 16px | 0 |
| **Button** | 0 16px | 8px between buttons |
| **Modal Content** | 16px | N/A |

---

## Responsive Design

### Breakpoint Behavior

| Component | Mobile (< 768px) | Tablet (768-1024px) | Desktop (> 1024px) |
|-----------|------------------|---------------------|-------------------|
| **Navigation** | Hamburger menu | Collapsed sidebar | Full sidebar |
| **Cards** | Full width, stacked | 2-column grid | 3-4 column grid |
| **Tables** | Cards or horizontal scroll | Horizontal scroll | Full table |
| **Forms** | Single column | Two columns | Two columns |
| **Modals** | Full screen | Centered, 90% width | Centered, fixed width |

### Touch Targets

- **Minimum touch target**: 44x44px
- **Button height on mobile**: 44px
- **Table row height on mobile**: 48px

---

## Accessibility

### Color Contrast

- **Normal text**: Minimum 4.5:1 ratio
- **Large text**: Minimum 3:1 ratio
- **Interactive elements**: Minimum 3:1 ratio

### Focus States

All interactive elements must have visible focus states:

```css
:focus-visible {
  outline: 2px solid #0176D3;
  outline-offset: 2px;
}
```

### ARIA Labels

- Use `aria-label` for icon-only buttons
- Use `aria-describedby` for form validation
- Use `aria-expanded` for collapsible sections
- Use `role="alert"` for error messages

### Keyboard Navigation

- Tab order follows visual order
- Escape closes modals and dropdowns
- Enter/Space activates buttons
- Arrow keys navigate within menus

---

## Quick Reference: CSS Utility Classes

### Tailwind Classes for SLDS

```css
/* Primary brand button */
.btn-brand {
  @apply bg-slds-brand text-white font-semibold px-4 py-2 rounded
         hover:bg-slds-brand-dark focus:ring-2 focus:ring-slds-brand
         focus:ring-offset-2 transition-colors;
}

/* Neutral button */
.btn-neutral {
  @apply bg-white text-gray-700 font-semibold px-4 py-2 rounded
         border border-gray-300 hover:bg-gray-50
         focus:ring-2 focus:ring-gray-500 focus:ring-offset-2;
}

/* Card */
.slds-card {
  @apply bg-white rounded border border-gray-200 shadow-sm;
}

/* Form input */
.slds-input {
  @apply w-full px-3 py-2 border border-gray-300 rounded
         focus:border-slds-brand focus:ring-2 focus:ring-slds-brand/20;
}

/* Page header */
.slds-page-header {
  @apply bg-white border-b border-gray-200 px-6 py-4;
}
```

---

## Implementation Checklist

When building a new page or component, verify:

- [ ] Page has proper header with breadcrumbs
- [ ] Cards have consistent padding and shadows
- [ ] Forms use stacked label layout
- [ ] Required fields have red asterisk
- [ ] Primary button is on the right
- [ ] Tables have zebra striping
- [ ] Color contrast meets WCAG AA
- [ ] Focus states are visible
- [ ] Touch targets are at least 44px
- [ ] Loading states are implemented
- [ ] Error states are handled gracefully
- [ ] Responsive breakpoints work correctly

---

*Last Updated: February 2026*
*Based on Salesforce Lightning Design System v2.x*
