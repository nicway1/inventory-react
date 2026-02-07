/**
 * HistoryPage Component
 *
 * Full activity log/audit log page with:
 * - Pagination
 * - Filter by date range
 * - Filter by action type (create, update, delete)
 * - Filter by entity type (ticket, asset, customer, user)
 * - Filter by user
 * - Search by content
 * - Export functionality
 */

import { useState, useEffect, useCallback } from 'react'
import {
  ClockIcon,
  ArrowPathIcon,
  ArrowDownTrayIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  DocumentArrowDownIcon,
  TableCellsIcon,
  QueueListIcon,
} from '@heroicons/react/24/outline'
import { PageLayout } from '@/components/templates/PageLayout'
import { Button } from '@/components/atoms/Button'
import { Card, CardHeader } from '@/components/molecules/Card'
import { Spinner } from '@/components/atoms/Spinner'
import { ActivityItem } from '@/components/molecules/ActivityItem'
import { ActivityTimeline } from '@/components/molecules/ActivityTimeline'
import { ActivityFilterPanel } from '@/components/molecules/ActivityFilterPanel'
import { cn } from '@/utils/cn'
import {
  getActivities,
  getActivityUsers,
  exportActivities,
  downloadExportFile,
} from '@/services/history.service'
import type { Activity, ActivityFilters, ActivityListParams } from '@/types/history'

/**
 * View mode for the activity list
 */
type ViewMode = 'list' | 'timeline'

/**
 * Pagination state
 */
interface PaginationState {
  page: number
  perPage: number
  total: number
  totalPages: number
}

export function HistoryPage() {
  // State
  const [activities, setActivities] = useState<Activity[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFilters] = useState<ActivityFilters>({})
  const [pagination, setPagination] = useState<PaginationState>({
    page: 1,
    perPage: 25,
    total: 0,
    totalPages: 0,
  })
  const [users, setUsers] = useState<{ id: number; name: string }[]>([])
  const [viewMode, setViewMode] = useState<ViewMode>('list')
  const [isExporting, setIsExporting] = useState(false)

  // Fetch activities
  const fetchActivities = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      const params: ActivityListParams = {
        page: pagination.page,
        per_page: pagination.perPage,
        sort: 'created_at',
        order: 'desc',
        ...filters,
      }

      const response = await getActivities(params)

      setActivities(response.data)
      setPagination((prev) => ({
        ...prev,
        total: response.meta.pagination.total,
        totalPages: response.meta.pagination.total_pages,
      }))
    } catch (err: unknown) {
      console.error('Error fetching activities:', err)
      setError((err as Error).message || 'Failed to load activity history')

      // Show mock data in development if API fails
      if (import.meta.env.DEV) {
        setActivities(generateMockActivities())
        setPagination((prev) => ({ ...prev, total: 100, totalPages: 4 }))
      }
    } finally {
      setIsLoading(false)
    }
  }, [pagination.page, pagination.perPage, filters])

  // Fetch users for filter dropdown
  const fetchUsers = useCallback(async () => {
    try {
      const userData = await getActivityUsers()
      setUsers(userData)
    } catch (err) {
      console.error('Error fetching users:', err)
    }
  }, [])

  // Initial load
  useEffect(() => {
    fetchUsers()
  }, [fetchUsers])

  // Fetch activities when filters or pagination change
  useEffect(() => {
    fetchActivities()
  }, [fetchActivities])

  // Handle filter changes
  const handleFiltersChange = (newFilters: ActivityFilters) => {
    setFilters(newFilters)
    setPagination((prev) => ({ ...prev, page: 1 })) // Reset to first page
  }

  // Handle page change
  const handlePageChange = (newPage: number) => {
    setPagination((prev) => ({ ...prev, page: newPage }))
  }

  // Handle refresh
  const handleRefresh = () => {
    fetchActivities()
  }

  // Handle export
  const handleExport = async (format: 'csv' | 'xlsx' | 'json') => {
    setIsExporting(true)

    try {
      const blob = await exportActivities({
        format,
        filters,
      })

      const filename = `activity_log_${new Date().toISOString().split('T')[0]}.${format}`
      downloadExportFile(blob, filename)
    } catch (err) {
      console.error('Error exporting activities:', err)
      alert('Failed to export activity log. Please try again.')
    } finally {
      setIsExporting(false)
    }
  }

  // Generate mock activities for development
  function generateMockActivities(): Activity[] {
    const types = [
      'ticket_created',
      'ticket_updated',
      'asset_created',
      'asset_updated',
      'customer_created',
      'admin_user_created',
      'admin_company_updated',
    ]
    const userNames = ['John Admin', 'Jane Tech', 'Bob Supervisor', 'Alice Developer']

    return Array.from({ length: 25 }, (_, i) => ({
      id: i + 1,
      user_id: (i % 4) + 1,
      user_name: userNames[i % 4],
      type: types[i % types.length],
      content: `Sample activity content ${i + 1} - ${types[i % types.length].replace(/_/g, ' ')}`,
      reference_id: i + 100,
      is_read: i % 3 !== 0,
      created_at: new Date(Date.now() - i * 3600000).toISOString(),
      updated_at: new Date(Date.now() - i * 3600000).toISOString(),
    }))
  }

  // Pagination info
  const startItem = (pagination.page - 1) * pagination.perPage + 1
  const endItem = Math.min(pagination.page * pagination.perPage, pagination.total)

  return (
    <PageLayout
      title="Activity History"
      subtitle="View and search the complete audit log of system activities"
      breadcrumbs={[{ label: 'Admin' }, { label: 'History' }]}
      actions={
        <div className="flex items-center gap-2">
          {/* View mode toggle */}
          <div className="flex items-center rounded-lg border border-gray-300 dark:border-gray-600 overflow-hidden">
            <button
              onClick={() => setViewMode('list')}
              className={cn(
                'p-2 transition-colors',
                viewMode === 'list'
                  ? 'bg-blue-500 text-white'
                  : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
              )}
              title="List view"
            >
              <TableCellsIcon className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('timeline')}
              className={cn(
                'p-2 transition-colors',
                viewMode === 'timeline'
                  ? 'bg-blue-500 text-white'
                  : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
              )}
              title="Timeline view"
            >
              <QueueListIcon className="w-4 h-4" />
            </button>
          </div>

          {/* Export dropdown */}
          <div className="relative group">
            <Button
              variant="secondary"
              leftIcon={<ArrowDownTrayIcon className="w-4 h-4" />}
              disabled={isExporting || activities.length === 0}
            >
              {isExporting ? 'Exporting...' : 'Export'}
            </Button>
            <div className="absolute right-0 mt-1 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-20">
              <div className="py-1">
                <button
                  onClick={() => handleExport('csv')}
                  className="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                  Export as CSV
                </button>
                <button
                  onClick={() => handleExport('xlsx')}
                  className="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                  Export as Excel
                </button>
                <button
                  onClick={() => handleExport('json')}
                  className="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                  Export as JSON
                </button>
              </div>
            </div>
          </div>

          {/* Refresh button */}
          <Button
            variant="secondary"
            leftIcon={<ArrowPathIcon className={cn('w-4 h-4', isLoading && 'animate-spin')} />}
            onClick={handleRefresh}
            disabled={isLoading}
          >
            Refresh
          </Button>
        </div>
      }
    >
      <div className="space-y-6">
        {/* Filter Panel */}
        <ActivityFilterPanel
          filters={filters}
          onFiltersChange={handleFiltersChange}
          users={users}
          isLoading={isLoading}
        />

        {/* Activities Card */}
        <Card padding="none">
          {/* Card Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30">
                <ClockIcon className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Activity Log
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {pagination.total > 0
                    ? `Showing ${startItem}-${endItem} of ${pagination.total} activities`
                    : 'No activities found'}
                </p>
              </div>
            </div>
          </div>

          {/* Content */}
          <div className="p-6">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Spinner size="lg" label="Loading activities..." />
              </div>
            ) : error ? (
              <div className="text-center py-12">
                <div className="w-16 h-16 mx-auto rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center mb-4">
                  <ClockIcon className="w-8 h-8 text-red-500 dark:text-red-400" />
                </div>
                <p className="text-red-600 dark:text-red-400 font-medium">{error}</p>
                <Button variant="secondary" className="mt-4" onClick={handleRefresh}>
                  Try Again
                </Button>
              </div>
            ) : activities.length === 0 ? (
              <div className="text-center py-12">
                <ClockIcon className="w-16 h-16 mx-auto text-gray-300 dark:text-gray-600 mb-4" />
                <p className="text-gray-500 dark:text-gray-400">
                  No activities found matching your filters
                </p>
              </div>
            ) : viewMode === 'timeline' ? (
              <ActivityTimeline
                activities={activities}
                showUser={true}
                showEntity={true}
                groupByDate={true}
                maxHeight="600px"
              />
            ) : (
              <div className="space-y-3">
                {activities.map((activity) => (
                  <ActivityItem
                    key={activity.id}
                    activity={activity}
                    showUser={true}
                    showEntity={true}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Pagination Footer */}
          {pagination.totalPages > 1 && (
            <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
              {/* Page info */}
              <div className="text-sm text-gray-500 dark:text-gray-400">
                Page {pagination.page} of {pagination.totalPages}
              </div>

              {/* Pagination controls */}
              <div className="flex items-center gap-2">
                {/* First page */}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handlePageChange(1)}
                  disabled={pagination.page <= 1}
                >
                  First
                </Button>

                {/* Previous page */}
                <Button
                  variant="ghost"
                  size="sm"
                  leftIcon={<ChevronLeftIcon className="w-4 h-4" />}
                  onClick={() => handlePageChange(pagination.page - 1)}
                  disabled={pagination.page <= 1}
                >
                  Previous
                </Button>

                {/* Page numbers */}
                <div className="flex items-center gap-1">
                  {Array.from({ length: Math.min(5, pagination.totalPages) }, (_, i) => {
                    let pageNum: number
                    if (pagination.totalPages <= 5) {
                      pageNum = i + 1
                    } else if (pagination.page <= 3) {
                      pageNum = i + 1
                    } else if (pagination.page >= pagination.totalPages - 2) {
                      pageNum = pagination.totalPages - 4 + i
                    } else {
                      pageNum = pagination.page - 2 + i
                    }

                    return (
                      <button
                        key={pageNum}
                        onClick={() => handlePageChange(pageNum)}
                        className={cn(
                          'w-8 h-8 rounded-lg text-sm font-medium transition-colors',
                          pagination.page === pageNum
                            ? 'bg-blue-500 text-white'
                            : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                        )}
                      >
                        {pageNum}
                      </button>
                    )
                  })}
                </div>

                {/* Next page */}
                <Button
                  variant="ghost"
                  size="sm"
                  rightIcon={<ChevronRightIcon className="w-4 h-4" />}
                  onClick={() => handlePageChange(pagination.page + 1)}
                  disabled={pagination.page >= pagination.totalPages}
                >
                  Next
                </Button>

                {/* Last page */}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handlePageChange(pagination.totalPages)}
                  disabled={pagination.page >= pagination.totalPages}
                >
                  Last
                </Button>
              </div>

              {/* Per page selector */}
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-500 dark:text-gray-400">Per page:</span>
                <select
                  value={pagination.perPage}
                  onChange={(e) =>
                    setPagination((prev) => ({
                      ...prev,
                      perPage: Number(e.target.value),
                      page: 1,
                    }))
                  }
                  className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white px-2 py-1 text-sm"
                >
                  <option value={10}>10</option>
                  <option value={25}>25</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                </select>
              </div>
            </div>
          )}
        </Card>
      </div>
    </PageLayout>
  )
}

export default HistoryPage
