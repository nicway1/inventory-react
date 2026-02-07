/**
 * Dashboard Service
 *
 * API methods for dashboard widgets and data.
 */

import { apiClient } from './api'
import type {
  Widget,
  WidgetsResponse,
  WidgetDataResponse,
  TicketStatsData,
  InventoryStatsData,
  WidgetSize,
} from '@/types/dashboard'
import type { PaginatedResponse } from '@/types'
import type { DashboardLayout, WidgetConfig } from '@/store/dashboard.store'

/**
 * Dashboard preferences response from API
 */
export interface DashboardPreferencesResponse {
  success: boolean
  data: {
    widgets: Array<{
      widget_id: string
      enabled: boolean
      position: number
      size: WidgetSize
      config: Record<string, unknown>
    }>
    last_updated: string | null
  }
  message?: string
}

/**
 * Dashboard preferences request payload
 */
export interface DashboardPreferencesPayload {
  widgets: Array<{
    widget_id: string
    enabled: boolean
    position: number
    size: WidgetSize
    config: Record<string, unknown>
  }>
}

/**
 * Get all available dashboard widgets
 */
export async function getWidgets(options?: {
  category?: string
  includeAll?: boolean
}): Promise<Widget[]> {
  const params = new URLSearchParams()
  if (options?.category) {
    params.append('category', options.category)
  }
  if (options?.includeAll) {
    params.append('include_all', 'true')
  }

  const response = await apiClient.get<WidgetsResponse>(
    `/v2/dashboard/widgets?${params.toString()}`
  )
  return response.data.data
}

/**
 * Get data for a specific widget
 */
export async function getWidgetData<T = unknown>(
  widgetId: string,
  config?: Record<string, unknown>
): Promise<T> {
  const params = new URLSearchParams()
  if (config) {
    params.append('config', JSON.stringify(config))
  }

  const response = await apiClient.get<WidgetDataResponse<T>>(
    `/v2/dashboard/widgets/${widgetId}/data?${params.toString()}`
  )
  return response.data.data
}

/**
 * Get ticket statistics
 */
export async function getTicketStats(config?: {
  show_resolved?: boolean
  time_period?: '7d' | '30d' | '90d'
}): Promise<TicketStatsData> {
  return getWidgetData<TicketStatsData>('ticket_stats', config)
}

/**
 * Get inventory statistics
 */
export async function getInventoryStats(): Promise<InventoryStatsData> {
  return getWidgetData<InventoryStatsData>('inventory_stats')
}

/**
 * Ticket list item for recent tickets
 */
export interface TicketListItem {
  id: number
  display_id: string
  subject: string
  description?: string
  status: string
  custom_status?: string
  priority: string
  category?: string
  queue_id?: number
  queue_name?: string
  requester_id?: number
  requester_name?: string
  assigned_to_id?: number
  assigned_to_name?: string
  customer_id?: number
  customer_name?: string
  asset_id?: number
  country?: string
  shipping_address?: string
  shipping_tracking?: string
  shipping_carrier?: string
  shipping_status?: string
  notes?: string
  created_at: string
  updated_at?: string
}

/**
 * Get recent tickets
 */
export async function getRecentTickets(options?: {
  per_page?: number
  sort?: string
  order?: 'asc' | 'desc'
}): Promise<TicketListItem[]> {
  const params = new URLSearchParams()
  params.append('per_page', String(options?.per_page || 5))
  params.append('sort_by', options?.sort || 'created_at')
  params.append('sort_order', options?.order || 'desc')

  const response = await apiClient.get<{ data: PaginatedResponse<TicketListItem> }>(
    `/v2/tickets?${params.toString()}`
  )
  return response.data.data.items
}

/**
 * Get user's dashboard preferences
 */
export async function getDashboardPreferences(): Promise<DashboardLayout> {
  try {
    const response = await apiClient.get<DashboardPreferencesResponse>(
      '/v2/user/preferences/dashboard'
    )

    if (response.data.success && response.data.data) {
      const { widgets, last_updated } = response.data.data
      return {
        widgets: widgets.map((w) => ({
          widgetId: w.widget_id,
          enabled: w.enabled,
          position: w.position,
          size: w.size,
          config: w.config || {},
        })),
        lastUpdated: last_updated,
      }
    }

    // Return empty layout if no preferences saved
    return { widgets: [], lastUpdated: null }
  } catch (error) {
    // If 404 or no preferences, return empty
    console.error('Failed to fetch dashboard preferences:', error)
    return { widgets: [], lastUpdated: null }
  }
}

/**
 * Save user's dashboard preferences
 */
export async function saveDashboardPreferences(
  layout: DashboardLayout
): Promise<DashboardLayout> {
  const payload: DashboardPreferencesPayload = {
    widgets: layout.widgets.map((w) => ({
      widget_id: w.widgetId,
      enabled: w.enabled,
      position: w.position,
      size: w.size,
      config: w.config,
    })),
  }

  const response = await apiClient.post<DashboardPreferencesResponse>(
    '/v2/user/preferences/dashboard',
    payload
  )

  if (response.data.success && response.data.data) {
    const { widgets, last_updated } = response.data.data
    return {
      widgets: widgets.map((w) => ({
        widgetId: w.widget_id,
        enabled: w.enabled,
        position: w.position,
        size: w.size,
        config: w.config || {},
      })),
      lastUpdated: last_updated,
    }
  }

  return layout
}

/**
 * Reset dashboard preferences to default
 */
export async function resetDashboardPreferences(): Promise<void> {
  await apiClient.delete('/v2/user/preferences/dashboard')
}

export const dashboardService = {
  getWidgets,
  getWidgetData,
  getTicketStats,
  getInventoryStats,
  getRecentTickets,
  getDashboardPreferences,
  saveDashboardPreferences,
  resetDashboardPreferences,
}

export default dashboardService
