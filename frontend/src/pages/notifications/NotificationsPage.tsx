/**
 * NotificationsPage Component
 *
 * Full notifications list page with filtering and bulk actions.
 * Features:
 * - Filter by type (all, mentions, tickets, assets, system)
 * - Filter by read status
 * - Search notifications
 * - Mark as read/unread
 * - Bulk actions (mark all read, delete all read)
 * - Infinite scroll / load more
 */

import { useEffect, useState, useCallback, useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  BellIcon,
  FunnelIcon,
  MagnifyingGlassIcon,
  CheckIcon,
  TrashIcon,
  ArrowPathIcon,
  XMarkIcon,
  ChevronDownIcon,
} from '@heroicons/react/24/outline'
import { useNotificationsStore } from '@/store/notifications.store'
import { NotificationItem } from '@/components/molecules/NotificationItem'
import type { NotificationType } from '@/services/notifications.service'
import { cn } from '@/utils/cn'

// Filter options for notification types
const typeFilters: { value: NotificationType | 'all'; label: string }[] = [
  { value: 'all', label: 'All Notifications' },
  { value: 'mention', label: 'Mentions' },
  { value: 'group_mention', label: 'Group Mentions' },
  { value: 'ticket_assigned', label: 'Ticket Assigned' },
  { value: 'ticket_updated', label: 'Ticket Updates' },
  { value: 'asset_checkout', label: 'Asset Checkout' },
  { value: 'asset_checkin', label: 'Asset Check-in' },
  { value: 'system', label: 'System Alerts' },
]

// Filter options for read status
const readFilters: { value: 'all' | 'unread' | 'read'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'unread', label: 'Unread' },
  { value: 'read', label: 'Read' },
]

export function NotificationsPage() {
  const {
    notifications,
    unreadCount,
    totalItems,
    isLoading,
    isLoadingMore,
    hasNext,
    error,
    typeFilter,
    readFilter,
    searchQuery,
    fetchNotifications,
    fetchMore,
    refreshNotifications,
    markAsRead,
    markAsUnread,
    markAllAsRead,
    deleteNotification,
    deleteAllRead,
    setTypeFilter,
    setReadFilter,
    setSearchQuery,
    clearFilters,
  } = useNotificationsStore()

  // Local state for UI
  const [showFilters, setShowFilters] = useState(false)
  const [searchInput, setSearchInput] = useState('')
  const [isDeleting, setIsDeleting] = useState(false)

  // Fetch notifications on mount
  useEffect(() => {
    fetchNotifications()
  }, [fetchNotifications])

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      if (searchInput !== searchQuery) {
        setSearchQuery(searchInput)
        fetchNotifications({ search: searchInput })
      }
    }, 300)

    return () => clearTimeout(timer)
  }, [searchInput, searchQuery, setSearchQuery, fetchNotifications])

  // Handle type filter change
  const handleTypeFilterChange = useCallback(
    (value: string) => {
      const type = value === 'all' ? null : (value as NotificationType)
      setTypeFilter(type)
    },
    [setTypeFilter]
  )

  // Handle read filter change
  const handleReadFilterChange = useCallback(
    (value: string) => {
      const isRead = value === 'all' ? null : value === 'read'
      setReadFilter(isRead)
    },
    [setReadFilter]
  )

  // Handle mark all as read
  const handleMarkAllAsRead = useCallback(async () => {
    try {
      await markAllAsRead()
    } catch (error) {
      console.error('Failed to mark all as read:', error)
    }
  }, [markAllAsRead])

  // Handle delete all read
  const handleDeleteAllRead = useCallback(async () => {
    if (!window.confirm('Are you sure you want to delete all read notifications?')) {
      return
    }

    setIsDeleting(true)
    try {
      await deleteAllRead()
    } catch (error) {
      console.error('Failed to delete read notifications:', error)
    } finally {
      setIsDeleting(false)
    }
  }, [deleteAllRead])

  // Handle refresh
  const handleRefresh = useCallback(() => {
    refreshNotifications()
  }, [refreshNotifications])

  // Handle load more
  const handleLoadMore = useCallback(() => {
    if (!isLoadingMore && hasNext) {
      fetchMore()
    }
  }, [isLoadingMore, hasNext, fetchMore])

  // Check if any filters are active
  const hasActiveFilters = useMemo(
    () => typeFilter !== null || readFilter !== null || searchQuery !== '',
    [typeFilter, readFilter, searchQuery]
  )

  // Count of read notifications
  const readCount = useMemo(
    () => notifications.filter((n) => n.is_read).length,
    [notifications]
  )

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Page Header */}
      <div className="bg-white dark:bg-gray-800 shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
                <BellIcon className="w-7 h-7" />
                Notifications
              </h1>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                {totalItems} total{' '}
                {unreadCount > 0 && (
                  <span className="text-blue-600 dark:text-blue-400">
                    ({unreadCount} unread)
                  </span>
                )}
              </p>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2">
              <button
                onClick={handleRefresh}
                className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
                title="Refresh"
              >
                <ArrowPathIcon className="w-4 h-4" />
              </button>

              {unreadCount > 0 && (
                <button
                  onClick={handleMarkAllAsRead}
                  className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
                >
                  <CheckIcon className="w-4 h-4" />
                  Mark all as read
                </button>
              )}

              {readCount > 0 && (
                <button
                  onClick={handleDeleteAllRead}
                  disabled={isDeleting}
                  className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-600 dark:text-red-400 bg-white dark:bg-gray-700 border border-red-300 dark:border-red-800 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors disabled:opacity-50"
                >
                  <TrashIcon className="w-4 h-4" />
                  {isDeleting ? 'Deleting...' : 'Delete read'}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex flex-col sm:flex-row gap-4">
            {/* Search */}
            <div className="relative flex-1 max-w-md">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search notifications..."
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              {searchInput && (
                <button
                  onClick={() => setSearchInput('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  <XMarkIcon className="w-4 h-4" />
                </button>
              )}
            </div>

            {/* Type Filter */}
            <div className="relative">
              <select
                value={typeFilter || 'all'}
                onChange={(e) => handleTypeFilterChange(e.target.value)}
                className="appearance-none pl-4 pr-10 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent cursor-pointer"
              >
                {typeFilters.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <ChevronDownIcon className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
            </div>

            {/* Read Status Filter */}
            <div className="flex rounded-lg border border-gray-300 dark:border-gray-600 overflow-hidden">
              {readFilters.map((option) => (
                <button
                  key={option.value}
                  onClick={() => handleReadFilterChange(option.value)}
                  className={cn(
                    'px-4 py-2 text-sm font-medium transition-colors',
                    (option.value === 'all' && readFilter === null) ||
                      (option.value === 'unread' && readFilter === false) ||
                      (option.value === 'read' && readFilter === true)
                      ? 'bg-blue-600 text-white'
                      : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600'
                  )}
                >
                  {option.label}
                </button>
              ))}
            </div>

            {/* Clear Filters */}
            {hasActiveFilters && (
              <button
                onClick={() => {
                  clearFilters()
                  setSearchInput('')
                }}
                className="inline-flex items-center gap-1 px-3 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
              >
                <XMarkIcon className="w-4 h-4" />
                Clear filters
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Error State */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <p className="text-red-800 dark:text-red-200">{error}</p>
            <button
              onClick={handleRefresh}
              className="mt-2 text-sm text-red-600 dark:text-red-400 hover:underline"
            >
              Try again
            </button>
          </div>
        )}

        {/* Loading State */}
        {isLoading && notifications.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500" />
            <p className="mt-4 text-gray-500 dark:text-gray-400">Loading notifications...</p>
          </div>
        ) : notifications.length === 0 ? (
          /* Empty State */
          <div className="flex flex-col items-center justify-center py-16">
            <div className="w-16 h-16 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center mb-4">
              <BellIcon className="w-8 h-8 text-gray-400" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">
              No notifications
            </h3>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {hasActiveFilters
                ? 'No notifications match your filters.'
                : "You're all caught up!"}
            </p>
            {hasActiveFilters && (
              <button
                onClick={() => {
                  clearFilters()
                  setSearchInput('')
                }}
                className="mt-4 text-sm text-blue-600 dark:text-blue-400 hover:underline"
              >
                Clear filters
              </button>
            )}
          </div>
        ) : (
          /* Notifications List */
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow divide-y divide-gray-100 dark:divide-gray-700">
            {notifications.map((notification) => (
              <NotificationItem
                key={notification.id}
                notification={notification}
                onMarkAsRead={markAsRead}
                onMarkAsUnread={markAsUnread}
                onDelete={deleteNotification}
              />
            ))}
          </div>
        )}

        {/* Load More */}
        {hasNext && !isLoading && (
          <div className="mt-6 flex justify-center">
            <button
              onClick={handleLoadMore}
              disabled={isLoadingMore}
              className="inline-flex items-center gap-2 px-6 py-3 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors disabled:opacity-50"
            >
              {isLoadingMore ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current" />
                  Loading...
                </>
              ) : (
                'Load more notifications'
              )}
            </button>
          </div>
        )}

        {/* End of List */}
        {!hasNext && notifications.length > 0 && (
          <p className="mt-6 text-center text-sm text-gray-500 dark:text-gray-400">
            That's all your notifications
          </p>
        )}
      </div>
    </div>
  )
}

export default NotificationsPage
