import { Routes, Route } from 'react-router-dom'
import { LoginPage } from '@/pages/auth'
import { DashboardPage } from '@/pages/dashboard'
import { TicketListPage, TicketCreate, TicketDetailPage, TicketEdit } from '@/pages/tickets'
import { InventoryList, AssetCreate, AssetDetail, AssetEdit, AccessoryDetail } from '@/pages/inventory'
import { CustomerListPage, CustomerDetailPage } from '@/pages/customers'
import { ReportsPage, GenerateReportPage } from '@/pages/reports'
import { NotificationsPage } from '@/pages/notifications/NotificationsPage'
import { ProfilePage } from '@/pages/profile'
import { SettingsPage } from '@/pages/settings'
import { HistoryPage } from '@/pages/history'
import { ProtectedRoute } from '@/components/atoms'
import { PageLayout, ContentLayout } from '@/components/templates/PageLayout'

function Admin() {
  return (
    <PageLayout
      title="Admin"
      subtitle="System administration and settings"
      breadcrumbs={[{ label: 'Admin' }]}
    >
      <div className="card">
        <div className="card-body">
          <p className="text-gray-600 dark:text-gray-400">
            Admin settings coming soon...
          </p>
        </div>
      </div>
    </PageLayout>
  )
}

function NotFound() {
  return (
    <ContentLayout className="flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-gray-300 dark:text-gray-700">404</h1>
        <p className="text-xl text-gray-600 dark:text-gray-400 mt-4">
          Page not found
        </p>
        <a href="/" className="sf-btn sf-btn-brand mt-6 inline-flex">
          Go Home
        </a>
      </div>
    </ContentLayout>
  )
}

function App() {
  return (
    <Routes>
      {/* Auth Routes (Public) */}
      <Route path="/login" element={<LoginPage />} />

      {/* Protected Application Routes */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />

      {/* Ticket Routes */}
      <Route
        path="/tickets"
        element={
          <ProtectedRoute>
            <TicketListPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/tickets/new"
        element={
          <ProtectedRoute>
            <TicketCreate />
          </ProtectedRoute>
        }
      />
      <Route
        path="/tickets/:id"
        element={
          <ProtectedRoute>
            <TicketDetailPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/tickets/:id/edit"
        element={
          <ProtectedRoute>
            <TicketEdit />
          </ProtectedRoute>
        }
      />

      {/* Inventory Routes */}
      <Route
        path="/inventory"
        element={
          <ProtectedRoute>
            <InventoryList />
          </ProtectedRoute>
        }
      />
      <Route
        path="/inventory/assets/new"
        element={
          <ProtectedRoute>
            <AssetCreate />
          </ProtectedRoute>
        }
      />
      <Route
        path="/inventory/assets/:id"
        element={
          <ProtectedRoute>
            <AssetDetail />
          </ProtectedRoute>
        }
      />
      <Route
        path="/inventory/assets/:id/edit"
        element={
          <ProtectedRoute>
            <AssetEdit />
          </ProtectedRoute>
        }
      />
      <Route
        path="/inventory/accessories/:id"
        element={
          <ProtectedRoute>
            <AccessoryDetail />
          </ProtectedRoute>
        }
      />

      {/* Customer Routes */}
      <Route
        path="/customers"
        element={
          <ProtectedRoute>
            <CustomerListPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/customers/:id"
        element={
          <ProtectedRoute>
            <CustomerDetailPage />
          </ProtectedRoute>
        }
      />

      {/* Reports Routes */}
      <Route
        path="/reports"
        element={
          <ProtectedRoute>
            <ReportsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/reports/generate/:templateId"
        element={
          <ProtectedRoute>
            <GenerateReportPage />
          </ProtectedRoute>
        }
      />

      {/* Notifications Route */}
      <Route
        path="/notifications"
        element={
          <ProtectedRoute>
            <NotificationsPage />
          </ProtectedRoute>
        }
      />

      {/* Profile & Settings Routes */}
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <ProfilePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <SettingsPage />
          </ProtectedRoute>
        }
      />

      {/* History/Audit Log (requires admin role) */}
      <Route
        path="/history"
        element={
          <ProtectedRoute allowedUserTypes={['SUPER_ADMIN', 'DEVELOPER']}>
            <HistoryPage />
          </ProtectedRoute>
        }
      />

      {/* Admin (requires admin role) */}
      <Route
        path="/admin/*"
        element={
          <ProtectedRoute allowedUserTypes={['ADMIN']}>
            <Admin />
          </ProtectedRoute>
        }
      />

      {/* 404 */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}

export default App
