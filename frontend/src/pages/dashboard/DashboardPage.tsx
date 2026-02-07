/**
 * DashboardPage Component
 *
 * Main dashboard page matching Flask TrueLog layout with:
 * - PageLayout wrapper (Header + TabSystem)
 * - Responsive widget grid (4-6 columns on desktop)
 * - Dashboard header with refresh button
 * - Widget cards in Salesforce style
 */

import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowPathIcon } from '@heroicons/react/24/outline'
import { cn } from '@/utils/cn'
import { useDashboardRefresh } from '@/hooks/useDashboard'
import { useAuthStore } from '@/store/auth.store'
import { PageLayout } from '@/components/templates/PageLayout'
import {
  TicketStatsWidget,
  InventoryStatsWidget,
  CustomerStatsWidget,
  QueueStatsWidget,
  WeeklyTicketsChartWidget,
  AssetStatusChartWidget,
  RecentActivitiesWidget,
  RecentTicketsWidget,
  QuickActionsWidget,
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

  const handleNavigateToCustomers = useCallback(() => {
    navigate('/customers')
  }, [navigate])

  const handleQueueClick = useCallback(
    (queueId: number) => {
      navigate(`/tickets?queue=${queueId}`)
    },
    [navigate]
  )

  const handleQuickAction = useCallback(
    (actionId: string) => {
      switch (actionId) {
        case 'new-ticket':
          navigate('/tickets/new')
          break
        case 'add-asset':
          navigate('/inventory/new')
          break
        case 'add-customer':
          navigate('/customers/new')
          break
        case 'reports':
          navigate('/reports')
          break
        case 'inventory':
          navigate('/inventory')
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
      <div className="flex min-h-screen items-center justify-center bg-[#f3f4f6] dark:bg-gray-950">
        <div className="text-center">
          <p className="text-gray-600 dark:text-gray-400">Please log in to view the dashboard.</p>
          <button
            onClick={() => navigate('/login')}
            className="mt-4 rounded-lg bg-[#0176d3] px-4 py-2 text-white hover:bg-[#014486]"
          >
            Go to Login
          </button>
        </div>
      </div>
    )
  }

  return (
    <PageLayout>
      {/* Dashboard Content Area - Salesforce Style */}
      <div className="sf-dashboard min-h-full">
        {/* Dashboard Header Bar */}
        <div className="bg-white dark:bg-gray-900 border-b border-[#dddbda] dark:border-gray-700 px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
            {user && (
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                Welcome back, {user.first_name || user.username}
              </p>
            )}
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleRefresh}
              disabled={isRefreshing}
              className={cn(
                'inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-md transition-all',
                'bg-white border border-[#dddbda] text-gray-700',
                'hover:bg-gray-50 hover:border-gray-400',
                'focus:outline-none focus:ring-2 focus:ring-[#0176d3] focus:ring-offset-2',
                'disabled:opacity-50 disabled:cursor-not-allowed',
                'dark:bg-gray-800 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700'
              )}
            >
              <ArrowPathIcon className={cn('h-4 w-4', isRefreshing && 'animate-spin')} />
              {isRefreshing ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>
        </div>

        {/* Widget Grid - Responsive Salesforce-style layout */}
        <div className="p-6">
          {/*
            Grid system matching Flask TrueLog:
            - 4 columns on desktop
            - 2 columns on tablets
            - 1 column on mobile

            Widget sizes:
            - widget-small: 1 column
            - widget-medium: 2 columns
            - widget-large: 3 columns
            - widget-full: 4 columns (full width)
          */}
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {/* Row 1: Stats Widgets (small - 1 column each) */}

            {/* Inventory Stats - Purple */}
            <div className="col-span-1">
              <InventoryStatsWidget onNavigate={handleNavigateToInventory} />
            </div>

            {/* Ticket Stats - Green */}
            <div className="col-span-1">
              <TicketStatsWidget
                onNavigate={handleNavigateToTickets}
                showResolved={true}
                timePeriod="30d"
              />
            </div>

            {/* Customer Stats - Blue */}
            <div className="col-span-1">
              <CustomerStatsWidget onNavigate={handleNavigateToCustomers} />
            </div>

            {/* Quick Actions - Small */}
            <div className="col-span-1">
              <QuickActionsWidget onAction={handleQuickAction} />
            </div>

            {/* Row 2: Medium Widgets (2 columns each) */}

            {/* Queue Stats - Orange - Medium (2 columns) */}
            <div className="col-span-1 sm:col-span-2">
              <QueueStatsWidget onQueueClick={handleQueueClick} />
            </div>

            {/* Weekly Tickets Chart - Medium (2 columns) */}
            <div className="col-span-1 sm:col-span-2">
              <WeeklyTicketsChartWidget />
            </div>

            {/* Row 3: Charts and Activities */}

            {/* Asset Status Chart - Medium (2 columns) */}
            <div className="col-span-1 sm:col-span-2">
              <AssetStatusChartWidget />
            </div>

            {/* Recent Activities - Medium (2 columns) */}
            <div className="col-span-1 sm:col-span-2">
              <RecentActivitiesWidget limit={5} />
            </div>

            {/* Row 4: Recent Tickets - Full Width (4 columns) */}
            <div className="col-span-1 sm:col-span-2 lg:col-span-4">
              <RecentTicketsWidget
                limit={5}
                onTicketClick={handleTicketClick}
                onViewAll={handleNavigateToTickets}
              />
            </div>
          </div>
        </div>
      </div>
    </PageLayout>
  )
}

export default DashboardPage
