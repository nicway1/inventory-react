/**
 * Notifications Store
 *
 * Manages notification state with Zustand.
 * Features:
 * - Notifications list with pagination
 * - Unread count tracking
 * - Auto-refresh polling
 * - Optimistic updates for read/unread actions
 */

import { create } from 'zustand'
import {
  notificationsService,
  type Notification,
  type NotificationListParams,
  type NotificationType,
} from '@/services/notifications.service'

// Store state interface
interface NotificationsState {
  // Data
  notifications: Notification[]
  unreadCount: number

  // Pagination
  page: number
  perPage: number
  totalItems: number
  totalPages: number
  hasNext: boolean
  hasPrev: boolean

  // Filters
  typeFilter: NotificationType | null
  readFilter: boolean | null
  searchQuery: string

  // Loading states
  isLoading: boolean
  isLoadingMore: boolean
  isRefreshing: boolean
  error: string | null

  // Polling
  pollingInterval: number | null
  lastFetched: Date | null

  // Actions
  fetchNotifications: (params?: NotificationListParams) => Promise<void>
  fetchMore: () => Promise<void>
  refreshNotifications: () => Promise<void>
  fetchUnreadCount: () => Promise<void>
  markAsRead: (id: number) => Promise<void>
  markAsUnread: (id: number) => Promise<void>
  markAllAsRead: (type?: NotificationType) => Promise<void>
  deleteNotification: (id: number) => Promise<void>
  bulkDelete: (ids: number[]) => Promise<void>
  deleteAllRead: () => Promise<void>

  // Filter actions
  setTypeFilter: (type: NotificationType | null) => void
  setReadFilter: (isRead: boolean | null) => void
  setSearchQuery: (query: string) => void
  clearFilters: () => void

  // Polling actions
  startPolling: (intervalMs?: number) => void
  stopPolling: () => void

  // Reset
  reset: () => void
}

// Initial state values
const initialState = {
  notifications: [],
  unreadCount: 0,
  page: 1,
  perPage: 20,
  totalItems: 0,
  totalPages: 0,
  hasNext: false,
  hasPrev: false,
  typeFilter: null,
  readFilter: null,
  searchQuery: '',
  isLoading: false,
  isLoadingMore: false,
  isRefreshing: false,
  error: null,
  pollingInterval: null,
  lastFetched: null,
}

// Create the store
export const useNotificationsStore = create<NotificationsState>((set, get) => ({
  ...initialState,

  // Fetch notifications with current filters
  fetchNotifications: async (params?: NotificationListParams) => {
    const { typeFilter, readFilter, searchQuery, perPage } = get()

    set({ isLoading: true, error: null })

    try {
      const response = await notificationsService.getNotifications({
        page: params?.page || 1,
        per_page: params?.per_page || perPage,
        type: params?.type || typeFilter || undefined,
        is_read: params?.is_read ?? readFilter ?? undefined,
        search: params?.search || searchQuery || undefined,
        sort: params?.sort || 'created_at',
        order: params?.order || 'desc',
      })

      const { pagination, unread_count } = response.meta

      set({
        notifications: response.data,
        unreadCount: unread_count,
        page: pagination.page,
        perPage: pagination.per_page,
        totalItems: pagination.total_items,
        totalPages: pagination.total_pages,
        hasNext: pagination.has_next,
        hasPrev: pagination.has_prev,
        isLoading: false,
        lastFetched: new Date(),
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch notifications'
      set({ isLoading: false, error: message })
      throw error
    }
  },

  // Fetch more notifications (next page)
  fetchMore: async () => {
    const { page, hasNext, typeFilter, readFilter, searchQuery, perPage, notifications } = get()

    if (!hasNext) return

    set({ isLoadingMore: true })

    try {
      const response = await notificationsService.getNotifications({
        page: page + 1,
        per_page: perPage,
        type: typeFilter || undefined,
        is_read: readFilter ?? undefined,
        search: searchQuery || undefined,
        sort: 'created_at',
        order: 'desc',
      })

      const { pagination, unread_count } = response.meta

      set({
        notifications: [...notifications, ...response.data],
        unreadCount: unread_count,
        page: pagination.page,
        hasNext: pagination.has_next,
        hasPrev: pagination.has_prev,
        isLoadingMore: false,
      })
    } catch (error) {
      set({ isLoadingMore: false })
      throw error
    }
  },

  // Refresh notifications (silent reload)
  refreshNotifications: async () => {
    const { typeFilter, readFilter, searchQuery, perPage } = get()

    set({ isRefreshing: true })

    try {
      const response = await notificationsService.getNotifications({
        page: 1,
        per_page: perPage,
        type: typeFilter || undefined,
        is_read: readFilter ?? undefined,
        search: searchQuery || undefined,
        sort: 'created_at',
        order: 'desc',
      })

      const { pagination, unread_count } = response.meta

      set({
        notifications: response.data,
        unreadCount: unread_count,
        page: pagination.page,
        totalItems: pagination.total_items,
        totalPages: pagination.total_pages,
        hasNext: pagination.has_next,
        hasPrev: pagination.has_prev,
        isRefreshing: false,
        lastFetched: new Date(),
      })
    } catch (error) {
      set({ isRefreshing: false })
      // Silently fail on refresh
    }
  },

  // Fetch just the unread count (for badge updates)
  fetchUnreadCount: async () => {
    try {
      const count = await notificationsService.getUnreadCount()
      set({ unreadCount: count })
    } catch (error) {
      // Silently fail
    }
  },

  // Mark a notification as read (optimistic update)
  markAsRead: async (id: number) => {
    const { notifications, unreadCount } = get()

    // Optimistic update
    const notification = notifications.find((n) => n.id === id)
    const wasUnread = notification && !notification.is_read

    set({
      notifications: notifications.map((n) =>
        n.id === id ? { ...n, is_read: true, read_at: new Date().toISOString() } : n
      ),
      unreadCount: wasUnread ? Math.max(0, unreadCount - 1) : unreadCount,
    })

    try {
      await notificationsService.markAsRead(id)
    } catch (error) {
      // Revert on failure
      set({
        notifications: notifications,
        unreadCount: unreadCount,
      })
      throw error
    }
  },

  // Mark a notification as unread (optimistic update)
  markAsUnread: async (id: number) => {
    const { notifications, unreadCount } = get()

    // Optimistic update
    const notification = notifications.find((n) => n.id === id)
    const wasRead = notification && notification.is_read

    set({
      notifications: notifications.map((n) =>
        n.id === id ? { ...n, is_read: false, read_at: null } : n
      ),
      unreadCount: wasRead ? unreadCount + 1 : unreadCount,
    })

    try {
      await notificationsService.markAsUnread(id)
    } catch (error) {
      // Revert on failure
      set({
        notifications: notifications,
        unreadCount: unreadCount,
      })
      throw error
    }
  },

  // Mark all notifications as read
  markAllAsRead: async (type?: NotificationType) => {
    const { notifications } = get()

    // Optimistic update
    set({
      notifications: notifications.map((n) =>
        !type || n.type === type
          ? { ...n, is_read: true, read_at: new Date().toISOString() }
          : n
      ),
      unreadCount: type
        ? get().notifications.filter((n) => n.type !== type && !n.is_read).length
        : 0,
    })

    try {
      await notificationsService.markAllAsRead(type)
    } catch (error) {
      // Revert on failure - refetch
      get().refreshNotifications()
      throw error
    }
  },

  // Delete a notification (optimistic update)
  deleteNotification: async (id: number) => {
    const { notifications, unreadCount } = get()

    // Find and remove notification
    const notification = notifications.find((n) => n.id === id)
    const wasUnread = notification && !notification.is_read

    set({
      notifications: notifications.filter((n) => n.id !== id),
      unreadCount: wasUnread ? Math.max(0, unreadCount - 1) : unreadCount,
      totalItems: get().totalItems - 1,
    })

    try {
      await notificationsService.deleteNotification(id)
    } catch (error) {
      // Revert on failure
      set({
        notifications: notifications,
        unreadCount: unreadCount,
        totalItems: get().totalItems + 1,
      })
      throw error
    }
  },

  // Bulk delete notifications
  bulkDelete: async (ids: number[]) => {
    const { notifications, unreadCount } = get()

    // Calculate how many unread are being deleted
    const unreadBeingDeleted = notifications.filter(
      (n) => ids.includes(n.id) && !n.is_read
    ).length

    // Optimistic update
    set({
      notifications: notifications.filter((n) => !ids.includes(n.id)),
      unreadCount: Math.max(0, unreadCount - unreadBeingDeleted),
      totalItems: get().totalItems - ids.length,
    })

    try {
      await notificationsService.bulkDeleteNotifications(ids)
    } catch (error) {
      // Revert on failure - refetch
      get().refreshNotifications()
      throw error
    }
  },

  // Delete all read notifications
  deleteAllRead: async () => {
    const { notifications, totalItems } = get()

    // Count read notifications
    const readCount = notifications.filter((n) => n.is_read).length

    // Optimistic update
    set({
      notifications: notifications.filter((n) => !n.is_read),
      totalItems: totalItems - readCount,
    })

    try {
      await notificationsService.deleteAllReadNotifications()
    } catch (error) {
      // Revert on failure - refetch
      get().refreshNotifications()
      throw error
    }
  },

  // Filter actions
  setTypeFilter: (type: NotificationType | null) => {
    set({ typeFilter: type, page: 1 })
    get().fetchNotifications({ page: 1, type: type || undefined })
  },

  setReadFilter: (isRead: boolean | null) => {
    set({ readFilter: isRead, page: 1 })
    get().fetchNotifications({ page: 1, is_read: isRead ?? undefined })
  },

  setSearchQuery: (query: string) => {
    set({ searchQuery: query, page: 1 })
    // Debounce search in the component
  },

  clearFilters: () => {
    set({
      typeFilter: null,
      readFilter: null,
      searchQuery: '',
      page: 1,
    })
    get().fetchNotifications({ page: 1 })
  },

  // Polling for real-time updates
  startPolling: (intervalMs = 30000) => {
    const { pollingInterval } = get()

    // Don't start if already polling
    if (pollingInterval) return

    const interval = window.setInterval(() => {
      // Skip polling when tab is not visible to reduce noisy traffic/logging.
      if (typeof document !== 'undefined' && document.hidden) {
        return
      }
      get().fetchUnreadCount()
    }, intervalMs)

    set({ pollingInterval: interval })
  },

  stopPolling: () => {
    const { pollingInterval } = get()

    if (pollingInterval) {
      window.clearInterval(pollingInterval)
      set({ pollingInterval: null })
    }
  },

  // Reset store to initial state
  reset: () => {
    const { pollingInterval } = get()

    // Stop polling if active
    if (pollingInterval) {
      window.clearInterval(pollingInterval)
    }

    set(initialState)
  },
}))

// Hook to get just the unread count (for header badge)
export const useUnreadCount = () => useNotificationsStore((state) => state.unreadCount)

// Hook to get notifications list
export const useNotifications = () =>
  useNotificationsStore((state) => ({
    notifications: state.notifications,
    isLoading: state.isLoading,
    isLoadingMore: state.isLoadingMore,
    hasNext: state.hasNext,
    error: state.error,
  }))
