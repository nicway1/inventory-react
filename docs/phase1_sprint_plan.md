# Phase 1 Sprint Plan: React Migration Foundation

## Asset Management System - React Migration

**Document Version:** 1.0
**Date:** February 7, 2026
**Phase Duration:** 16 Weeks (Months 1-4)
**Sprint Length:** 2 Weeks

---

## Executive Summary

Phase 1 establishes the foundation for the React migration, focusing on infrastructure, authentication, core component library, and navigation/layout systems. The React project scaffold already exists in `/frontend/` with Vite, TypeScript, Tailwind CSS, React Query, and Zustand configured.

### Phase 1 Objectives

| Objective | Status | Target Sprint |
|-----------|--------|---------------|
| React foundation setup | DONE | Pre-Phase 1 |
| CI/CD pipeline | Pending | Sprint 1 |
| Authentication system | Pending | Sprint 2 |
| Base layout (sidebar, header, navigation) | Pending | Sprint 5-6 |
| Core component library (atoms, molecules) | Pending | Sprint 3-4 |
| Theme system (light, dark, liquid-glass) | Pending | Sprint 1 |

### Team Allocation

| Role | Allocation | Primary Responsibilities |
|------|------------|--------------------------|
| Tech Lead | 100% | Architecture, code reviews, standards |
| Senior Frontend Engineer | 100% | Component library, complex features |
| Frontend Engineer | 100% | Feature development, testing |
| Backend Engineer | 25% | Auth endpoints, API support |
| QA Engineer | 50% | Test automation, quality gates |

---

## Sprint Overview

```
Week  1   2   3   4   5   6   7   8   9  10  11  12  13  14  15  16
      |-----|-----|-----|-----|-----|-----|-----|
      Spr 1 Spr 2 Spr 3 Spr 4  Sprint 5-6   Sprint 7-8
      Found Auth  Atoms Orgs  Navigation   Integration
```

---

## Sprint 1: Foundation & Infrastructure (Weeks 1-2)

### Sprint Goal
Establish development infrastructure, CI/CD pipeline, and theme system foundation.

### User Stories

#### US-1.1: CI/CD Pipeline Setup
**As a** developer
**I want** automated build, test, and deployment pipelines
**So that** code quality is maintained and deployments are consistent

**Acceptance Criteria:**
- [ ] GitHub Actions workflow for PR checks (lint, type-check, unit tests)
- [ ] GitHub Actions workflow for deployment to staging
- [ ] Build artifacts generated and stored
- [ ] Branch protection rules configured for `main` and `develop`
- [ ] Automated version bumping on merge to main

**Story Points:** 8

**Tasks:**
1. Create `.github/workflows/ci.yml` for PR checks
2. Create `.github/workflows/deploy-staging.yml`
3. Configure branch protection rules
4. Set up semantic versioning with conventional commits
5. Document CI/CD process in README

---

#### US-1.2: ESLint, Prettier, and Husky Configuration
**As a** developer
**I want** consistent code formatting and linting
**So that** the codebase maintains quality standards

**Acceptance Criteria:**
- [ ] ESLint configured with React, TypeScript, and accessibility rules
- [ ] Prettier configured with project-specific settings
- [ ] Husky pre-commit hooks run lint and format checks
- [ ] lint-staged configured for staged files only
- [ ] VS Code settings shared for team consistency

**Story Points:** 5

**Tasks:**
1. Extend `.eslintrc.cjs` with additional rules
2. Create `.prettierrc` configuration
3. Install and configure Husky
4. Configure lint-staged in package.json
5. Create `.vscode/settings.json` and `.vscode/extensions.json`

---

#### US-1.3: Theme Provider Implementation
**As a** user
**I want** to switch between light, dark, and liquid-glass themes
**So that** I can customize my viewing experience

**Acceptance Criteria:**
- [ ] ThemeContext provides current theme and toggle function
- [ ] Theme persists to localStorage
- [ ] Theme respects system preference on first load
- [ ] CSS variables defined for all theme tokens
- [ ] Smooth transition between themes (150ms)
- [ ] useTheme hook available for components

**Story Points:** 8

**Tasks:**
1. Create `src/context/ThemeContext.tsx`
2. Create `src/hooks/useTheme.ts`
3. Define CSS variables in `src/styles/themes.css`
4. Implement localStorage persistence
5. Add system preference detection
6. Create theme toggle component for testing

---

#### US-1.4: Design Tokens Setup
**As a** developer
**I want** centralized design tokens
**So that** styling is consistent across all components

**Acceptance Criteria:**
- [ ] Color palette defined matching current Tailwind config
- [ ] Typography scale defined (headings, body, labels)
- [ ] Spacing scale defined (4px base)
- [ ] Border radius scale defined
- [ ] Shadow definitions created
- [ ] Tokens exported as TypeScript constants
- [ ] Tokens integrated with Tailwind config

**Story Points:** 5

**Tasks:**
1. Create `src/design-tokens/colors.ts`
2. Create `src/design-tokens/typography.ts`
3. Create `src/design-tokens/spacing.ts`
4. Create `src/design-tokens/shadows.ts`
5. Create `src/design-tokens/borders.ts`
6. Update `tailwind.config.js` to use tokens

---

#### US-1.5: Storybook Setup
**As a** developer
**I want** Storybook for component documentation
**So that** components can be developed and reviewed in isolation

**Acceptance Criteria:**
- [ ] Storybook 7.x installed and configured
- [ ] Tailwind CSS integrated with Storybook
- [ ] Theme switcher addon working
- [ ] Accessibility addon configured
- [ ] Documentation template created
- [ ] Storybook builds successfully

**Story Points:** 5

**Tasks:**
1. Install Storybook with Vite builder
2. Configure Storybook for Tailwind
3. Add @storybook/addon-a11y
4. Add @storybook/addon-themes
5. Create component documentation template
6. Add Storybook build to CI pipeline

---

### Sprint 1 Capacity

| Story | Points | Assignee |
|-------|--------|----------|
| US-1.1: CI/CD Pipeline | 8 | Tech Lead |
| US-1.2: ESLint/Prettier/Husky | 5 | Frontend Engineer |
| US-1.3: Theme Provider | 8 | Senior Frontend Engineer |
| US-1.4: Design Tokens | 5 | Senior Frontend Engineer |
| US-1.5: Storybook Setup | 5 | Frontend Engineer |
| **Total** | **31** | |

### Sprint 1 Dependencies
- None (foundation sprint)

### Sprint 1 Risks
| Risk | Mitigation |
|------|------------|
| CI/CD complexity with existing infrastructure | Start with minimal viable pipeline, iterate |
| Theme system affecting existing styles | Scope to React app only initially |

---

## Sprint 2: Authentication System (Weeks 3-4)

### Sprint Goal
Implement complete authentication flow with JWT tokens, protected routes, and session management.

### User Stories

#### US-2.1: Login Page
**As a** user
**I want** to log in with my credentials
**So that** I can access the system

**Acceptance Criteria:**
- [ ] Login form with email and password fields
- [ ] Form validation with error messages
- [ ] Loading state during authentication
- [ ] Error handling for invalid credentials
- [ ] "Remember me" checkbox option
- [ ] Link to password reset (placeholder)
- [ ] Responsive design (mobile-friendly)
- [ ] Accessibility compliant (WCAG 2.1 AA)

**Story Points:** 8

**Tasks:**
1. Create `src/pages/auth/LoginPage.tsx`
2. Create login form with react-hook-form + zod
3. Implement form validation schema
4. Add loading spinner during auth
5. Handle API error responses
6. Add "remember me" functionality
7. Style with Tailwind (all themes)
8. Add unit tests

---

#### US-2.2: JWT Token Handling
**As a** developer
**I want** secure JWT token management
**So that** API requests are authenticated

**Acceptance Criteria:**
- [ ] Token stored securely (httpOnly cookie preferred, localStorage fallback)
- [ ] Token attached to all API requests via Axios interceptor
- [ ] Token refresh before expiration
- [ ] Automatic logout on token expiration
- [ ] Token cleared on logout
- [ ] XSS protection measures implemented

**Story Points:** 8

**Tasks:**
1. Create `src/services/auth.service.ts`
2. Implement token storage utility
3. Configure Axios request interceptor
4. Implement token refresh logic
5. Add token expiration monitoring
6. Create logout handler
7. Add security headers

---

#### US-2.3: Auth Context & Provider
**As a** developer
**I want** centralized authentication state
**So that** components can access user information

**Acceptance Criteria:**
- [ ] AuthContext provides user, isAuthenticated, isLoading
- [ ] AuthProvider wraps application
- [ ] useAuth hook for consuming auth state
- [ ] Initial auth check on app load
- [ ] User permissions available via context
- [ ] Type-safe user object

**Story Points:** 5

**Tasks:**
1. Create `src/context/AuthContext.tsx`
2. Create `src/hooks/useAuth.ts`
3. Define User and Permission types
4. Implement initial auth verification
5. Add permission checking utilities
6. Integrate with existing `auth.store.ts`

---

#### US-2.4: Protected Routes
**As a** developer
**I want** route protection based on authentication
**So that** unauthenticated users cannot access protected pages

**Acceptance Criteria:**
- [ ] ProtectedRoute component wraps authenticated pages
- [ ] Unauthenticated users redirected to login
- [ ] Return URL preserved for post-login redirect
- [ ] Role-based route protection
- [ ] Loading state while checking auth
- [ ] 403 page for unauthorized access

**Story Points:** 5

**Tasks:**
1. Create `src/components/auth/ProtectedRoute.tsx`
2. Create `src/components/auth/RoleGuard.tsx`
3. Implement redirect with return URL
4. Create loading component for auth check
5. Create 403 Forbidden page
6. Add route protection to router config

---

#### US-2.5: Session Management
**As a** user
**I want** my session managed securely
**So that** I stay logged in appropriately

**Acceptance Criteria:**
- [ ] Session timeout after inactivity (configurable)
- [ ] Warning modal before session expires
- [ ] Extend session option
- [ ] Multiple tab session synchronization
- [ ] Logout from all devices option
- [ ] Session activity tracked

**Story Points:** 8

**Tasks:**
1. Create `src/hooks/useSessionTimeout.ts`
2. Create session warning modal
3. Implement activity tracking
4. Add cross-tab session sync with BroadcastChannel
5. Create logout all sessions API call
6. Add session extension functionality

---

#### US-2.6: Backend Auth Endpoints Enhancement
**As a** frontend developer
**I want** enhanced auth API endpoints
**So that** the React app can authenticate properly

**Acceptance Criteria:**
- [ ] POST /api/v2/auth/login returns JWT + user data
- [ ] POST /api/v2/auth/logout invalidates token
- [ ] POST /api/v2/auth/refresh returns new token
- [ ] GET /api/v2/auth/me returns current user
- [ ] Consistent error response format
- [ ] Rate limiting on auth endpoints

**Story Points:** 5

**Tasks:**
1. Review existing auth endpoints
2. Add /api/v2/auth/login endpoint
3. Add /api/v2/auth/refresh endpoint
4. Add /api/v2/auth/me endpoint
5. Implement rate limiting
6. Document API contracts

---

### Sprint 2 Capacity

| Story | Points | Assignee |
|-------|--------|----------|
| US-2.1: Login Page | 8 | Frontend Engineer |
| US-2.2: JWT Token Handling | 8 | Senior Frontend Engineer |
| US-2.3: Auth Context & Provider | 5 | Senior Frontend Engineer |
| US-2.4: Protected Routes | 5 | Frontend Engineer |
| US-2.5: Session Management | 8 | Senior Frontend Engineer |
| US-2.6: Backend Auth Endpoints | 5 | Backend Engineer |
| **Total** | **39** | |

### Sprint 2 Dependencies
- Sprint 1: Theme Provider (for login page styling)
- Sprint 1: Design Tokens (for consistent styling)

### Sprint 2 Risks
| Risk | Mitigation |
|------|------------|
| JWT vs session cookie decision | Implement dual-auth bridge per migration strategy |
| Session sync complexity | Start with single-tab, add multi-tab in iteration |

---

## Sprint 3: Atoms & Core Molecules (Weeks 5-6)

### Sprint Goal
Build the foundational atomic components and essential molecules with full theme support and Storybook documentation.

### User Stories

#### US-3.1: Button Component
**As a** developer
**I want** a reusable Button component
**So that** buttons are consistent across the application

**Acceptance Criteria:**
- [ ] Variants: primary, secondary, danger, ghost, icon
- [ ] Sizes: sm, md, lg
- [ ] States: default, hover, active, focus, disabled, loading
- [ ] Left and right icon support
- [ ] Full width option
- [ ] All three themes supported
- [ ] Keyboard accessible
- [ ] Storybook documentation with all variants

**Story Points:** 5

**Tasks:**
1. Create `src/components/atoms/Button/Button.tsx`
2. Create `src/components/atoms/Button/Button.stories.tsx`
3. Create `src/components/atoms/Button/Button.test.tsx`
4. Implement all variants and sizes
5. Add loading spinner
6. Add accessibility attributes

---

#### US-3.2: Input Component
**As a** developer
**I want** a reusable Input component
**So that** form inputs are consistent

**Acceptance Criteria:**
- [ ] Types: text, email, password, search, number, date
- [ ] States: default, focus, error, disabled, read-only
- [ ] Label integration
- [ ] Help text and error text support
- [ ] Left and right icon/addon support
- [ ] Password visibility toggle
- [ ] Search clear button
- [ ] Storybook documentation

**Story Points:** 8

**Tasks:**
1. Create `src/components/atoms/Input/Input.tsx`
2. Create `src/components/atoms/Input/Input.stories.tsx`
3. Create `src/components/atoms/Input/Input.test.tsx`
4. Implement all input types
5. Add password toggle functionality
6. Add search clear functionality
7. Style for all themes

---

#### US-3.3: Badge Component
**As a** developer
**I want** a reusable Badge component
**So that** status indicators are consistent

**Acceptance Criteria:**
- [ ] Variants: default, success, warning, danger, info, purple
- [ ] Sizes: sm, md, lg
- [ ] Optional dot indicator
- [ ] Removable variant with X button
- [ ] Status-to-variant mapping utility
- [ ] Storybook documentation

**Story Points:** 3

**Tasks:**
1. Create `src/components/atoms/Badge/Badge.tsx`
2. Create `src/components/atoms/Badge/Badge.stories.tsx`
3. Create status mapping utility
4. Style for all themes
5. Add unit tests

---

#### US-3.4: Icon Component
**As a** developer
**I want** a reusable Icon wrapper component
**So that** icons have consistent sizing and styling

**Acceptance Criteria:**
- [ ] Wraps Heroicons (primary) and Font Awesome (legacy)
- [ ] Sizes: xs, sm, md, lg, xl
- [ ] Color prop with theme awareness
- [ ] Spin and pulse animations
- [ ] Accessibility (aria-hidden when decorative)
- [ ] Storybook icon gallery

**Story Points:** 3

**Tasks:**
1. Create `src/components/atoms/Icon/Icon.tsx`
2. Create icon registry for commonly used icons
3. Add size mappings
4. Create Storybook icon gallery
5. Add unit tests

---

#### US-3.5: Spinner & Loading Components
**As a** developer
**I want** loading indicator components
**So that** loading states are clear to users

**Acceptance Criteria:**
- [ ] Spinner component with sizes
- [ ] Full page loading overlay
- [ ] Inline loading text
- [ ] Skeleton loader component
- [ ] Theme-aware colors
- [ ] Storybook documentation

**Story Points:** 3

**Tasks:**
1. Create `src/components/atoms/Spinner/Spinner.tsx`
2. Create `src/components/atoms/Skeleton/Skeleton.tsx`
3. Create loading overlay component
4. Style for all themes
5. Add Storybook stories

---

#### US-3.6: Avatar Component
**As a** developer
**I want** an Avatar component
**So that** user images are displayed consistently

**Acceptance Criteria:**
- [ ] Sizes: xs, sm, md, lg, xl
- [ ] Image with fallback to initials
- [ ] Online/offline status indicator
- [ ] Stacked avatar group
- [ ] Theme-aware placeholder colors
- [ ] Storybook documentation

**Story Points:** 3

**Tasks:**
1. Create `src/components/atoms/Avatar/Avatar.tsx`
2. Create `src/components/atoms/AvatarGroup/AvatarGroup.tsx`
3. Implement initials fallback
4. Add status indicator
5. Add Storybook stories

---

#### US-3.7: Tooltip Component
**As a** developer
**I want** a Tooltip component
**So that** additional context is available on hover

**Acceptance Criteria:**
- [ ] Positions: top, bottom, left, right
- [ ] Trigger: hover, click, focus
- [ ] Delay configuration
- [ ] Arrow pointer
- [ ] Theme-aware styling
- [ ] Accessible (role="tooltip", aria-describedby)
- [ ] Storybook documentation

**Story Points:** 5

**Tasks:**
1. Create `src/components/atoms/Tooltip/Tooltip.tsx`
2. Use Headless UI Popover or custom implementation
3. Implement positioning logic
4. Add accessibility attributes
5. Style for all themes
6. Add Storybook stories

---

#### US-3.8: Card Component
**As a** developer
**I want** a Card component
**So that** content sections are visually grouped

**Acceptance Criteria:**
- [ ] Card, CardHeader, CardBody, CardFooter subcomponents
- [ ] Variants: default, bordered, elevated
- [ ] Collapsible option with animation
- [ ] Header with title, subtitle, and actions
- [ ] Theme-aware styling (matches sf-card)
- [ ] Storybook documentation

**Story Points:** 5

**Tasks:**
1. Create `src/components/molecules/Card/Card.tsx`
2. Create CardHeader, CardBody, CardFooter components
3. Implement collapse animation
4. Style to match existing sf-card
5. Add Storybook stories
6. Add unit tests

---

#### US-3.9: Dropdown Component
**As a** developer
**I want** a Dropdown component
**So that** menu and select patterns are consistent

**Acceptance Criteria:**
- [ ] Menu variant (action list)
- [ ] Select variant (form input)
- [ ] Multi-select variant
- [ ] Search/filter within dropdown
- [ ] Keyboard navigation
- [ ] Grouped items with headers
- [ ] Icons and shortcuts display
- [ ] Danger item styling
- [ ] Theme-aware styling
- [ ] Storybook documentation

**Story Points:** 8

**Tasks:**
1. Create `src/components/molecules/Dropdown/Dropdown.tsx`
2. Use Headless UI Menu/Listbox
3. Implement keyboard navigation
4. Add search/filter functionality
5. Style for all themes
6. Add Storybook stories
7. Add unit tests

---

#### US-3.10: FormGroup Component
**As a** developer
**I want** a FormGroup component
**So that** form fields have consistent layout

**Acceptance Criteria:**
- [ ] Label with required indicator
- [ ] Input slot (children)
- [ ] Help text below input
- [ ] Error text with icon
- [ ] Horizontal and vertical layouts
- [ ] Theme-aware styling
- [ ] Storybook documentation

**Story Points:** 3

**Tasks:**
1. Create `src/components/molecules/FormGroup/FormGroup.tsx`
2. Implement layout variants
3. Style error states
4. Add Storybook stories
5. Add unit tests

---

### Sprint 3 Capacity

| Story | Points | Assignee |
|-------|--------|----------|
| US-3.1: Button | 5 | Senior Frontend Engineer |
| US-3.2: Input | 8 | Senior Frontend Engineer |
| US-3.3: Badge | 3 | Frontend Engineer |
| US-3.4: Icon | 3 | Frontend Engineer |
| US-3.5: Spinner/Loading | 3 | Frontend Engineer |
| US-3.6: Avatar | 3 | Frontend Engineer |
| US-3.7: Tooltip | 5 | Senior Frontend Engineer |
| US-3.8: Card | 5 | Senior Frontend Engineer |
| US-3.9: Dropdown | 8 | Senior Frontend Engineer |
| US-3.10: FormGroup | 3 | Frontend Engineer |
| **Total** | **46** | |

### Sprint 3 Dependencies
- Sprint 1: Theme Provider (components use theme context)
- Sprint 1: Design Tokens (consistent styling)
- Sprint 1: Storybook (documentation)

### Sprint 3 Risks
| Risk | Mitigation |
|------|------------|
| Component scope creep | Strict adherence to acceptance criteria |
| Theme complexity | Test all three themes early and often |

---

## Sprint 4: Organisms (Weeks 7-8)

### Sprint Goal
Build complex organisms including DataTable, Modal, Toast notifications, and Form components.

### User Stories

#### US-4.1: DataTable Component
**As a** developer
**I want** a full-featured DataTable component
**So that** list views are consistent and functional

**Acceptance Criteria:**
- [ ] Column definitions with accessor/cell render
- [ ] Sortable columns with indicators
- [ ] Row selection (single and multi)
- [ ] Row actions dropdown
- [ ] Fixed header on scroll
- [ ] Empty state
- [ ] Loading state with skeletons
- [ ] Column visibility toggle
- [ ] Bulk actions toolbar
- [ ] Row click handler
- [ ] Responsive behavior
- [ ] Theme-aware styling (matches sf-data-table)
- [ ] Storybook documentation

**Story Points:** 13

**Tasks:**
1. Create `src/components/organisms/DataTable/DataTable.tsx`
2. Use TanStack Table for headless logic
3. Implement sorting
4. Implement row selection
5. Create row actions dropdown
6. Add fixed header
7. Create empty and loading states
8. Add bulk actions toolbar
9. Style to match sf-data-table
10. Add Storybook stories
11. Add unit and integration tests

---

#### US-4.2: Modal System
**As a** developer
**I want** a Modal component system
**So that** dialogs are consistent and accessible

**Acceptance Criteria:**
- [ ] Sizes: sm, md, lg, xl, full
- [ ] Modal, ModalHeader, ModalBody, ModalFooter subcomponents
- [ ] Backdrop with click-to-close option
- [ ] Escape key to close
- [ ] Focus trap within modal
- [ ] Entry/exit animations
- [ ] Scroll lock on body
- [ ] Nested modals support
- [ ] Confirmation modal variant
- [ ] Theme-aware styling
- [ ] Storybook documentation

**Story Points:** 8

**Tasks:**
1. Create `src/components/organisms/Modal/Modal.tsx`
2. Use Headless UI Dialog
3. Implement subcomponents
4. Add animations with Framer Motion or CSS
5. Implement focus trap
6. Add scroll lock
7. Create confirmation modal variant
8. Add Storybook stories
9. Add unit tests

---

#### US-4.3: Toast Notification System
**As a** developer
**I want** a Toast notification system
**So that** feedback messages are displayed consistently

**Acceptance Criteria:**
- [ ] Types: success, error, warning, info, mention
- [ ] Positions: top-right, top-left, top-center, bottom-*
- [ ] Auto-dismiss with configurable duration
- [ ] Manual dismiss button
- [ ] Action button option
- [ ] Queue management (max visible)
- [ ] useToast hook for triggering
- [ ] ToastProvider for context
- [ ] Entry/exit animations
- [ ] Theme-aware styling
- [ ] Storybook documentation

**Story Points:** 8

**Tasks:**
1. Create `src/components/organisms/Toast/Toast.tsx`
2. Create `src/components/organisms/Toast/ToastContainer.tsx`
3. Create `src/context/ToastContext.tsx`
4. Create `src/hooks/useToast.ts`
5. Implement queue management
6. Add animations
7. Style for all toast types and themes
8. Add Storybook stories
9. Add unit tests

---

#### US-4.4: Form Component System
**As a** developer
**I want** a Form component system
**So that** forms are consistent and validated

**Acceptance Criteria:**
- [ ] Form wrapper with react-hook-form integration
- [ ] Automatic error display from form state
- [ ] Submit button with loading state
- [ ] Reset button
- [ ] Dirty state tracking
- [ ] Field-level and form-level validation
- [ ] Zod schema integration
- [ ] useFormField hook for custom fields
- [ ] Theme-aware styling
- [ ] Storybook documentation

**Story Points:** 8

**Tasks:**
1. Create `src/components/organisms/Form/Form.tsx`
2. Create `src/components/organisms/Form/FormField.tsx`
3. Create `src/hooks/useFormField.ts`
4. Integrate with react-hook-form
5. Add zod resolver
6. Implement submit and reset buttons
7. Add Storybook stories
8. Add integration tests

---

#### US-4.5: Select Component (Advanced)
**As a** developer
**I want** an advanced Select component
**So that** complex selections are handled

**Acceptance Criteria:**
- [ ] Single select
- [ ] Multi-select with chips
- [ ] Searchable/filterable
- [ ] Async option loading
- [ ] Grouped options
- [ ] Create new option
- [ ] Clear selection
- [ ] Disabled options
- [ ] Loading state
- [ ] Theme-aware styling
- [ ] Storybook documentation

**Story Points:** 8

**Tasks:**
1. Create `src/components/organisms/Select/Select.tsx`
2. Build on Dropdown component
3. Add multi-select with chips
4. Implement async loading
5. Add grouping support
6. Add create option functionality
7. Style for all themes
8. Add Storybook stories
9. Add unit tests

---

#### US-4.6: Tabs Component
**As a** developer
**I want** a Tabs component
**So that** content is organized in tabs

**Acceptance Criteria:**
- [ ] Horizontal and vertical orientations
- [ ] Tab with icon and badge
- [ ] Lazy loading of tab content
- [ ] Controlled and uncontrolled modes
- [ ] Keyboard navigation
- [ ] URL-synced tabs option
- [ ] Theme-aware styling (matches sf-tabs)
- [ ] Storybook documentation

**Story Points:** 5

**Tasks:**
1. Create `src/components/organisms/Tabs/Tabs.tsx`
2. Use Headless UI Tabs
3. Implement lazy loading
4. Add URL sync option
5. Style to match sf-tabs
6. Add Storybook stories
7. Add unit tests

---

### Sprint 4 Capacity

| Story | Points | Assignee |
|-------|--------|----------|
| US-4.1: DataTable | 13 | Senior Frontend Engineer |
| US-4.2: Modal System | 8 | Senior Frontend Engineer |
| US-4.3: Toast System | 8 | Frontend Engineer |
| US-4.4: Form System | 8 | Senior Frontend Engineer |
| US-4.5: Advanced Select | 8 | Frontend Engineer |
| US-4.6: Tabs | 5 | Frontend Engineer |
| **Total** | **50** | |

### Sprint 4 Dependencies
- Sprint 3: All atomic components (Button, Input, Badge, etc.)
- Sprint 3: Card, Dropdown components

### Sprint 4 Risks
| Risk | Mitigation |
|------|------------|
| DataTable complexity | Use TanStack Table; time-box features |
| Performance with large datasets | Implement virtualization if needed |

---

## Sprint 5-6: Navigation & Layout (Weeks 9-12)

### Sprint Goal
Build navigation components (Sidebar, Header, Breadcrumbs) and page layout templates.

### User Stories

#### US-5.1: Sidebar Navigation
**As a** user
**I want** a sidebar navigation
**So that** I can navigate between sections

**Acceptance Criteria:**
- [ ] Collapsible sidebar (expanded/collapsed states)
- [ ] Logo/brand area
- [ ] Navigation sections with headers
- [ ] Nav items with icons and labels
- [ ] Active state indication
- [ ] Badge/count indicators
- [ ] Nested navigation (submenus)
- [ ] Collapse persists to localStorage
- [ ] Mobile: off-canvas drawer
- [ ] Theme-aware styling
- [ ] Storybook documentation

**Story Points:** 13

**Tasks:**
1. Create `src/components/organisms/Sidebar/Sidebar.tsx`
2. Create `src/components/organisms/Sidebar/SidebarNav.tsx`
3. Create `src/components/organisms/Sidebar/NavItem.tsx`
4. Implement collapse/expand animation
5. Add mobile drawer behavior
6. Integrate with router for active state
7. Add localStorage persistence
8. Style for all themes
9. Add Storybook stories
10. Add unit tests

---

#### US-5.2: Header Component
**As a** user
**I want** a header with search and user menu
**So that** I can access global actions

**Acceptance Criteria:**
- [ ] Logo/brand (links to dashboard)
- [ ] Global search input with suggestions
- [ ] Notification bell with count
- [ ] User avatar with dropdown menu
- [ ] Quick actions (create ticket, etc.)
- [ ] Mobile: hamburger menu
- [ ] Theme toggle button
- [ ] Theme-aware styling
- [ ] Storybook documentation

**Story Points:** 8

**Tasks:**
1. Create `src/components/organisms/Header/Header.tsx`
2. Create `src/components/organisms/Header/GlobalSearch.tsx`
3. Create `src/components/organisms/Header/UserMenu.tsx`
4. Integrate search with API
5. Add notification badge
6. Implement theme toggle
7. Add mobile hamburger
8. Style for all themes
9. Add Storybook stories

---

#### US-5.3: Breadcrumb Component
**As a** user
**I want** breadcrumb navigation
**So that** I know my location in the app

**Acceptance Criteria:**
- [ ] Home icon as first item
- [ ] Clickable links to parent pages
- [ ] Current page (non-clickable)
- [ ] Truncation for long paths
- [ ] Icon support per item
- [ ] Auto-generation from route
- [ ] Theme-aware styling
- [ ] Storybook documentation

**Story Points:** 3

**Tasks:**
1. Create `src/components/molecules/Breadcrumb/Breadcrumb.tsx`
2. Create `src/hooks/useBreadcrumbs.ts`
3. Implement route-based auto-generation
4. Add truncation logic
5. Style for all themes
6. Add Storybook stories

---

#### US-5.4: Page Header Component
**As a** developer
**I want** a PageHeader component
**So that** page titles and actions are consistent

**Acceptance Criteria:**
- [ ] Title and optional subtitle
- [ ] Breadcrumb integration
- [ ] Action buttons area
- [ ] Record count display
- [ ] Back button option
- [ ] Theme-aware styling
- [ ] Storybook documentation

**Story Points:** 3

**Tasks:**
1. Create `src/components/molecules/PageHeader/PageHeader.tsx`
2. Integrate breadcrumb
3. Add action button slots
4. Style for all themes
5. Add Storybook stories

---

#### US-5.5: Main Layout Template
**As a** developer
**I want** a MainLayout template
**So that** pages have consistent structure

**Acceptance Criteria:**
- [ ] Sidebar (collapsible)
- [ ] Header
- [ ] Main content area with scrolling
- [ ] Footer (optional)
- [ ] Responsive behavior
- [ ] Loading state for layout
- [ ] Theme class applied to root
- [ ] Storybook documentation

**Story Points:** 5

**Tasks:**
1. Create `src/components/templates/MainLayout/MainLayout.tsx`
2. Compose Sidebar, Header components
3. Implement responsive behavior
4. Add theme class management
5. Add Storybook stories

---

#### US-5.6: List View Layout Template
**As a** developer
**I want** a ListViewLayout template
**So that** list pages are consistent

**Acceptance Criteria:**
- [ ] PageHeader with title and actions
- [ ] Filter toolbar area
- [ ] View tabs (predefined filters)
- [ ] DataTable or CardGrid slot
- [ ] Pagination footer
- [ ] Empty state handling
- [ ] Loading state
- [ ] Storybook documentation

**Story Points:** 5

**Tasks:**
1. Create `src/components/templates/ListViewLayout/ListViewLayout.tsx`
2. Integrate PageHeader and DataTable
3. Add filter toolbar
4. Add view tabs
5. Handle empty and loading states
6. Add Storybook stories

---

#### US-5.7: Record Detail Layout Template
**As a** developer
**I want** a RecordDetailLayout template
**So that** detail pages are consistent

**Acceptance Criteria:**
- [ ] Record header with title, status, actions
- [ ] Highlight panel (key info)
- [ ] Tab navigation
- [ ] Main content area (field sections)
- [ ] Related lists sidebar or section
- [ ] Activity timeline section
- [ ] Edit mode support
- [ ] Loading state
- [ ] Storybook documentation

**Story Points:** 8

**Tasks:**
1. Create `src/components/templates/RecordDetailLayout/RecordDetailLayout.tsx`
2. Create RecordHeader component
3. Create FieldSection component
4. Create RelatedList component
5. Implement edit mode
6. Add loading state
7. Add Storybook stories

---

#### US-5.8: Pagination Component
**As a** developer
**I want** a Pagination component
**So that** list navigation is consistent

**Acceptance Criteria:**
- [ ] Variants: simple, numbered, compact
- [ ] Page size selector
- [ ] Total items/pages display
- [ ] First/last page buttons
- [ ] Ellipsis for large page counts
- [ ] Keyboard accessible
- [ ] Theme-aware styling
- [ ] Storybook documentation

**Story Points:** 5

**Tasks:**
1. Create `src/components/molecules/Pagination/Pagination.tsx`
2. Implement all variants
3. Add page size selector
4. Add keyboard navigation
5. Style for all themes
6. Add Storybook stories

---

### Sprint 5-6 Capacity (4 weeks)

| Story | Points | Assignee | Sprint |
|-------|--------|----------|--------|
| US-5.1: Sidebar | 13 | Senior Frontend Engineer | 5 |
| US-5.2: Header | 8 | Senior Frontend Engineer | 5 |
| US-5.3: Breadcrumb | 3 | Frontend Engineer | 5 |
| US-5.4: PageHeader | 3 | Frontend Engineer | 5 |
| US-5.5: MainLayout | 5 | Senior Frontend Engineer | 6 |
| US-5.6: ListViewLayout | 5 | Frontend Engineer | 6 |
| US-5.7: RecordDetailLayout | 8 | Senior Frontend Engineer | 6 |
| US-5.8: Pagination | 5 | Frontend Engineer | 6 |
| **Total** | **50** | | |

### Sprint 5-6 Dependencies
- Sprint 4: DataTable, Modal, Form components
- Sprint 3: All atomic and molecular components

### Sprint 5-6 Risks
| Risk | Mitigation |
|------|------------|
| Layout complexity | Start with existing Flask layouts as reference |
| Mobile responsiveness | Test on mobile early; use mobile-first approach |

---

## Sprint 7-8: Integration & Quick Wins (Weeks 13-16)

### Sprint Goal
Connect React components to Flask API, test with real data, and build dashboard widgets.

### User Stories

#### US-7.1: API Client Configuration
**As a** developer
**I want** a configured API client
**So that** all API calls are consistent

**Acceptance Criteria:**
- [ ] Axios instance with baseURL
- [ ] Request interceptor for auth token
- [ ] Response interceptor for error handling
- [ ] Automatic 401 redirect to login
- [ ] Request/response logging (dev only)
- [ ] Retry logic for failed requests
- [ ] Type-safe API response wrappers

**Story Points:** 5

**Tasks:**
1. Enhance `src/services/api.ts`
2. Add request interceptor
3. Add response interceptor
4. Implement retry logic
5. Create typed response wrappers
6. Add dev logging

---

#### US-7.2: React Query Configuration
**As a** developer
**I want** React Query configured
**So that** data fetching is optimized

**Acceptance Criteria:**
- [ ] QueryClient configured with defaults
- [ ] DevTools available in development
- [ ] Stale time and cache time configured
- [ ] Error boundary integration
- [ ] Optimistic updates pattern documented
- [ ] Prefetching pattern documented

**Story Points:** 3

**Tasks:**
1. Enhance `src/store/index.ts` or create query config
2. Configure QueryClient defaults
3. Add error boundary
4. Document patterns
5. Add DevTools toggle

---

#### US-7.3: Ticket API Integration
**As a** developer
**I want** ticket data fetched via React Query
**So that** the React app shows real ticket data

**Acceptance Criteria:**
- [ ] useTickets hook for list with filters
- [ ] useTicket hook for single ticket
- [ ] useCreateTicket mutation
- [ ] useUpdateTicket mutation
- [ ] Optimistic updates for status changes
- [ ] Cache invalidation on mutations
- [ ] Pagination support
- [ ] Error handling

**Story Points:** 8

**Tasks:**
1. Create `src/features/tickets/api/ticketApi.ts`
2. Create `src/features/tickets/hooks/useTickets.ts`
3. Create `src/features/tickets/hooks/useTicket.ts`
4. Create mutation hooks
5. Implement optimistic updates
6. Add pagination params
7. Add unit tests

---

#### US-7.4: Asset API Integration
**As a** developer
**I want** asset data fetched via React Query
**So that** the React app shows real asset data

**Acceptance Criteria:**
- [ ] useAssets hook for list
- [ ] useAsset hook for single asset
- [ ] useAccessories hook for list
- [ ] Filter by status, category, company
- [ ] Search functionality
- [ ] Error handling

**Story Points:** 5

**Tasks:**
1. Create `src/features/inventory/api/assetApi.ts`
2. Create asset hooks
3. Create accessory hooks
4. Implement filtering
5. Add unit tests

---

#### US-7.5: Dashboard Page
**As a** user
**I want** a React dashboard page
**So that** I can see key metrics at a glance

**Acceptance Criteria:**
- [ ] Key metric cards (tickets open, assets deployed, etc.)
- [ ] Recent tickets widget
- [ ] My assigned tickets widget
- [ ] Quick actions panel
- [ ] Responsive grid layout
- [ ] Real data from API
- [ ] Loading states
- [ ] Theme-aware styling

**Story Points:** 13

**Tasks:**
1. Create `src/pages/dashboard/DashboardPage.tsx`
2. Create metric card component
3. Create recent tickets widget
4. Create my tickets widget
5. Create quick actions panel
6. Connect to dashboard API
7. Implement responsive grid
8. Style for all themes

---

#### US-7.6: Ticket List Page (Quick Win)
**As a** user
**I want** to view tickets in the React app
**So that** I can start using the new interface

**Acceptance Criteria:**
- [ ] Ticket list with DataTable
- [ ] Status, priority filters
- [ ] Search functionality
- [ ] Sort by columns
- [ ] Click to view ticket (placeholder detail page)
- [ ] Create ticket button (placeholder)
- [ ] Real data from API
- [ ] Loading and empty states

**Story Points:** 8

**Tasks:**
1. Create `src/pages/tickets/TicketListPage.tsx`
2. Define ticket columns
3. Integrate with useTickets hook
4. Add filter toolbar
5. Implement search
6. Add row click navigation
7. Style for all themes

---

#### US-7.7: Bug Fixes & Polish
**As a** developer
**I want** to fix bugs and polish components
**So that** Phase 1 deliverables are production-ready

**Acceptance Criteria:**
- [ ] All critical bugs fixed
- [ ] Component APIs consistent
- [ ] Documentation complete in Storybook
- [ ] Accessibility audit passed
- [ ] Performance metrics met (Lighthouse > 80)
- [ ] Cross-browser testing passed

**Story Points:** 8

**Tasks:**
1. Bug triage and fixing
2. Storybook documentation review
3. Accessibility audit with aXe
4. Lighthouse audit
5. Cross-browser testing (Chrome, Firefox, Safari)
6. Performance optimization

---

#### US-7.8: Route Configuration
**As a** developer
**I want** React Router configured
**So that** navigation works correctly

**Acceptance Criteria:**
- [ ] Route definitions for all Phase 1 pages
- [ ] Nested routes for layouts
- [ ] Protected routes with auth guard
- [ ] 404 Not Found page
- [ ] Route-based code splitting
- [ ] Scroll restoration
- [ ] Route transitions (optional)

**Story Points:** 5

**Tasks:**
1. Create `src/routes/index.tsx`
2. Define route configuration
3. Implement lazy loading for routes
4. Create NotFound page
5. Add scroll restoration
6. Test all routes

---

### Sprint 7-8 Capacity (4 weeks)

| Story | Points | Assignee | Sprint |
|-------|--------|----------|--------|
| US-7.1: API Client | 5 | Senior Frontend Engineer | 7 |
| US-7.2: React Query Config | 3 | Senior Frontend Engineer | 7 |
| US-7.3: Ticket API | 8 | Senior Frontend Engineer | 7 |
| US-7.4: Asset API | 5 | Frontend Engineer | 7 |
| US-7.5: Dashboard Page | 13 | Senior Frontend Engineer | 7-8 |
| US-7.6: Ticket List Page | 8 | Frontend Engineer | 8 |
| US-7.7: Bug Fixes & Polish | 8 | All | 8 |
| US-7.8: Route Config | 5 | Frontend Engineer | 7 |
| **Total** | **55** | | |

### Sprint 7-8 Dependencies
- All previous sprints completed
- Backend API endpoints available and documented

### Sprint 7-8 Risks
| Risk | Mitigation |
|------|------------|
| API discrepancies | Coordinate with backend; use API contracts |
| Data format issues | Use TypeScript types; validate responses |

---

## Definition of Done

A user story is considered done when:

1. **Code Complete**
   - [ ] All acceptance criteria met
   - [ ] Code follows project conventions
   - [ ] TypeScript strict mode passes
   - [ ] No ESLint errors or warnings

2. **Tested**
   - [ ] Unit tests written and passing (>80% coverage)
   - [ ] Integration tests for complex flows
   - [ ] Manual testing in all three themes
   - [ ] Cross-browser tested (Chrome, Firefox, Safari)

3. **Documented**
   - [ ] Storybook story created with all variants
   - [ ] Props documented with JSDoc
   - [ ] README updated if needed

4. **Reviewed**
   - [ ] Code reviewed by at least one team member
   - [ ] Accessibility reviewed (keyboard, screen reader)

5. **Deployed**
   - [ ] Merged to develop branch
   - [ ] Deployed to staging environment
   - [ ] Smoke tested in staging

---

## Phase 1 Quality Gates

Before Phase 1 sign-off:

### Technical Quality
- [ ] All 8 sprints completed
- [ ] >80% unit test coverage
- [ ] Lighthouse Performance score >80
- [ ] No critical or high severity bugs open
- [ ] All components documented in Storybook

### Accessibility
- [ ] WCAG 2.1 AA compliance verified
- [ ] Keyboard navigation tested
- [ ] Screen reader tested (VoiceOver, NVDA)

### Performance
- [ ] Initial bundle <250KB gzipped
- [ ] Time to Interactive <3s
- [ ] No memory leaks detected

### Security
- [ ] Auth flow security reviewed
- [ ] XSS protection verified
- [ ] CSRF protection in place

### Documentation
- [ ] Component library documentation complete
- [ ] API integration patterns documented
- [ ] Developer onboarding guide created

---

## Phase 1 Deliverables Summary

| Deliverable | Sprint | Status |
|-------------|--------|--------|
| CI/CD Pipeline | 1 | Planned |
| ESLint/Prettier/Husky | 1 | Planned |
| Theme System | 1 | Planned |
| Design Tokens | 1 | Planned |
| Storybook | 1 | Planned |
| Login Page | 2 | Planned |
| JWT Token Handling | 2 | Planned |
| Auth Context | 2 | Planned |
| Protected Routes | 2 | Planned |
| Session Management | 2 | Planned |
| Button, Input, Badge | 3 | Planned |
| Icon, Spinner, Avatar | 3 | Planned |
| Tooltip, Card, Dropdown | 3 | Planned |
| FormGroup | 3 | Planned |
| DataTable | 4 | Planned |
| Modal System | 4 | Planned |
| Toast System | 4 | Planned |
| Form System | 4 | Planned |
| Advanced Select, Tabs | 4 | Planned |
| Sidebar | 5 | Planned |
| Header | 5 | Planned |
| Breadcrumb, PageHeader | 5 | Planned |
| MainLayout | 6 | Planned |
| ListViewLayout | 6 | Planned |
| RecordDetailLayout | 6 | Planned |
| Pagination | 6 | Planned |
| API Integration | 7 | Planned |
| Dashboard Page | 7-8 | Planned |
| Ticket List Page | 8 | Planned |
| Bug Fixes & Polish | 8 | Planned |

---

## Appendix A: Story Point Reference

| Points | Complexity | Example |
|--------|------------|---------|
| 1 | Trivial | Fix typo, update config |
| 2 | Simple | Add prop to existing component |
| 3 | Small | Simple component (Badge, Spinner) |
| 5 | Medium | Standard component (Card, FormGroup) |
| 8 | Large | Complex component (Dropdown, Modal) |
| 13 | Very Large | Multi-part system (DataTable, Sidebar) |
| 21 | Epic | Should be broken down |

---

## Appendix B: Component Priority Matrix

| Component | Business Value | Technical Complexity | Priority |
|-----------|---------------|---------------------|----------|
| Button | High | Low | P0 |
| Input | High | Medium | P0 |
| DataTable | Critical | High | P0 |
| Modal | High | Medium | P0 |
| Toast | Medium | Medium | P1 |
| Sidebar | High | High | P0 |
| Header | High | Medium | P0 |
| Card | High | Low | P1 |
| Dropdown | High | Medium | P1 |
| Tabs | Medium | Low | P2 |

---

## Appendix C: Technology Stack

| Category | Technology | Version |
|----------|------------|---------|
| Framework | React | 18.2.x |
| Language | TypeScript | 5.4.x |
| Build Tool | Vite | 5.1.x |
| Styling | Tailwind CSS | 3.4.x |
| State (Client) | Zustand | 4.5.x |
| State (Server) | TanStack Query | 5.28.x |
| Routing | React Router | 6.22.x |
| Forms | React Hook Form | 7.51.x |
| Validation | Zod | 3.22.x |
| UI Primitives | Headless UI | 2.1.x |
| Icons | Heroicons | 2.1.x |
| HTTP Client | Axios | 1.6.x |
| Documentation | Storybook | 7.x |

---

*This document should be reviewed and updated at the start of each sprint during sprint planning.*

**Document Approval**

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Tech Lead | | | |
| Product Owner | | | |
| Engineering Manager | | | |
