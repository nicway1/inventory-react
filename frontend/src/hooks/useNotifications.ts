/**
 * useNotifications Hook
 *
 * Provides notification-related functionality including:
 * - Toast notifications for new notifications
 * - Navigation to notification references
 * - Unread count tracking
 */

import { useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useNotificationsStore } from '@/store/notifications.store'
import { useUIStore } from '@/store/ui.store'
import type { Notification } from '@/services/notifications.service'

/**
 * Hook to show toast notifications when new notifications arrive
 */
export function useNotificationToasts() {
  const { unreadCount, fetchUnreadCount } = useNotificationsStore()
  const { addToast } = useUIStore()
  const previousCountRef = useRef<number>(unreadCount)

  // Check for new notifications and show toast
  useEffect(() => {
    // Only show toast if count increased (not on initial load)
    if (
      previousCountRef.current !== null &&
      unreadCount > previousCountRef.current &&
      previousCountRef.current > 0
    ) {
      const newCount = unreadCount - previousCountRef.current
      addToast({
        type: 'info',
        message: `You have ${newCount} new notification${newCount > 1 ? 's' : ''}`,
        duration: 5000,
      })
    }

    previousCountRef.current = unreadCount
  }, [unreadCount, addToast])

  return {
    unreadCount,
    refreshCount: fetchUnreadCount,
  }
}

/**
 * Hook to navigate to a notification's reference
 */
export function useNotificationNavigation() {
  const navigate = useNavigate()
  const { markAsRead } = useNotificationsStore()

  const navigateToNotification = useCallback(
    async (notification: Notification) => {
      // Mark as read if unread
      if (!notification.is_read) {
        try {
          await markAsRead(notification.id)
        } catch (error) {
          console.error('Failed to mark notification as read:', error)
        }
      }

      // Navigate based on reference type
      if (notification.reference_type && notification.reference_id) {
        switch (notification.reference_type) {
          case 'ticket':
            navigate(`/tickets/${notification.reference_id}`)
            break
          case 'asset':
            navigate(`/inventory/assets/${notification.reference_id}`)
            break
          default:
            // No navigation for unknown types
            break
        }
      }
    },
    [navigate, markAsRead]
  )

  return { navigateToNotification }
}

/**
 * Hook to get notification icon and color based on type
 */
export function useNotificationStyles(type: Notification['type']) {
  const styles = {
    mention: {
      icon: 'AtSymbolIcon',
      color: 'blue',
      bgClass: 'bg-blue-100 dark:bg-blue-900/30',
      textClass: 'text-blue-600 dark:text-blue-400',
    },
    group_mention: {
      icon: 'UserGroupIcon',
      color: 'purple',
      bgClass: 'bg-purple-100 dark:bg-purple-900/30',
      textClass: 'text-purple-600 dark:text-purple-400',
    },
    ticket_assigned: {
      icon: 'TicketIcon',
      color: 'orange',
      bgClass: 'bg-orange-100 dark:bg-orange-900/30',
      textClass: 'text-orange-600 dark:text-orange-400',
    },
    ticket_updated: {
      icon: 'TicketIcon',
      color: 'cyan',
      bgClass: 'bg-cyan-100 dark:bg-cyan-900/30',
      textClass: 'text-cyan-600 dark:text-cyan-400',
    },
    asset_checkout: {
      icon: 'ArchiveBoxIcon',
      color: 'green',
      bgClass: 'bg-green-100 dark:bg-green-900/30',
      textClass: 'text-green-600 dark:text-green-400',
    },
    asset_checkin: {
      icon: 'ArchiveBoxIcon',
      color: 'teal',
      bgClass: 'bg-teal-100 dark:bg-teal-900/30',
      textClass: 'text-teal-600 dark:text-teal-400',
    },
    system: {
      icon: 'BellAlertIcon',
      color: 'gray',
      bgClass: 'bg-gray-100 dark:bg-gray-700',
      textClass: 'text-gray-600 dark:text-gray-400',
    },
  }

  return styles[type] || styles.system
}

/**
 * Combined hook for common notification operations
 */
export function useNotifications() {
  const store = useNotificationsStore()
  const { navigateToNotification } = useNotificationNavigation()

  return {
    // State
    notifications: store.notifications,
    unreadCount: store.unreadCount,
    isLoading: store.isLoading,
    isLoadingMore: store.isLoadingMore,
    hasNext: store.hasNext,
    error: store.error,

    // Actions
    fetch: store.fetchNotifications,
    fetchMore: store.fetchMore,
    refresh: store.refreshNotifications,
    markAsRead: store.markAsRead,
    markAsUnread: store.markAsUnread,
    markAllAsRead: store.markAllAsRead,
    deleteNotification: store.deleteNotification,
    navigateToNotification,

    // Filters
    setTypeFilter: store.setTypeFilter,
    setReadFilter: store.setReadFilter,
    setSearchQuery: store.setSearchQuery,
    clearFilters: store.clearFilters,

    // Polling
    startPolling: store.startPolling,
    stopPolling: store.stopPolling,
  }
}

export default useNotifications
