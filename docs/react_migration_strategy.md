# React Migration Strategy
## Asset Management System - Flask/Jinja2 to React

**Document Version:** 1.0
**Date:** February 7, 2026
**Author:** Lead Developer
**Status:** Draft for Review

---

## Executive Summary

This document outlines a comprehensive strategy for migrating the Asset Management System from Flask/Jinja2 templates to a modern React-based Single Page Application (SPA). The current system comprises **236 HTML templates** totaling approximately **125,000 lines** of HTML/Jinja2 code, with the largest template (`tickets/view.html`) at nearly 14,000 lines.

### Key Findings

| Metric | Value |
|--------|-------|
| Total Templates | 236 |
| Total HTML Lines | ~125,000 |
| Largest Template | tickets/view.html (13,945 lines) |
| JavaScript Files | 5 files (~2,400 lines) |
| API v2 Endpoints | 12+ modules ready for React |
| Styling Framework | Tailwind CSS (already in use) |

### Strategic Recommendation

We recommend a **Strangler Fig Pattern** migration over 12-18 months, prioritizing high-value, frequently-used modules while maintaining the existing Flask application in production. The existing API v2 layer is well-architected and provides a solid foundation for the React frontend.

---

## Table of Contents

1. [Current State Analysis](#1-current-state-analysis)
2. [Technology Stack Recommendations](#2-technology-stack-recommendations)
3. [Architecture Design](#3-architecture-design)
4. [Migration Approach](#4-migration-approach)
5. [Priority Matrix](#5-priority-matrix)
6. [Timeline and Phases](#6-timeline-and-phases)
7. [Risk Assessment](#7-risk-assessment)
8. [Team Structure](#8-team-structure)
9. [Success Metrics](#9-success-metrics)
10. [Appendices](#10-appendices)

---

## 1. Current State Analysis

### 1.1 Template Distribution by Domain

| Domain | Templates | Lines (Est.) | Complexity | Business Value |
|--------|-----------|--------------|------------|----------------|
| **Tickets** | 19 | ~28,000 | Very High | Critical |
| **Inventory** | 42 | ~18,000 | High | Critical |
| **Admin** | 40 | ~15,000 | Medium-High | High |
| **Reports** | 9 | ~7,000 | Medium | High |
| **Development** | 31 | ~8,000 | Medium | Medium |
| **Knowledge** | 9 | ~3,500 | Low-Medium | Medium |
| **Documents** | 8 | ~2,500 | Low | Low-Medium |
| **Shipments** | 8 | ~2,000 | Low | Medium |
| **Auth** | 6 | ~1,500 | Low | Critical |
| **Other** | 64 | ~39,500 | Varies | Varies |

### 1.2 Largest Templates (Migration Complexity Indicators)

```
1. tickets/view.html         13,945 lines  - Ticket detail view (highest priority refactor)
2. tickets/list_sf.html       4,689 lines  - Ticket list (Salesforce-style)
3. tickets/list.html          3,799 lines  - Standard ticket list
4. tickets/create.html        3,623 lines  - Ticket creation form
5. inventory/view.html        3,276 lines  - Inventory detail view
6. inventory/view_sf.html     3,132 lines  - Inventory Salesforce-style view
7. home_v2.html               2,778 lines  - Dashboard/home page
8. reports/dashboard_builder  2,671 lines  - Report builder
9. dashboard/widget_showcase  2,500 lines  - Widget gallery
10. reports/case_reports      2,208 lines  - Case reports builder
```

### 1.3 Existing Assets (Advantages)

#### API v2 Layer - Ready for React
The existing `/api/v2/` endpoints are well-designed for frontend consumption:

- **Standardized Response Format:**
  ```json
  {
    "success": true,
    "data": { ... },
    "meta": { "pagination": {...}, "timestamp": "..." }
  }
  ```

- **Available Endpoints:**
  - `/api/v2/tickets` - Full CRUD + assign, status change
  - `/api/v2/assets` - Full CRUD + image upload
  - `/api/v2/accessories` - Full CRUD + returns
  - `/api/v2/customers` - Customer management
  - `/api/v2/admin` - User, Company, Queue management
  - `/api/v2/reports` - Report templates and generation
  - `/api/v2/dashboard` - Widget data
  - `/api/v2/attachments` - File uploads
  - `/api/v2/service_records` - Service record CRUD
  - `/api/v2/system_settings` - System configuration
  - `/api/v2/user_preferences` - User settings

- **Authentication:** Dual-auth support (Bearer token + API key)
- **Pagination:** Built-in with configurable page size
- **Sorting:** Standardized query parameters
- **Error Handling:** Consistent error codes and messages

#### Tailwind CSS
Already integrated - no styling migration needed. Current usage includes:
- Dark/light theme support
- Responsive design patterns
- Custom `truelog` color palette

#### JavaScript Patterns
Current vanilla JS (~2,400 lines) handles:
- Tab switching
- @mention autocomplete
- Modal management
- Form validation
- AJAX requests (fetch/XHR)

These patterns can inform React component behavior.

### 1.4 Technical Debt Identified

1. **Monolithic Templates:** `tickets/view.html` at 14K lines combines view, edit, comments, attachments, history - should be 15+ React components
2. **Inline JavaScript:** Heavy use of inline `<script>` blocks instead of modules
3. **Global State:** Uses `window` object for state sharing between scripts
4. **Hardcoded URLs:** Some templates contain hardcoded `127.0.0.1:5000` references
5. **Duplicate Code:** Similar patterns repeated across `*_sf.html` (Salesforce-style) and standard views
6. **Mixed Concerns:** Business logic embedded in templates via Jinja2

---

## 2. Technology Stack Recommendations

### 2.1 Core Framework

| Technology | Recommendation | Rationale |
|------------|----------------|-----------|
| **React** | v18.x | Concurrent features, Suspense for data fetching |
| **TypeScript** | v5.x | Type safety, better IDE support, reduced runtime errors |
| **Build Tool** | Vite | Faster HMR than Webpack, native ESM support |

### 2.2 State Management

**Recommendation: Zustand + React Query**

| Option | Pros | Cons | Our Choice |
|--------|------|------|------------|
| Redux Toolkit | Enterprise standard, DevTools | Boilerplate, learning curve | No |
| Zustand | Simple, minimal boilerplate, TypeScript-first | Less ecosystem | **Yes - Client State** |
| React Query (TanStack) | Server state caching, auto-refetch | Learning curve | **Yes - Server State** |
| Context API | Built-in, simple | Performance issues at scale | Sparingly |

**Architecture:**
- **Zustand:** UI state (modals, sidebars, user preferences, theme)
- **React Query:** All API data fetching, caching, synchronization
- **Context:** Dependency injection (auth context, theme context)

### 2.3 Routing

**Recommendation: React Router v6**

- Nested routes for layout preservation
- Data loaders for route-level data fetching
- Type-safe route parameters

```
Route Structure:
/                          -> Dashboard
/tickets                   -> TicketList
/tickets/:id               -> TicketDetail
/tickets/create            -> TicketCreate
/inventory                 -> InventoryList
/inventory/assets/:id      -> AssetDetail
/inventory/accessories/:id -> AccessoryDetail
/admin/*                   -> AdminRoutes (lazy-loaded)
/reports/*                 -> ReportsRoutes (lazy-loaded)
```

### 2.4 UI Component Library

**Recommendation: Headless UI + Custom Components**

- **Headless UI:** Accessible primitives (modals, dropdowns, tabs)
- **Tailwind CSS:** Already in use, retain for styling
- **Custom Component Library:** Build project-specific components

Avoid heavy libraries (Material UI, Ant Design) - Tailwind is already integrated.

### 2.5 Form Handling

**Recommendation: React Hook Form + Zod**

- React Hook Form: Performant form state management
- Zod: Schema validation with TypeScript inference

### 2.6 Additional Libraries

| Purpose | Library | Notes |
|---------|---------|-------|
| Data Tables | TanStack Table | Headless, highly customizable |
| Date Handling | date-fns | Tree-shakeable, immutable |
| Icons | Heroicons | Already used via Font Awesome, migrate gradually |
| HTTP Client | Axios or fetch wrapper | Unified error handling |
| File Upload | react-dropzone | Already handling attachments |
| Rich Text | TipTap or Lexical | For ticket descriptions/comments |
| Charts | Recharts or Visx | For dashboard widgets |

---

## 3. Architecture Design

### 3.1 Component Hierarchy

```
src/
├── app/
│   ├── App.tsx                 # Root component, providers
│   ├── routes.tsx              # Route definitions
│   └── providers/
│       ├── AuthProvider.tsx
│       ├── QueryProvider.tsx
│       └── ThemeProvider.tsx
│
├── features/                   # Feature-based modules
│   ├── tickets/
│   │   ├── components/
│   │   │   ├── TicketList/
│   │   │   │   ├── TicketList.tsx
│   │   │   │   ├── TicketListItem.tsx
│   │   │   │   ├── TicketListFilters.tsx
│   │   │   │   └── index.ts
│   │   │   ├── TicketDetail/
│   │   │   │   ├── TicketDetail.tsx
│   │   │   │   ├── TicketHeader.tsx
│   │   │   │   ├── TicketTimeline.tsx
│   │   │   │   ├── TicketComments.tsx
│   │   │   │   ├── TicketAttachments.tsx
│   │   │   │   ├── TicketAssets.tsx
│   │   │   │   ├── TicketSidebar.tsx
│   │   │   │   └── index.ts
│   │   │   ├── TicketCreate/
│   │   │   └── TicketEdit/
│   │   ├── hooks/
│   │   │   ├── useTickets.ts
│   │   │   ├── useTicket.ts
│   │   │   ├── useTicketMutations.ts
│   │   │   └── useTicketFilters.ts
│   │   ├── api/
│   │   │   └── ticketApi.ts
│   │   ├── types/
│   │   │   └── ticket.types.ts
│   │   └── index.ts
│   │
│   ├── inventory/
│   │   ├── components/
│   │   │   ├── AssetList/
│   │   │   ├── AssetDetail/
│   │   │   ├── AccessoryList/
│   │   │   └── AccessoryDetail/
│   │   ├── hooks/
│   │   ├── api/
│   │   └── types/
│   │
│   ├── admin/
│   ├── reports/
│   ├── dashboard/
│   └── auth/
│
├── shared/
│   ├── components/
│   │   ├── ui/                 # Base UI components
│   │   │   ├── Button/
│   │   │   ├── Input/
│   │   │   ├── Modal/
│   │   │   ├── Table/
│   │   │   ├── Dropdown/
│   │   │   ├── Tabs/
│   │   │   └── Card/
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Header.tsx
│   │   │   ├── MainLayout.tsx
│   │   │   └── PageHeader.tsx
│   │   └── common/
│   │       ├── LoadingSpinner.tsx
│   │       ├── ErrorBoundary.tsx
│   │       ├── Pagination.tsx
│   │       └── EmptyState.tsx
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── usePermissions.ts
│   │   └── useDebounce.ts
│   ├── utils/
│   │   ├── api.ts              # API client configuration
│   │   ├── formatters.ts
│   │   └── validators.ts
│   └── types/
│       ├── api.types.ts
│       └── common.types.ts
│
├── stores/
│   ├── uiStore.ts              # UI state (Zustand)
│   └── userPreferencesStore.ts
│
└── styles/
    └── tailwind.css
```

### 3.2 State Management Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      React Components                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐  ┌──────────────────────────────────┐ │
│  │   Zustand Store  │  │         React Query Cache        │ │
│  │                  │  │                                  │ │
│  │  - UI State      │  │  - Tickets                       │ │
│  │  - Theme         │  │  - Assets                        │ │
│  │  - Sidebar       │  │  - Accessories                   │ │
│  │  - Modals        │  │  - Users                         │ │
│  │  - Preferences   │  │  - Reports                       │ │
│  └────────┬─────────┘  └────────────────┬─────────────────┘ │
│           │                              │                   │
│           │  Hydration from API          │  Fetching/Caching │
│           ▼                              ▼                   │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                     API Layer                           ││
│  │                                                          ││
│  │  - Axios/fetch wrapper                                   ││
│  │  - Request/response interceptors                         ││
│  │  - Error handling                                        ││
│  │  - Token refresh                                         ││
│  └──────────────────────────────────────────────────────────┘│
│                              │                               │
└──────────────────────────────┼───────────────────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Flask API v2       │
                    │   /api/v2/*          │
                    └──────────────────────┘
```

### 3.3 API Integration Pattern

```typescript
// src/shared/utils/api.ts
import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v2',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - attach auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('authToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor - handle errors
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to login
      window.location.href = '/login';
    }
    return Promise.reject(error.response?.data || error);
  }
);

export default api;
```

```typescript
// src/features/tickets/api/ticketApi.ts
import api from '@/shared/utils/api';
import { Ticket, TicketListParams, TicketCreatePayload } from '../types';

export const ticketApi = {
  list: (params: TicketListParams) =>
    api.get<ApiResponse<Ticket[]>>('/tickets', { params }),

  get: (id: number) =>
    api.get<ApiResponse<Ticket>>(`/tickets/${id}`),

  create: (data: TicketCreatePayload) =>
    api.post<ApiResponse<Ticket>>('/tickets', data),

  update: (id: number, data: Partial<Ticket>) =>
    api.put<ApiResponse<Ticket>>(`/tickets/${id}`, data),

  assign: (id: number, userId: number) =>
    api.post(`/tickets/${id}/assign`, { user_id: userId }),

  changeStatus: (id: number, status: string) =>
    api.post(`/tickets/${id}/status`, { status }),
};
```

### 3.4 Authentication Handling

**Hybrid Approach During Migration:**

1. **Flask Session (Current):** Existing Flask-Login session for legacy pages
2. **JWT Tokens (New):** Issue JWT on login for React SPA
3. **API Key (System):** For service-to-service communication

```typescript
// src/features/auth/AuthProvider.tsx
interface AuthContext {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
  checkPermission: (permission: string) => boolean;
}

// Check authentication on app load
useEffect(() => {
  const checkAuth = async () => {
    try {
      // Validate session with Flask backend
      const response = await api.get('/auth/me');
      setUser(response.data);
    } catch {
      // Not authenticated - may redirect to /login
    }
  };
  checkAuth();
}, []);
```

### 3.5 Routing Strategy

**Hybrid Routing During Migration:**

```
Flask App (Existing)     React SPA (New)
──────────────────────   ─────────────────
/login
/logout
/legacy/*
                         /app/*  (React Router)
                         /app/tickets/*
                         /app/inventory/*
                         /app/admin/*
                         /app/reports/*
```

**Flask serves React SPA:**
```python
@app.route('/app/', defaults={'path': ''})
@app.route('/app/<path:path>')
@login_required
def react_app(path):
    return send_from_directory('react-dist', 'index.html')
```

---

## 4. Migration Approach

### 4.1 Strangler Fig Pattern

The Strangler Fig pattern allows incremental replacement of the legacy system while maintaining production stability.

```
Phase 1                    Phase 2                    Phase 3
┌────────────────────┐    ┌────────────────────┐    ┌────────────────────┐
│   Flask/Jinja2     │    │   Flask/Jinja2     │    │      React SPA     │
│   ████████████     │    │   ████████         │    │   ████████████     │
│                    │    │                    │    │                    │
│   React SPA        │    │   React SPA        │    │   Flask API        │
│   ████             │    │   ████████         │    │   (API only)       │
└────────────────────┘    └────────────────────┘    └────────────────────┘
     Months 1-4               Months 5-10             Months 11-18
```

### 4.2 Migration Steps Per Feature

For each feature module (e.g., Tickets):

1. **Prepare API Endpoints**
   - Audit existing `/api/v2/tickets/*` endpoints
   - Add missing endpoints if needed
   - Document API contracts

2. **Create React Feature Module**
   - Set up folder structure
   - Define TypeScript types
   - Create API integration layer
   - Build React Query hooks

3. **Build Components (Inside-Out)**
   - Start with smallest, reusable components
   - Compose into larger container components
   - Add routing for the feature

4. **Parallel Deployment**
   - Deploy React version alongside Jinja2
   - Feature flag or URL-based routing
   - Collect user feedback

5. **Cutover**
   - Redirect traffic to React version
   - Monitor for issues
   - Deprecate Jinja2 template

6. **Cleanup**
   - Remove legacy template
   - Update documentation

### 4.3 Parallel Running Strategy

During migration, both systems run simultaneously:

```
┌───────────────────────────────────────────────────────────────┐
│                         Nginx/LB                               │
├───────────────────────────────────────────────────────────────┤
│                                                                │
│   /login, /logout           →  Flask (Auth)                   │
│   /api/v2/*                 →  Flask (API)                    │
│   /legacy/tickets/*         →  Flask (Jinja2)                 │
│   /app/tickets/*            →  React SPA                      │
│                                                                │
└───────────────────────────────────────────────────────────────┘
```

Feature toggles control which UI users see:
- Staff can opt-in to React UI early
- Gradual rollout by user cohort
- Instant rollback capability

---

## 5. Priority Matrix

### 5.1 Template Complexity Score

Formula: `Complexity = (Lines * 0.4) + (Dependencies * 30) + (Business Logic * 50)`

### 5.2 Priority Matrix

| Template/Feature | Lines | Complexity | Business Value | Migration Difficulty | Priority Score | Recommended Phase |
|------------------|-------|------------|----------------|---------------------|----------------|-------------------|
| **Auth (login/register)** | 1,500 | Low | Critical | Low | 95 | Phase 1 |
| **tickets/list.html** | 3,799 | High | Critical | Medium | 90 | Phase 2 |
| **tickets/create.html** | 3,623 | Medium | Critical | Medium | 88 | Phase 2 |
| **tickets/view.html** | 13,945 | Very High | Critical | Very High | 85 | Phase 2-3 |
| **inventory/index.html** | ~600 | Low | Critical | Low | 85 | Phase 2 |
| **inventory/view_asset.html** | ~1,000 | Medium | High | Medium | 80 | Phase 2 |
| **home_v2.html (Dashboard)** | 2,778 | Medium | High | Medium | 78 | Phase 2 |
| **admin/users.html** | 1,003 | Medium | High | Low | 75 | Phase 3 |
| **reports/index.html** | 1,433 | Medium | High | Medium | 72 | Phase 3 |
| **reports/dashboard_builder** | 2,671 | High | Medium | High | 68 | Phase 4 |
| **knowledge/article_detail** | 1,266 | Low | Medium | Low | 60 | Phase 4 |
| **development/**** | 8,000 | Medium | Low | Medium | 40 | Phase 5 |

### 5.3 Feature Groupings

**Group A - Core Workflow (Phase 1-2)**
- Authentication
- Ticket List/Detail/Create
- Inventory List/Asset Detail
- Dashboard

**Group B - Management (Phase 3)**
- Admin: Users, Companies, Queues
- Customer Management
- Accessory Management

**Group C - Reporting (Phase 4)**
- Reports Builder
- SLA Dashboard
- Case Reports

**Group D - Supporting (Phase 5)**
- Knowledge Base
- Development Tools
- Documents/Shipments
- Widget Showcase

### 5.4 Ticket Detail Decomposition

The `tickets/view.html` (13,945 lines) should decompose into:

```
TicketDetailPage/
├── TicketHeader           (~200 lines)  - ID, status, priority badges
├── TicketInfoCard         (~300 lines)  - Key ticket metadata
├── TicketDescription      (~150 lines)  - Subject, description
├── TicketAssignee         (~200 lines)  - Assignment controls
├── TicketStatus           (~250 lines)  - Status change workflow
├── TicketTimeline         (~400 lines)  - Activity history
├── TicketComments         (~500 lines)  - Comment thread
│   ├── CommentForm        (~200 lines)  - With @mentions
│   └── CommentItem        (~150 lines)  - Single comment
├── TicketAttachments      (~400 lines)  - File list + upload
├── TicketAssets           (~600 lines)  - Linked assets
│   ├── AssetList
│   └── AssetAddModal
├── TicketAccessories      (~400 lines)  - Linked accessories
├── TicketShipping         (~500 lines)  - Shipping info + tracking
├── TicketIssues           (~350 lines)  - Issue reports
├── TicketServiceRecords   (~400 lines)  - Service history
└── TicketSidebar          (~300 lines)  - Quick actions, related
                          ─────────────
                          ~4,650 lines  (vs 13,945 - 67% reduction)
```

---

## 6. Timeline and Phases

### 6.1 Overall Timeline: 12-18 Months

```
Month  1  2  3  4  5  6  7  8  9  10  11  12  13  14  15  16  17  18
       │──────────│──────────────────│────────────│──────────────────│
       Phase 1    Phase 2            Phase 3      Phase 4-5
       Foundation Core Features       Management   Polish & Migrate
```

### 6.2 Phase Details

#### Phase 1: Foundation (Months 1-4)

**Goals:**
- Set up React project with TypeScript, Vite, Tailwind
- Establish component library and design system
- Implement authentication bridge
- Create shared utilities and API layer
- Build CI/CD pipeline for React

**Deliverables:**
- [ ] React project scaffold with folder structure
- [ ] Shared UI component library (Button, Input, Modal, Table, etc.)
- [ ] API client with interceptors
- [ ] Auth provider and protected routes
- [ ] Zustand stores setup
- [ ] React Query configuration
- [ ] Login page (React version)
- [ ] Basic layout (Sidebar, Header)
- [ ] CI/CD pipeline with tests

**Team:** 2-3 frontend engineers

#### Phase 2: Core Features (Months 5-8)

**Goals:**
- Migrate ticket management (highest business value)
- Migrate inventory core views
- Implement dashboard

**Deliverables:**
- [ ] Ticket List with filtering, sorting, pagination
- [ ] Ticket Detail (decomposed as above)
- [ ] Ticket Create/Edit forms
- [ ] Inventory List (assets, accessories)
- [ ] Asset Detail view
- [ ] Dashboard with widgets
- [ ] Queue selector/filter

**Team:** 3-4 frontend engineers, 1 backend engineer

#### Phase 3: Management Features (Months 9-11)

**Goals:**
- Admin console migration
- Customer management
- User management

**Deliverables:**
- [ ] User management (list, create, edit, permissions)
- [ ] Company management
- [ ] Queue management
- [ ] Customer management
- [ ] Accessory management with checkout flow
- [ ] Group management

**Team:** 2-3 frontend engineers, 1 backend engineer

#### Phase 4-5: Complete Migration (Months 12-18)

**Goals:**
- Migrate remaining features
- Performance optimization
- Legacy deprecation

**Deliverables:**
- [ ] Reports module
- [ ] SLA dashboard
- [ ] Knowledge base
- [ ] Documents/shipments
- [ ] Development tools
- [ ] Performance audit and optimization
- [ ] Legacy template removal
- [ ] Documentation update

**Team:** 2-3 engineers (can reduce as scope narrows)

---

## 7. Risk Assessment

### 7.1 Risk Matrix

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Scope creep** | High | High | Strict feature parity first; enhancements after migration |
| **API gaps discovered late** | Medium | High | Audit API early in each phase; involve backend team |
| **Performance regression** | Medium | High | Performance budget; benchmark against current app |
| **User adoption resistance** | Medium | Medium | Gradual rollout; training; collect feedback early |
| **Authentication complexity** | Medium | High | Invest in auth bridge early; test thoroughly |
| **Timeline slippage** | High | Medium | Buffer time; prioritize ruthlessly; cut scope if needed |
| **Key developer departure** | Low | High | Documentation; knowledge sharing; avoid single points of failure |
| **Data synchronization issues** | Low | High | Single source of truth (API v2); avoid client-side state duplication |

### 7.2 Technical Risks

1. **Large Bundle Size**
   - Risk: React app becomes too large
   - Mitigation: Code splitting, lazy loading, bundle analysis

2. **SEO Impact**
   - Risk: SPA reduces search engine visibility
   - Mitigation: SSR for public pages if needed (Next.js evaluation for future)

3. **Browser Compatibility**
   - Risk: Modern JS breaks older browsers
   - Mitigation: Define browser support matrix; use appropriate polyfills

4. **Real-time Features**
   - Risk: Current templates may have WebSocket/polling patterns
   - Mitigation: Audit real-time needs; implement React Query polling or Socket.io

### 7.3 Organizational Risks

1. **Parallel System Maintenance**
   - Risk: Bug fixes need to be applied to both systems
   - Mitigation: Feature freeze on migrated modules; quick cutover

2. **Testing Overhead**
   - Risk: Need to test both systems during migration
   - Mitigation: Automated E2E tests; shared test scenarios

---

## 8. Team Structure

### 8.1 Recommended Team Composition

**Phase 1-2 (Foundation + Core):**

| Role | Count | Responsibilities |
|------|-------|------------------|
| Tech Lead | 1 | Architecture decisions, code reviews, standards |
| Senior Frontend Engineer | 2 | Component library, complex features |
| Frontend Engineer | 2 | Feature development, testing |
| Backend Engineer | 1 | API enhancements, authentication |
| QA Engineer | 1 | Test automation, regression testing |
| **Total** | **7** | |

**Phase 3-5 (Maintenance + Complete):**

| Role | Count | Notes |
|------|-------|-------|
| Tech Lead | 1 | Can transition to part-time oversight |
| Senior Frontend Engineer | 1-2 | |
| Frontend Engineer | 1-2 | |
| Backend Engineer | 0.5 | As-needed API support |
| QA Engineer | 1 | |
| **Total** | **4-6** | |

### 8.2 Responsibilities

**Tech Lead:**
- Define coding standards and architecture patterns
- Review all PRs for architectural consistency
- Make technology decisions
- Coordinate with backend team
- Manage technical debt

**Senior Frontend Engineers:**
- Build component library
- Implement complex features (Ticket Detail, Dashboard Builder)
- Mentor junior developers
- Performance optimization

**Frontend Engineers:**
- Implement feature modules
- Write unit and integration tests
- Participate in code reviews

**Backend Engineer:**
- Extend API v2 as needed
- Authentication integration
- Performance optimization on API side

**QA Engineer:**
- Define test strategy
- Write E2E tests (Playwright/Cypress)
- Regression testing
- Performance testing

### 8.3 Ceremonies

- **Daily Standup:** 15 min sync
- **Sprint Planning:** Bi-weekly, 2-hour sessions
- **Sprint Review:** Demo migrated features to stakeholders
- **Retro:** Bi-weekly, process improvement
- **Architecture Review:** Weekly, 1 hour for design decisions

---

## 9. Success Metrics

### 9.1 Technical Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Lighthouse Performance Score** | > 80 | Per-page audit |
| **Time to Interactive (TTI)** | < 3s | Core Web Vitals |
| **Bundle Size (gzipped)** | < 250KB initial | Webpack bundle analyzer |
| **Code Coverage** | > 80% | Jest coverage report |
| **Type Coverage** | > 95% | TypeScript strict mode |
| **API Response Time** | < 200ms (p95) | APM monitoring |

### 9.2 Business Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Template Migration Rate** | 100% by Month 18 | Count of migrated templates |
| **User Adoption** | > 90% using React UI | Analytics |
| **Bug Report Reduction** | 30% decrease | Support tickets |
| **Feature Delivery Speed** | 50% faster | Sprint velocity |
| **Developer Satisfaction** | > 4/5 | Team surveys |

### 9.3 Quality Gates

Before each phase cutover:
- [ ] All unit tests passing
- [ ] E2E tests covering critical paths
- [ ] Performance benchmarks met
- [ ] Accessibility audit passed (WCAG 2.1 AA)
- [ ] Security review completed
- [ ] User acceptance testing completed
- [ ] Rollback plan documented

---

## 10. Appendices

### 10.1 Template Inventory (Complete)

See attached spreadsheet with all 236 templates, line counts, and categorization.

**Summary by Directory:**

| Directory | Count | Total Lines (Est.) |
|-----------|-------|-------------------|
| tickets/ | 19 | 28,000 |
| inventory/ | 42 | 18,000 |
| admin/ | 40 | 15,000 |
| widgets/ | 35 | 12,000 |
| development/ | 31 | 8,000 |
| knowledge/ | 9 | 3,500 |
| reports/ | 9 | 7,000 |
| shipments/ | 8 | 2,000 |
| documents/ | 8 | 2,500 |
| auth/ | 6 | 1,500 |
| Other (root, misc) | 29 | 27,500 |
| **Total** | **236** | **~125,000** |

### 10.2 API v2 Endpoint Inventory

| Module | Endpoints | Status |
|--------|-----------|--------|
| /api/v2/tickets | GET, POST, PUT, /assign, /status | Ready |
| /api/v2/assets | GET, POST, PUT, DELETE, /image | Ready |
| /api/v2/accessories | GET, POST, PUT, DELETE, /return | Ready |
| /api/v2/customers | CRUD | Ready |
| /api/v2/admin | Users, Companies, Queues, Categories | Ready |
| /api/v2/attachments | Upload, Delete | Ready |
| /api/v2/service_records | CRUD | Ready |
| /api/v2/reports | List, Generate | Ready |
| /api/v2/dashboard | Widgets, Data | Ready |
| /api/v2/system_settings | CRUD | Ready |
| /api/v2/user_preferences | GET, PUT | Ready |
| /api/v2/health | Health check | Ready |

### 10.3 Component Library Checklist

**Base Components (Phase 1):**
- [ ] Button (variants: primary, secondary, danger, ghost)
- [ ] Input (text, email, password, textarea)
- [ ] Select / Dropdown
- [ ] Checkbox / Radio
- [ ] Modal / Dialog
- [ ] Toast / Notification
- [ ] Table (with sorting, pagination)
- [ ] Tabs
- [ ] Card
- [ ] Badge / Tag
- [ ] Avatar
- [ ] Spinner / Loader
- [ ] EmptyState
- [ ] Tooltip
- [ ] Popover

**Layout Components:**
- [ ] Sidebar
- [ ] Header / Navbar
- [ ] PageHeader (with breadcrumbs)
- [ ] MainLayout
- [ ] GridLayout

**Feature Components:**
- [ ] DataTable (TanStack)
- [ ] DatePicker
- [ ] FileUpload
- [ ] RichTextEditor
- [ ] SearchInput with autocomplete
- [ ] MentionInput

### 10.4 Glossary

| Term | Definition |
|------|------------|
| **Strangler Fig Pattern** | Incremental migration where new system gradually replaces old |
| **SPA** | Single Page Application |
| **SSR** | Server-Side Rendering |
| **TTI** | Time to Interactive |
| **Zustand** | Lightweight state management library |
| **React Query** | Data fetching/caching library (TanStack Query) |
| **Headless UI** | Unstyled, accessible UI primitives |

---

## Document Approval

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Lead Developer | | | |
| Engineering Manager | | | |
| Product Owner | | | |
| CTO | | | |

---

*This document is a living artifact and should be updated as the migration progresses.*
