/**
 * Notifications Service
 *
 * API methods for notification management.
 */

import { apiClient } from './api'

// Notification types
export type NotificationType =
  | 'mention'
  | 'group_mention'
  | 'ticket_assigned'
  | 'ticket_updated'
  | 'asset_checkout'
  | 'asset_checkin'
  | 'system'

// Notification interface
export interface Notification {
  id: number
  type: NotificationType
  title: string
  message: string
  is_read: boolean
  reference_type: 'ticket' | 'asset' | 'comment' | null
  reference_id: number | null
  created_at: string
  read_at: string | null
}

// List params interface
export interface NotificationListParams {
  page?: number
  per_page?: number
  sort?: string
  order?: 'asc' | 'desc'
  type?: NotificationType
  is_read?: boolean
  search?: string
}

// Pagination metadata
export interface PaginationMeta {
  pagination: {
    page: number
    per_page: number
    total_items: number
    total_pages: number
    has_next: boolean
    has_prev: boolean
    next_page: number | null
    prev_page: number | null
  }
  unread_count: number
  request_id: string
  timestamp: string
}

// List response interface
export interface NotificationListResponse {
  success: boolean
  data: Notification[]
  meta: PaginationMeta
}

// Single notification response
export interface NotificationResponse {
  success: boolean
  data: Notification
  message?: string
}

// Count response
export interface UnreadCountResponse {
  success: boolean
  data: {
    unread_count: number
  }
}

// Bulk action response
export interface BulkActionResponse {
  success: boolean
  data: {
    updated_count?: number
    deleted_count?: number
  }
  message?: string
}

/**
 * Get list of notifications with pagination and filtering
 */
export async function getNotifications(
  params: NotificationListParams = {}
): Promise<NotificationListResponse> {
  const searchParams = new URLSearchParams()

  if (params.page) searchParams.append('page', String(params.page))
  if (params.per_page) searchParams.append('per_page', String(params.per_page))
  if (params.sort) searchParams.append('sort', params.sort)
  if (params.order) searchParams.append('order', params.order)
  if (params.type) searchParams.append('type', params.type)
  if (params.is_read !== undefined) searchParams.append('is_read', String(params.is_read))
  if (params.search) searchParams.append('search', params.search)

  const response = await apiClient.get<NotificationListResponse>(
    `/v2/notifications?${searchParams.toString()}`
  )
  return response.data
}

/**
 * Get unread notification count
 */
export async function getUnreadCount(): Promise<number> {
  const response = await apiClient.get<UnreadCountResponse>(
    '/v2/notifications/unread-count'
  )
  return response.data.data.unread_count
}

/**
 * Get a single notification by ID
 */
export async function getNotification(id: number): Promise<Notification> {
  const response = await apiClient.get<NotificationResponse>(
    `/v2/notifications/${id}`
  )
  return response.data.data
}

/**
 * Mark a single notification as read
 */
export async function markAsRead(id: number): Promise<Notification> {
  const response = await apiClient.put<NotificationResponse>(
    `/v2/notifications/${id}/read`
  )
  return response.data.data
}

/**
 * Mark a single notification as unread
 */
export async function markAsUnread(id: number): Promise<Notification> {
  const response = await apiClient.put<NotificationResponse>(
    `/v2/notifications/${id}/unread`
  )
  return response.data.data
}

/**
 * Mark all notifications as read
 * @param type - Optional: only mark notifications of this type as read
 */
export async function markAllAsRead(type?: NotificationType): Promise<number> {
  const response = await apiClient.put<BulkActionResponse>(
    '/v2/notifications/read-all',
    type ? { type } : {}
  )
  return response.data.data.updated_count || 0
}

/**
 * Delete a single notification
 */
export async function deleteNotification(id: number): Promise<void> {
  await apiClient.delete(`/v2/notifications/${id}`)
}

/**
 * Bulk delete notifications by IDs
 */
export async function bulkDeleteNotifications(notificationIds: number[]): Promise<number> {
  const response = await apiClient.post<BulkActionResponse>(
    '/v2/notifications/bulk-delete',
    { notification_ids: notificationIds }
  )
  return response.data.data.deleted_count || 0
}

/**
 * Delete all read notifications
 */
export async function deleteAllReadNotifications(): Promise<number> {
  const response = await apiClient.post<BulkActionResponse>(
    '/v2/notifications/bulk-delete',
    { delete_all_read: true }
  )
  return response.data.data.deleted_count || 0
}

// Export service object
export const notificationsService = {
  getNotifications,
  getUnreadCount,
  getNotification,
  markAsRead,
  markAsUnread,
  markAllAsRead,
  deleteNotification,
  bulkDeleteNotifications,
  deleteAllReadNotifications,
}

export default notificationsService
