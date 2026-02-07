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
} from '@/types/dashboard'
import type { PaginatedResponse } from '@/types'

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

export const dashboardService = {
  getWidgets,
  getWidgetData,
  getTicketStats,
  getInventoryStats,
  getRecentTickets,
}

export default dashboardService
