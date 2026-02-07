/**
 * NotificationDropdown Component
 *
 * Full dropdown for notifications in the header.
 * Features:
 * - Shows recent notifications
 * - Mark all as read action
 * - View all link to notifications page
 * - Empty state
 * - Loading state
 * - Auto-refresh on open
 */

import { Fragment, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { Transition } from '@headlessui/react'
import {
  BellIcon,
  CheckIcon,
  ArrowRightIcon,
} from '@heroicons/react/24/outline'
import { useNotificationsStore } from '@/store/notifications.store'
import { NotificationItem } from '@/components/molecules/NotificationItem'
import { cn } from '@/utils/cn'

interface NotificationDropdownProps {
  isOpen: boolean
  onClose: () => void
}

export function NotificationDropdown({ isOpen, onClose }: NotificationDropdownProps) {
  const {
    notifications,
    unreadCount,
    isLoading,
    isRefreshing,
    fetchNotifications,
    markAsRead,
    markAsUnread,
    markAllAsRead,
    deleteNotification,
  } = useNotificationsStore()

  // Fetch notifications when dropdown opens
  useEffect(() => {
    if (isOpen) {
      fetchNotifications({ per_page: 10 })
    }
  }, [isOpen, fetchNotifications])

  // Handle mark all as read
  const handleMarkAllAsRead = useCallback(
    async (e: React.MouseEvent) => {
      e.preventDefault()
      e.stopPropagation()
      try {
        await markAllAsRead()
      } catch (error) {
        console.error('Failed to mark all as read:', error)
      }
    },
    [markAllAsRead]
  )

  // Handle notification actions
  const handleMarkAsRead = useCallback(
    async (id: number) => {
      try {
        await markAsRead(id)
      } catch (error) {
        console.error('Failed to mark as read:', error)
      }
    },
    [markAsRead]
  )

  const handleMarkAsUnread = useCallback(
    async (id: number) => {
      try {
        await markAsUnread(id)
      } catch (error) {
        console.error('Failed to mark as unread:', error)
      }
    },
    [markAsUnread]
  )

  const handleDelete = useCallback(
    async (id: number) => {
      try {
        await deleteNotification(id)
      } catch (error) {
        console.error('Failed to delete notification:', error)
      }
    },
    [deleteNotification]
  )

  return (
    <Transition
      show={isOpen}
      as={Fragment}
      enter="transition ease-out duration-100"
      enterFrom="transform opacity-0 scale-95"
      enterTo="transform opacity-100 scale-100"
      leave="transition ease-in duration-75"
      leaveFrom="transform opacity-100 scale-100"
      leaveTo="transform opacity-0 scale-95"
    >
      <div className="absolute right-0 mt-2 w-96 bg-white dark:bg-gray-800 rounded-lg shadow-lg ring-1 ring-black/5 dark:ring-white/10 z-50 overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center bg-gray-50 dark:bg-gray-800/50">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
              Notifications
            </h3>
            {unreadCount > 0 && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/50 dark:text-blue-200">
                {unreadCount} new
              </span>
            )}
          </div>

          {unreadCount > 0 && (
            <button
              onClick={handleMarkAllAsRead}
              className="flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 font-medium"
            >
              <CheckIcon className="w-3.5 h-3.5" />
              Mark all read
            </button>
          )}
        </div>

        {/* Content */}
        <div className="max-h-[400px] overflow-y-auto">
          {isLoading && notifications.length === 0 ? (
            // Loading state
            <div className="p-8 text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto" />
              <p className="mt-3 text-sm text-gray-500 dark:text-gray-400">
                Loading notifications...
              </p>
            </div>
          ) : notifications.length === 0 ? (
            // Empty state
            <div className="p-8 text-center">
              <div className="mx-auto w-12 h-12 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center mb-3">
                <BellIcon className="w-6 h-6 text-gray-400" />
              </div>
              <p className="text-sm font-medium text-gray-900 dark:text-white">
                No notifications
              </p>
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                You're all caught up!
              </p>
            </div>
          ) : (
            // Notifications list
            <div className="divide-y divide-gray-100 dark:divide-gray-700/50">
              {notifications.slice(0, 10).map((notification) => (
                <NotificationItem
                  key={notification.id}
                  notification={notification}
                  onMarkAsRead={handleMarkAsRead}
                  onMarkAsUnread={handleMarkAsUnread}
                  onDelete={handleDelete}
                  compact
                />
              ))}
            </div>
          )}

          {/* Refreshing indicator */}
          {isRefreshing && (
            <div className="absolute top-16 left-1/2 -translate-x-1/2 bg-blue-500 text-white text-xs px-3 py-1 rounded-full shadow-lg">
              Refreshing...
            </div>
          )}
        </div>

        {/* Footer */}
        {notifications.length > 0 && (
          <div className="p-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
            <Link
              to="/notifications"
              onClick={onClose}
              className="flex items-center justify-center gap-2 w-full py-2 text-sm font-medium text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors"
            >
              View all notifications
              <ArrowRightIcon className="w-4 h-4" />
            </Link>
          </div>
        )}
      </div>
    </Transition>
  )
}

export default NotificationDropdown
