import { Routes, Route } from 'react-router-dom'
import { LoginPage } from '@/pages/auth'
import { DashboardPage } from '@/pages/dashboard'
import { ProtectedRoute } from '@/components/atoms'
import { PageLayout, ContentLayout } from '@/components/templates/PageLayout'

function Tickets() {
  return (
    <PageLayout
      title="Tickets"
      subtitle="Manage repair and service tickets"
      breadcrumbs={[{ label: 'Tickets' }]}
      actions={
        <button className="sf-btn sf-btn-brand">
          New Ticket
        </button>
      }
    >
      <div className="card">
        <div className="card-body">
          <p className="text-gray-600 dark:text-gray-400">
            Tickets list coming soon...
          </p>
        </div>
      </div>
    </PageLayout>
  )
}

function Inventory() {
  return (
    <PageLayout
      title="Inventory"
      subtitle="Track and manage device inventory"
      breadcrumbs={[{ label: 'Inventory' }]}
      actions={
        <button className="sf-btn sf-btn-brand">
          Add Device
        </button>
      }
    >
      <div className="card">
        <div className="card-body">
          <p className="text-gray-600 dark:text-gray-400">
            Inventory list coming soon...
          </p>
        </div>
      </div>
    </PageLayout>
  )
}

function Accessories() {
  return (
    <PageLayout
      title="Accessories"
      subtitle="Manage accessories and components"
      breadcrumbs={[{ label: 'Accessories' }]}
      actions={
        <button className="sf-btn sf-btn-brand">
          Add Accessory
        </button>
      }
    >
      <div className="card">
        <div className="card-body">
          <p className="text-gray-600 dark:text-gray-400">
            Accessories list coming soon...
          </p>
        </div>
      </div>
    </PageLayout>
  )
}

function Customers() {
  return (
    <PageLayout
      title="Customers"
      subtitle="Manage customer accounts and contacts"
      breadcrumbs={[{ label: 'Customers' }]}
      actions={
        <button className="sf-btn sf-btn-brand">
          Add Customer
        </button>
      }
    >
      <div className="card">
        <div className="card-body">
          <p className="text-gray-600 dark:text-gray-400">
            Customers list coming soon...
          </p>
        </div>
      </div>
    </PageLayout>
  )
}

function Reports() {
  return (
    <PageLayout
      title="Reports"
      subtitle="View analytics and generate reports"
      breadcrumbs={[{ label: 'Reports' }]}
    >
      <div className="card">
        <div className="card-body">
          <p className="text-gray-600 dark:text-gray-400">
            Reports coming soon...
          </p>
        </div>
      </div>
    </PageLayout>
  )
}

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
      <Route
        path="/tickets/*"
        element={
          <ProtectedRoute>
            <Tickets />
          </ProtectedRoute>
        }
      />
      <Route
        path="/inventory/*"
        element={
          <ProtectedRoute>
            <Inventory />
          </ProtectedRoute>
        }
      />
      <Route
        path="/accessories/*"
        element={
          <ProtectedRoute>
            <Accessories />
          </ProtectedRoute>
        }
      />
      <Route
        path="/customers/*"
        element={
          <ProtectedRoute>
            <Customers />
          </ProtectedRoute>
        }
      />
      <Route
        path="/reports/*"
        element={
          <ProtectedRoute>
            <Reports />
          </ProtectedRoute>
        }
      />
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
