/**
 * History/Audit Log Types
 *
 * Type definitions for the history/audit log feature.
 */

import { BaseEntity } from './common'

/**
 * Activity action types
 */
export type ActivityAction = 'create' | 'update' | 'delete' | 'assign' | 'status_change' | 'comment' | 'attachment' | 'login' | 'logout' | 'export' | 'import' | 'bulk_action'

/**
 * Entity types that can have activity logs
 */
export type ActivityEntityType = 'ticket' | 'asset' | 'customer' | 'user' | 'company' | 'queue' | 'accessory' | 'comment' | 'attachment' | 'system'

/**
 * Activity log entry
 */
export interface Activity extends BaseEntity {
  user_id: number
  user_name?: string
  user_email?: string
  type: string
  action?: ActivityAction
  content: string
  reference_id?: number
  entity_type?: ActivityEntityType
  entity_name?: string
  is_read: boolean
  metadata?: Record<string, unknown>
  changes?: ActivityChange[]
  ip_address?: string
  user_agent?: string
}

/**
 * Activity change entry for tracking field changes
 */
export interface ActivityChange {
  field: string
  old_value: string | number | boolean | null
  new_value: string | number | boolean | null
}

/**
 * Activity type configuration for display
 */
export interface ActivityTypeConfig {
  type: string
  label: string
  icon: string
  color: string
  category: ActivityAction
}

/**
 * Activity type definitions for the system
 */
export const ACTIVITY_TYPES: Record<string, ActivityTypeConfig> = {
  // Ticket activities
  ticket_created: { type: 'ticket_created', label: 'Ticket Created', icon: 'plus', color: 'green', category: 'create' },
  ticket_updated: { type: 'ticket_updated', label: 'Ticket Updated', icon: 'pencil', color: 'blue', category: 'update' },
  ticket_deleted: { type: 'ticket_deleted', label: 'Ticket Deleted', icon: 'trash', color: 'red', category: 'delete' },
  ticket_assigned: { type: 'ticket_assigned', label: 'Ticket Assigned', icon: 'user-plus', color: 'purple', category: 'assign' },
  ticket_status_changed: { type: 'ticket_status_changed', label: 'Status Changed', icon: 'refresh', color: 'orange', category: 'status_change' },
  ticket_comment_added: { type: 'ticket_comment_added', label: 'Comment Added', icon: 'chat', color: 'teal', category: 'comment' },

  // Asset activities
  asset_created: { type: 'asset_created', label: 'Asset Created', icon: 'plus', color: 'green', category: 'create' },
  asset_updated: { type: 'asset_updated', label: 'Asset Updated', icon: 'pencil', color: 'blue', category: 'update' },
  asset_deleted: { type: 'asset_deleted', label: 'Asset Deleted', icon: 'trash', color: 'red', category: 'delete' },
  asset_checked_out: { type: 'asset_checked_out', label: 'Asset Checked Out', icon: 'arrow-right', color: 'purple', category: 'update' },
  asset_checked_in: { type: 'asset_checked_in', label: 'Asset Checked In', icon: 'arrow-left', color: 'teal', category: 'update' },

  // Customer activities
  customer_created: { type: 'customer_created', label: 'Customer Created', icon: 'plus', color: 'green', category: 'create' },
  customer_updated: { type: 'customer_updated', label: 'Customer Updated', icon: 'pencil', color: 'blue', category: 'update' },
  customer_deleted: { type: 'customer_deleted', label: 'Customer Deleted', icon: 'trash', color: 'red', category: 'delete' },

  // User/Admin activities
  admin_user_created: { type: 'admin_user_created', label: 'User Created', icon: 'user-plus', color: 'green', category: 'create' },
  admin_user_updated: { type: 'admin_user_updated', label: 'User Updated', icon: 'user', color: 'blue', category: 'update' },
  admin_user_deleted: { type: 'admin_user_deleted', label: 'User Deleted', icon: 'user-minus', color: 'red', category: 'delete' },
  admin_user_deactivated: { type: 'admin_user_deactivated', label: 'User Deactivated', icon: 'user-x', color: 'orange', category: 'update' },
  admin_user_deleted_permanent: { type: 'admin_user_deleted_permanent', label: 'User Permanently Deleted', icon: 'user-minus', color: 'red', category: 'delete' },

  // Company activities
  admin_company_created: { type: 'admin_company_created', label: 'Company Created', icon: 'building', color: 'green', category: 'create' },
  admin_company_updated: { type: 'admin_company_updated', label: 'Company Updated', icon: 'building', color: 'blue', category: 'update' },
  admin_company_deleted: { type: 'admin_company_deleted', label: 'Company Deleted', icon: 'building', color: 'red', category: 'delete' },

  // Queue activities
  admin_queue_created: { type: 'admin_queue_created', label: 'Queue Created', icon: 'folder', color: 'green', category: 'create' },
  admin_queue_updated: { type: 'admin_queue_updated', label: 'Queue Updated', icon: 'folder', color: 'blue', category: 'update' },
  admin_queue_deleted: { type: 'admin_queue_deleted', label: 'Queue Deleted', icon: 'folder', color: 'red', category: 'delete' },

  // Category activities
  admin_category_created: { type: 'admin_category_created', label: 'Category Created', icon: 'tag', color: 'green', category: 'create' },
  admin_category_updated: { type: 'admin_category_updated', label: 'Category Updated', icon: 'tag', color: 'blue', category: 'update' },
  admin_category_deleted: { type: 'admin_category_deleted', label: 'Category Deleted', icon: 'tag', color: 'red', category: 'delete' },

  // Auth activities
  user_login: { type: 'user_login', label: 'User Login', icon: 'login', color: 'green', category: 'login' },
  user_logout: { type: 'user_logout', label: 'User Logout', icon: 'logout', color: 'gray', category: 'logout' },

  // System activities
  mention: { type: 'mention', label: 'Mentioned', icon: 'at', color: 'blue', category: 'comment' },
  system: { type: 'system', label: 'System Event', icon: 'cog', color: 'gray', category: 'update' },
}

/**
 * Activity filters interface
 */
export interface ActivityFilters {
  search?: string
  action?: ActivityAction | 'all'
  entity_type?: ActivityEntityType | 'all'
  user_id?: number | 'all'
  date_from?: string
  date_to?: string
  type?: string
}

/**
 * Activity list request parameters
 */
export interface ActivityListParams extends ActivityFilters {
  page?: number
  per_page?: number
  sort?: string
  order?: 'asc' | 'desc'
}

/**
 * Activity list response
 */
export interface ActivityListResponse {
  data: Activity[]
  meta: {
    pagination: {
      page: number
      per_page: number
      total: number
      total_pages: number
    }
    counts?: {
      total: number
      by_action?: Record<string, number>
      by_entity?: Record<string, number>
    }
  }
}

/**
 * Activity types response
 */
export interface ActivityTypesResponse {
  data: {
    actions: { value: ActivityAction; label: string }[]
    entity_types: { value: ActivityEntityType; label: string }[]
    activity_types: string[]
  }
}

/**
 * Export options
 */
export interface ActivityExportOptions {
  format: 'csv' | 'xlsx' | 'json'
  filters?: ActivityFilters
  include_metadata?: boolean
  date_range?: {
    from: string
    to: string
  }
}

/**
 * Entity activity props for reusable component
 */
export interface EntityActivityProps {
  entityType: ActivityEntityType
  entityId: number
  limit?: number
  showHeader?: boolean
  className?: string
}

/**
 * Get color class for activity action
 */
export function getActivityActionColor(action: ActivityAction): string {
  const colorMap: Record<ActivityAction, string> = {
    create: 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/30',
    update: 'text-blue-600 bg-blue-100 dark:text-blue-400 dark:bg-blue-900/30',
    delete: 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900/30',
    assign: 'text-purple-600 bg-purple-100 dark:text-purple-400 dark:bg-purple-900/30',
    status_change: 'text-orange-600 bg-orange-100 dark:text-orange-400 dark:bg-orange-900/30',
    comment: 'text-teal-600 bg-teal-100 dark:text-teal-400 dark:bg-teal-900/30',
    attachment: 'text-cyan-600 bg-cyan-100 dark:text-cyan-400 dark:bg-cyan-900/30',
    login: 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/30',
    logout: 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-700/30',
    export: 'text-indigo-600 bg-indigo-100 dark:text-indigo-400 dark:bg-indigo-900/30',
    import: 'text-indigo-600 bg-indigo-100 dark:text-indigo-400 dark:bg-indigo-900/30',
    bulk_action: 'text-yellow-600 bg-yellow-100 dark:text-yellow-400 dark:bg-yellow-900/30',
  }
  return colorMap[action] || 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-700/30'
}

/**
 * Get icon name for activity action
 */
export function getActivityActionIcon(action: ActivityAction): string {
  const iconMap: Record<ActivityAction, string> = {
    create: 'plus-circle',
    update: 'pencil',
    delete: 'trash',
    assign: 'user-plus',
    status_change: 'arrow-path',
    comment: 'chat-bubble-left',
    attachment: 'paper-clip',
    login: 'arrow-right-on-rectangle',
    logout: 'arrow-left-on-rectangle',
    export: 'arrow-down-tray',
    import: 'arrow-up-tray',
    bulk_action: 'squares-2x2',
  }
  return iconMap[action] || 'clock'
}
