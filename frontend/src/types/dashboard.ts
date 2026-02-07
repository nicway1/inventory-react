/**
 * Dashboard Types
 *
 * Type definitions for dashboard widgets and data.
 */

// Widget size for grid layout
export type WidgetSize = 'small' | 'medium' | 'large' | 'full'

// Widget categories
export type WidgetCategory = 'stats' | 'charts' | 'lists' | 'actions' | 'system'

// Widget definition from API
export interface Widget {
  id: string
  name: string
  description: string
  long_description?: string
  category: WidgetCategory
  icon: string
  color: string
  default_size: { w: number; h: number }
  min_size: { w: number; h: number }
  max_size: { w: number; h: number }
  config_options: WidgetConfigOption[]
  permissions: string[]
  refreshable: boolean
  configurable: boolean
  screenshot?: string
  has_access: boolean
}

// Widget configuration option
export interface WidgetConfigOption {
  key: string
  type: 'string' | 'number' | 'boolean' | 'select'
  label: string
  default: unknown
  options?: string[]
  min?: number
  max?: number
}

// Ticket status enum
export type TicketStatus = 'NEW' | 'IN_PROGRESS' | 'RESOLVED' | 'RESOLVED_DELIVERED'

// Ticket stats from API
export interface TicketStatsData {
  widget_id: string
  generated_at: string
  values: {
    total: number
    open: number
    in_progress: number
    resolved?: number
  }
  chart_data?: {
    labels: string[]
    values: number[]
    colors: string[]
  }
}

// Inventory stats from API
export interface InventoryStatsData {
  widget_id: string
  generated_at: string
  values: {
    total: number
    tech_assets: number
    accessories: number
  }
  chart_data: null
}

// Recent ticket for list display
export interface RecentTicket {
  id: number
  display_id: string
  subject: string
  status: TicketStatus
  custom_status?: string
  priority: string
  customer_name: string | null
  requester_name: string | null
  created_at: string
}

// Stats card trend direction
export type TrendDirection = 'up' | 'down' | 'neutral'

// Stats card variant colors
export type StatsCardVariant = 'blue' | 'green' | 'purple' | 'orange' | 'red' | 'cyan' | 'indigo' | 'gray'

// Widgets API response
export interface WidgetsResponse {
  data: Widget[]
  meta: {
    categories: WidgetCategoryMeta[]
    total_available: number
    total_widgets: number
  }
}

// Widget category metadata
export interface WidgetCategoryMeta {
  id: string
  name: string
  icon: string
  description: string
}

// Widget data API response
export interface WidgetDataResponse<T = unknown> {
  data: T
  success: boolean
  message?: string
}
