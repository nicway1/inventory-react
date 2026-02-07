/**
 * DashboardPage Component
 *
 * Main dashboard page with responsive grid layout for widgets.
 * Supports pull-to-refresh and loading states.
 */

import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { cn } from '@/utils/cn'
import { useDashboardRefresh } from '@/hooks/useDashboard'
import { useAuthStore } from '@/store/auth.store'
import {
  TicketStatsWidget,
  InventoryStatsWidget,
  RecentTicketsWidget,
  QuickActionsWidget,
  StatsCard,
} from '@/components/organisms/widgets'

export function DashboardPage() {
  const navigate = useNavigate()
  const { refreshAll } = useDashboardRefresh()
  const { user, isAuthenticated } = useAuthStore()
  const [isRefreshing, setIsRefreshing] = useState(false)

  // Handle pull-to-refresh
  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true)
    refreshAll()
    // Simulate minimum refresh time for UX
    setTimeout(() => setIsRefreshing(false), 500)
  }, [refreshAll])

  // Navigation handlers
  const handleNavigateToTickets = useCallback(() => {
    navigate('/tickets')
  }, [navigate])

  const handleNavigateToInventory = useCallback(() => {
    navigate('/inventory')
  }, [navigate])

  const handleTicketClick = useCallback(
    (ticketId: number) => {
      navigate(`/tickets/${ticketId}`)
    },
    [navigate]
  )

  const handleQuickAction = useCallback(
    (actionId: string) => {
      switch (actionId) {
        case 'create-ticket':
          navigate('/tickets/new')
          break
        case 'create-asset':
          navigate('/inventory/new')
          break
        case 'scan-qr':
          // TODO: Open QR scanner modal
          console.log('Scan QR action')
          break
        case 'search':
          // TODO: Open search modal or navigate to search
          navigate('/search')
          break
        default:
          console.log('Unknown action:', actionId)
      }
    },
    [navigate]
  )

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600">Please log in to view the dashboard.</p>
          <button
            onClick={() => navigate('/login')}
            className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
          >
            Go to Login
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-white border-b border-gray-200">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold text-gray-900">Dashboard</h1>
              {user && (
                <p className="text-sm text-gray-500">
                  Welcome back, {user.first_name || user.username}
                </p>
              )}
            </div>
            <button
              onClick={handleRefresh}
              disabled={isRefreshing}
              className={cn(
                'inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors',
                'bg-white border border-gray-300 text-gray-700',
                'hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              <svg
                className={cn('h-4 w-4', isRefreshing && 'animate-spin')}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
              {isRefreshing ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        {/* Responsive grid layout */}
        {/* Mobile: 1 column, Tablet: 2 columns, Desktop: 3-4 columns */}
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {/* Quick Actions - spans 1 column */}
          <div className="sm:col-span-1">
            <QuickActionsWidget onAction={handleQuickAction} />
          </div>

          {/* Ticket Stats - spans 1 column */}
          <div className="sm:col-span-1">
            <TicketStatsWidget
              onNavigate={handleNavigateToTickets}
              showResolved={true}
              timePeriod="30d"
            />
          </div>

          {/* Inventory Stats - spans 1 column */}
          <div className="sm:col-span-1">
            <InventoryStatsWidget onNavigate={handleNavigateToInventory} />
          </div>

          {/* Customer Stats Card - spans 1 column */}
          <div className="sm:col-span-1">
            <StatsCard
              label="Customers"
              value="--"
              icon="users"
              variant="blue"
              onClick={() => navigate('/customers')}
              subtitle="Click to view all customers"
            />
          </div>

          {/* Recent Tickets - spans 2 columns on tablet+, full width on mobile */}
          <div className="sm:col-span-2 lg:col-span-2 xl:col-span-2">
            <RecentTicketsWidget
              limit={5}
              onTicketClick={handleTicketClick}
              onViewAll={handleNavigateToTickets}
            />
          </div>

          {/* Additional Stats Cards */}
          <div className="sm:col-span-1">
            <StatsCard
              label="Accessories"
              value="--"
              variant="orange"
              onClick={() => navigate('/accessories')}
              customIcon={
                <svg
                  className="h-6 w-6"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"
                  />
                </svg>
              }
            />
          </div>

          <div className="sm:col-span-1">
            <StatsCard
              label="Active Shipments"
              value="--"
              variant="cyan"
              customIcon={
                <svg
                  className="h-6 w-6"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"
                  />
                </svg>
              }
            />
          </div>
        </div>
      </main>
    </div>
  )
}

export default DashboardPage
