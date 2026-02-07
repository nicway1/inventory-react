/**
 * Protected Route Component
 *
 * Wraps routes that require authentication.
 * Optionally checks for specific permissions.
 */

import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/store/auth.store'

/**
 * Loading spinner component
 */
function LoadingSpinner() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="flex flex-col items-center gap-4">
        {/* Spinner */}
        <div className="relative w-12 h-12">
          <div className="absolute inset-0 rounded-full border-4 border-gray-200 dark:border-gray-700" />
          <div className="absolute inset-0 rounded-full border-4 border-primary-500 border-t-transparent animate-spin" />
        </div>
        {/* Loading text */}
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Loading...
        </p>
      </div>
    </div>
  )
}

/**
 * Access denied component
 */
function AccessDenied() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="max-w-md w-full mx-4">
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8 text-center">
          {/* Icon */}
          <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-danger-100 dark:bg-danger-900/30 flex items-center justify-center">
            <svg
              className="w-8 h-8 text-danger-600 dark:text-danger-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </div>

          {/* Title */}
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            Access Denied
          </h1>

          {/* Message */}
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            You do not have permission to access this page.
            Please contact your administrator if you believe this is an error.
          </p>

          {/* Back button */}
          <button
            onClick={() => window.history.back()}
            className="btn-primary"
          >
            Go Back
          </button>
        </div>
      </div>
    </div>
  )
}

/**
 * Props for ProtectedRoute
 */
interface ProtectedRouteProps {
  /** Child components to render if authenticated */
  children: React.ReactNode
  /** Required permissions (optional) */
  permissions?: string[]
  /** Whether all permissions are required (default: false - any permission) */
  requireAll?: boolean
  /** Allowed user types (optional) */
  allowedUserTypes?: Array<'ADMIN' | 'TECHNICIAN' | 'CLIENT'>
  /** Custom redirect path (default: /login) */
  redirectTo?: string
  /** Show access denied page instead of redirecting (for permission failures) */
  showAccessDenied?: boolean
}

/**
 * ProtectedRoute component
 *
 * Wraps routes that require authentication and optionally specific permissions.
 *
 * @example
 * // Basic protection - just requires authentication
 * <ProtectedRoute>
 *   <Dashboard />
 * </ProtectedRoute>
 *
 * @example
 * // With permission check
 * <ProtectedRoute permissions={['admin.users.view']}>
 *   <AdminUsers />
 * </ProtectedRoute>
 *
 * @example
 * // With user type restriction
 * <ProtectedRoute allowedUserTypes={['ADMIN', 'TECHNICIAN']}>
 *   <TechnicianDashboard />
 * </ProtectedRoute>
 */
export function ProtectedRoute({
  children,
  permissions = [],
  requireAll = false,
  allowedUserTypes,
  redirectTo = '/login',
  showAccessDenied = true,
}: ProtectedRouteProps) {
  const location = useLocation()
  const { user, isAuthenticated, isLoading, hasPermission, hasAnyPermission, hasAllPermissions } =
    useAuthStore()

  // Show loading state while checking auth
  if (isLoading) {
    return <LoadingSpinner />
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated || !user) {
    // Save the current location for redirect after login
    return <Navigate to={redirectTo} state={{ from: location }} replace />
  }

  // Check user type if specified
  if (allowedUserTypes && allowedUserTypes.length > 0) {
    if (!allowedUserTypes.includes(user.user_type)) {
      if (showAccessDenied) {
        return <AccessDenied />
      }
      return <Navigate to="/dashboard" replace />
    }
  }

  // Check permissions if specified
  if (permissions.length > 0) {
    const hasAccess = requireAll
      ? hasAllPermissions(permissions)
      : hasAnyPermission(permissions)

    if (!hasAccess) {
      if (showAccessDenied) {
        return <AccessDenied />
      }
      return <Navigate to="/dashboard" replace />
    }
  }

  // User is authenticated and has required permissions
  return <>{children}</>
}

export default ProtectedRoute
