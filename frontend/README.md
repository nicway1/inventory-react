# TrueLog Inventory Frontend

Modern React-based frontend for the TrueLog Inventory Management System, built to replace the legacy Jinja templating system.

## Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **React Router 6** - Client-side routing
- **TanStack Query (React Query)** - Data fetching and caching
- **Zustand** - Lightweight state management
- **Tailwind CSS** - Utility-first styling
- **Headless UI** - Accessible component primitives
- **React Hook Form + Zod** - Form handling and validation
- **Axios** - HTTP client

## Getting Started

### Prerequisites

- Node.js 18+ (LTS recommended)
- npm or pnpm

### Installation

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Copy environment file
cp .env.example .env

# Start development server
npm run dev
```

The app will be available at `http://localhost:3000`.

### Development Commands

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build |
| `npm run lint` | Run ESLint |
| `npm run type-check` | Run TypeScript type checking |

## Project Structure

```
frontend/
├── public/                 # Static assets
├── docs/                   # Documentation
├── src/
│   ├── components/         # Reusable UI components (Atomic Design)
│   │   ├── atoms/          # Basic elements (Button, Input, Badge)
│   │   ├── molecules/      # Combinations (FormField, SearchBar)
│   │   ├── organisms/      # Complex sections (Navbar, DataTable)
│   │   └── templates/      # Page layouts (MainLayout, AuthLayout)
│   │
│   ├── pages/              # Route-based page components
│   │   ├── tickets/        # Service ticket management
│   │   ├── inventory/      # Device inventory
│   │   ├── accessories/    # Accessory management
│   │   ├── customers/      # Customer management
│   │   ├── dashboard/      # Main dashboard
│   │   ├── admin/          # Admin settings
│   │   └── auth/           # Authentication pages
│   │
│   ├── hooks/              # Custom React hooks
│   ├── services/           # API service functions
│   ├── store/              # Zustand state stores
│   ├── utils/              # Utility functions
│   ├── types/              # TypeScript type definitions
│   ├── styles/             # Global styles and Tailwind config
│   │
│   ├── App.tsx             # Root component with routes
│   └── main.tsx            # Application entry point
│
├── package.json
├── tsconfig.json
├── tailwind.config.js
├── vite.config.ts
└── .env.example
```

## Architecture Decisions

### Atomic Design

Components follow the Atomic Design methodology:
- **Atoms**: Smallest, indivisible components (buttons, inputs)
- **Molecules**: Simple groups of atoms (form fields, menu items)
- **Organisms**: Complex, self-contained sections (navigation, tables)
- **Templates**: Page-level layouts that compose organisms

### State Management

- **Server state**: TanStack Query handles all API data fetching, caching, and synchronization
- **Client state**: Zustand manages UI state (modals, sidebar) and auth state
- **Form state**: React Hook Form manages form state with Zod validation

### Styling

- Tailwind CSS with custom TrueLog theme colors
- CSS custom properties for theme values
- `cn()` utility for conditional class merging

## API Integration

The frontend communicates with the Flask backend via RESTful APIs. The Vite dev server proxies `/api` requests to the backend.

```typescript
// Example API call
import { apiClient } from '@/services/api'

const response = await apiClient.get('/tickets')
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | Backend API base URL | `/api` |
| `VITE_APP_NAME` | Application name | `TrueLog Inventory` |
| `VITE_ENABLE_DEV_TOOLS` | Enable React Query devtools | `true` |

## Contributing

1. Create a feature branch from `main`
2. Follow the existing code style and patterns
3. Write meaningful commit messages
4. Submit a pull request for review

## License

Proprietary - TrueLog Pte Ltd
