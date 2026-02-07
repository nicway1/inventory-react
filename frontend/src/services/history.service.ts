/**
 * History/Audit Log Service
 *
 * API methods for activity log management.
 */

import { apiClient } from './api'
import type {
  Activity,
  ActivityListParams,
  ActivityListResponse,
  ActivityTypesResponse,
  ActivityExportOptions,
  ActivityEntityType,
} from '@/types/history'

/**
 * Build query string from params
 */
function buildQueryString(params: ActivityListParams): string {
  const searchParams = new URLSearchParams()

  if (params.page) searchParams.append('page', String(params.page))
  if (params.per_page) searchParams.append('per_page', String(params.per_page))
  if (params.sort) searchParams.append('sort', params.sort)
  if (params.order) searchParams.append('order', params.order)
  if (params.search) searchParams.append('search', params.search)
  if (params.action && params.action !== 'all') searchParams.append('action', params.action)
  if (params.entity_type && params.entity_type !== 'all') searchParams.append('entity_type', params.entity_type)
  if (params.user_id && params.user_id !== 'all') searchParams.append('user_id', String(params.user_id))
  if (params.date_from) searchParams.append('date_from', params.date_from)
  if (params.date_to) searchParams.append('date_to', params.date_to)
  if (params.type) searchParams.append('type', params.type)

  return searchParams.toString()
}

/**
 * Get paginated list of activities
 */
export async function getActivities(
  params: ActivityListParams = {}
): Promise<ActivityListResponse> {
  const queryString = buildQueryString(params)
  const response = await apiClient.get<ActivityListResponse>(
    `/v2/admin/activities${queryString ? `?${queryString}` : ''}`
  )
  return response.data
}

/**
 * Get a single activity by ID
 */
export async function getActivity(id: number): Promise<Activity> {
  const response = await apiClient.get<{ data: Activity }>(`/v2/admin/activities/${id}`)
  return response.data.data
}

/**
 * Get activities for a specific entity
 */
export async function getEntityActivities(
  entityType: ActivityEntityType,
  entityId: number,
  params: Omit<ActivityListParams, 'entity_type'> = {}
): Promise<ActivityListResponse> {
  const queryString = buildQueryString({ ...params, entity_type: entityType })
  const response = await apiClient.get<ActivityListResponse>(
    `/v2/${entityType}s/${entityId}/activities${queryString ? `?${queryString}` : ''}`
  )
  return response.data
}

/**
 * Get ticket activities
 */
export async function getTicketActivities(
  ticketId: number,
  params: ActivityListParams = {}
): Promise<ActivityListResponse> {
  const queryString = buildQueryString(params)
  const response = await apiClient.get<ActivityListResponse>(
    `/v2/tickets/${ticketId}/activity${queryString ? `?${queryString}` : ''}`
  )
  // Transform response to match expected format
  const activities = response.data.data || (response.data as unknown as { activities: Activity[] }).activities || []
  return {
    data: activities,
    meta: {
      pagination: {
        page: 1,
        per_page: activities.length,
        total: activities.length,
        total_pages: 1,
      },
    },
  }
}

/**
 * Get asset activities
 */
export async function getAssetActivities(
  assetId: number,
  params: ActivityListParams = {}
): Promise<ActivityListResponse> {
  const queryString = buildQueryString(params)
  const response = await apiClient.get<ActivityListResponse>(
    `/v2/assets/${assetId}/activity${queryString ? `?${queryString}` : ''}`
  )
  const activities = response.data.data || (response.data as unknown as { activities: Activity[] }).activities || []
  return {
    data: activities,
    meta: {
      pagination: {
        page: 1,
        per_page: activities.length,
        total: activities.length,
        total_pages: 1,
      },
    },
  }
}

/**
 * Get customer activities
 */
export async function getCustomerActivities(
  customerId: number,
  params: ActivityListParams = {}
): Promise<ActivityListResponse> {
  const queryString = buildQueryString(params)
  const response = await apiClient.get<ActivityListResponse>(
    `/v2/customers/${customerId}/activity${queryString ? `?${queryString}` : ''}`
  )
  const activities = response.data.data || (response.data as unknown as { activities: Activity[] }).activities || []
  return {
    data: activities,
    meta: {
      pagination: {
        page: 1,
        per_page: activities.length,
        total: activities.length,
        total_pages: 1,
      },
    },
  }
}

/**
 * Get available activity types for filtering
 */
export async function getActivityTypes(): Promise<ActivityTypesResponse> {
  try {
    const response = await apiClient.get<ActivityTypesResponse>('/v2/admin/activities/types')
    return response.data
  } catch {
    // Fallback to default types if endpoint doesn't exist
    return {
      data: {
        actions: [
          { value: 'create', label: 'Create' },
          { value: 'update', label: 'Update' },
          { value: 'delete', label: 'Delete' },
          { value: 'assign', label: 'Assign' },
          { value: 'status_change', label: 'Status Change' },
          { value: 'comment', label: 'Comment' },
          { value: 'attachment', label: 'Attachment' },
          { value: 'login', label: 'Login' },
          { value: 'logout', label: 'Logout' },
        ],
        entity_types: [
          { value: 'ticket', label: 'Ticket' },
          { value: 'asset', label: 'Asset' },
          { value: 'customer', label: 'Customer' },
          { value: 'user', label: 'User' },
          { value: 'company', label: 'Company' },
          { value: 'queue', label: 'Queue' },
          { value: 'accessory', label: 'Accessory' },
        ],
        activity_types: [
          'ticket_created',
          'ticket_updated',
          'ticket_deleted',
          'ticket_assigned',
          'ticket_status_changed',
          'asset_created',
          'asset_updated',
          'asset_deleted',
          'customer_created',
          'customer_updated',
          'customer_deleted',
          'admin_user_created',
          'admin_user_updated',
          'admin_user_deleted',
          'admin_company_created',
          'admin_company_updated',
          'admin_company_deleted',
        ],
      },
    }
  }
}

/**
 * Get users for activity filter dropdown
 */
export async function getActivityUsers(): Promise<{ id: number; name: string }[]> {
  try {
    const response = await apiClient.get<{ data: { id: number; username: string; email: string }[] }>(
      '/v2/users?limit=200'
    )
    return response.data.data.map((user) => ({
      id: user.id,
      name: user.username || user.email,
    }))
  } catch {
    return []
  }
}

/**
 * Export activities to file
 */
export async function exportActivities(options: ActivityExportOptions): Promise<Blob> {
  const params: ActivityListParams = {
    ...options.filters,
    per_page: 10000, // Get all activities
  }

  if (options.date_range) {
    params.date_from = options.date_range.from
    params.date_to = options.date_range.to
  }

  const queryString = buildQueryString(params)
  const response = await apiClient.get(
    `/v2/admin/activities/export?format=${options.format}${queryString ? `&${queryString}` : ''}`,
    {
      responseType: 'blob',
    }
  )

  return response.data
}

/**
 * Download exported activities file
 */
export function downloadExportFile(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

/**
 * Mark activity as read
 */
export async function markActivityAsRead(id: number): Promise<void> {
  await apiClient.patch(`/v2/activities/${id}/read`)
}

/**
 * Mark all activities as read
 */
export async function markAllActivitiesAsRead(): Promise<void> {
  await apiClient.post('/v2/activities/mark-all-read')
}

/**
 * History service object for default export
 */
export const historyService = {
  getActivities,
  getActivity,
  getEntityActivities,
  getTicketActivities,
  getAssetActivities,
  getCustomerActivities,
  getActivityTypes,
  getActivityUsers,
  exportActivities,
  downloadExportFile,
  markActivityAsRead,
  markAllActivitiesAsRead,
}

export default historyService
