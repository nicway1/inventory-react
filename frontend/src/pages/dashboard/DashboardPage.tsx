/**
 * DashboardPage Component
 *
 * Main dashboard page matching Flask TrueLog layout with:
 * - PageLayout wrapper (Header + TabSystem)
 * - Customizable widget grid (4-6 columns on desktop)
 * - Dashboard header with refresh and customize buttons
 * - Widget cards in Salesforce style
 * - Drag-and-drop widget customization
 */

import { useCallback, useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowPathIcon, Cog6ToothIcon } from '@heroicons/react/24/outline'
import { cn } from '@/utils/cn'
import { useDashboardRefresh } from '@/hooks/useDashboard'
import { useAuthStore } from '@/store/auth.store'
import { useOpenTab } from '@/components/organisms/TabSystem'
import { useDashboardStore, selectEnabledWidgets, type WidgetConfig } from '@/store/dashboard.store'
import { PageLayout } from '@/components/templates/PageLayout'
import { DashboardCustomizer } from '@/components/organisms/DashboardCustomizer'
import { getDashboardPreferences } from '@/services/dashboard.service'
import type { WidgetSize } from '@/types/dashboard'
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

/**
 * Map widget ID to React component
 */
function renderWidget(
  widgetConfig: WidgetConfig,
  handlers: {
    onNavigateToTickets: () => void
    onNavigateToInventory: () => void
    onNavigateToCustomers: () => void
    onTicketClick: (ticketId: number) => void
    onQueueClick: (queueId: number) => void
    onQuickAction: (actionId: string) => void
  }
) {
  const { widgetId, config } = widgetConfig

  switch (widgetId) {
    case 'inventory_stats':
      return <InventoryStatsWidget onNavigate={handlers.onNavigateToInventory} />

    case 'ticket_stats':
      return (
        <TicketStatsWidget
          onNavigate={handlers.onNavigateToTickets}
          showResolved={config.show_resolved as boolean | undefined}
          timePeriod={(config.time_period as '7d' | '30d' | '90d') || '30d'}
        />
      )

    case 'customer_stats':
      return <CustomerStatsWidget onNavigate={handlers.onNavigateToCustomers} />

    case 'quick_actions':
      return <QuickActionsWidget onAction={handlers.onQuickAction} />

    case 'queue_stats':
      return <QueueStatsWidget onQueueClick={handlers.onQueueClick} />

    case 'weekly_tickets_chart':
      return <WeeklyTicketsChartWidget />

    case 'asset_status_chart':
      return <AssetStatusChartWidget />

    case 'recent_activities':
      return <RecentActivitiesWidget limit={(config.limit as number) || 5} />

    case 'recent_tickets':
      return (
        <RecentTicketsWidget
          limit={(config.limit as number) || 5}
          onTicketClick={handlers.onTicketClick}
          onViewAll={handlers.onNavigateToTickets}
        />
      )

    default:
      // Unknown widget - show placeholder
      return (
        <div className="rounded bg-white p-6 shadow-[0_2px_4px_rgba(0,0,0,0.1)] border border-[#DDDBDA] h-full flex items-center justify-center">
          <p className="text-gray-500">Widget: {widgetId}</p>
        </div>
      )
  }
}

/**
 * Get column span class based on widget size
 */
function getSizeClasses(size: WidgetSize): string {
  switch (size) {
    case 'small':
      return 'col-span-1'
    case 'medium':
      return 'col-span-1 sm:col-span-2'
    case 'large':
      return 'col-span-1 sm:col-span-2 lg:col-span-3'
    case 'full':
      return 'col-span-1 sm:col-span-2 lg:col-span-4'
    default:
      return 'col-span-1'
  }
}

export function DashboardPage() {
  const navigate = useNavigate()
  const openTab = useOpenTab()
  const { refreshAll } = useDashboardRefresh()
  const { user, isAuthenticated } = useAuthStore()
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [isCustomizerOpen, setIsCustomizerOpen] = useState(false)
  const [isLoadingPreferences, setIsLoadingPreferences] = useState(true)

  // Get enabled widgets from store
  const enabledWidgets = useDashboardStore(selectEnabledWidgets)
  const { setLayout } = useDashboardStore()

  // Load user preferences on mount
  useEffect(() => {
    const loadPreferences = async () => {
      try {
        const prefs = await getDashboardPreferences()
        // Only set layout if we got valid widgets back
        if (prefs.widgets && prefs.widgets.length > 0) {
          setLayout(prefs)
        }
      } catch (error) {
        console.error('Failed to load dashboard preferences:', error)
        // Use default layout from store
      } finally {
        setIsLoadingPreferences(false)
      }
    }

    if (isAuthenticated) {
      loadPreferences()
    } else {
      setIsLoadingPreferences(false)
    }
  }, [isAuthenticated, setLayout])

  // Handle pull-to-refresh
  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true)
    refreshAll()
    // Simulate minimum refresh time for UX
    setTimeout(() => setIsRefreshing(false), 500)
  }, [refreshAll])

  // Navigation handlers - use openTab hook which opens tab AND navigates
  const handleNavigateToTickets = useCallback(() => {
    openTab('/tickets', 'Tickets')
  }, [openTab])

  const handleNavigateToInventory = useCallback(() => {
    openTab('/inventory', 'Inventory')
  }, [openTab])

  const handleTicketClick = useCallback(
    (ticketId: number) => {
      openTab(`/tickets/${ticketId}`, `Ticket #${ticketId}`)
    },
    [openTab]
  )

  const handleNavigateToCustomers = useCallback(() => {
    openTab('/customers', 'Customers')
  }, [openTab])

  const handleQueueClick = useCallback(
    (queueId: number) => {
      openTab(`/tickets?queue=${queueId}`, `Queue #${queueId}`)
    },
    [openTab]
  )

  const handleQuickAction = useCallback(
    (actionId: string) => {
      switch (actionId) {
        case 'new-ticket':
          openTab('/tickets/new', 'New Ticket')
          break
        case 'add-asset':
          openTab('/inventory/assets/new', 'New Asset')
          break
        case 'add-customer':
          openTab('/customers', 'Customers')
          break
        case 'reports':
          openTab('/reports', 'Reports')
          break
        case 'inventory':
          openTab('/inventory', 'Inventory')
          break
        default:
          console.log('Unknown action:', actionId)
      }
    },
    [openTab]
  )

  // Open customizer
  const handleOpenCustomizer = useCallback(() => {
    setIsCustomizerOpen(true)
  }, [])

  // Close customizer
  const handleCloseCustomizer = useCallback(() => {
    setIsCustomizerOpen(false)
  }, [])

  // Handlers object for widget rendering
  const handlers = {
    onNavigateToTickets: handleNavigateToTickets,
    onNavigateToInventory: handleNavigateToInventory,
    onNavigateToCustomers: handleNavigateToCustomers,
    onTicketClick: handleTicketClick,
    onQueueClick: handleQueueClick,
    onQuickAction: handleQuickAction,
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#f3f4f6] dark:bg-gray-950">
        <div className="text-center">
          <p className="text-gray-600 dark:text-gray-400">Please log in to view the dashboard.</p>
          <button
            type="button"
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
            {/* Customize Dashboard Button */}
            <button
              type="button"
              onClick={handleOpenCustomizer}
              className={cn(
                'inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-md transition-all',
                'bg-white border border-[#dddbda] text-gray-700',
                'hover:bg-gray-50 hover:border-gray-400',
                'focus:outline-none focus:ring-2 focus:ring-[#0176d3] focus:ring-offset-2',
                'dark:bg-gray-800 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700'
              )}
            >
              <Cog6ToothIcon className="h-4 w-4" />
              Customize
            </button>

            {/* Refresh Button */}
            <button
              type="button"
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
          {isLoadingPreferences ? (
            // Loading skeleton
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
              {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
                <div
                  key={i}
                  className={cn(
                    'h-48 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse',
                    i <= 4 ? 'col-span-1' : 'col-span-1 sm:col-span-2'
                  )}
                />
              ))}
            </div>
          ) : enabledWidgets.length === 0 ? (
            // Empty state
            <div className="text-center py-12">
              <Cog6ToothIcon className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-white">
                No widgets enabled
              </h3>
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                Click the Customize button to add widgets to your dashboard.
              </p>
              <button
                type="button"
                onClick={handleOpenCustomizer}
                className="mt-4 inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-md bg-[#0176d3] text-white hover:bg-[#014486]"
              >
                <Cog6ToothIcon className="h-4 w-4" />
                Customize Dashboard
              </button>
            </div>
          ) : (
            // Widget grid
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
              {enabledWidgets.map((widgetConfig) => (
                <div key={widgetConfig.widgetId} className={getSizeClasses(widgetConfig.size)}>
                  {renderWidget(widgetConfig, handlers)}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Dashboard Customizer Modal */}
      <DashboardCustomizer isOpen={isCustomizerOpen} onClose={handleCloseCustomizer} />
    </PageLayout>
  )
}

export default DashboardPage
