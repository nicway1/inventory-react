/**
 * Ticket Types
 *
 * Type definitions for ticket management.
 */

import { BaseEntity } from './common'

/**
 * Ticket status values
 */
export type TicketStatus =
  | 'NEW'
  | 'IN_PROGRESS'
  | 'PROCESSING'
  | 'ON_HOLD'
  | 'RESOLVED'
  | 'RESOLVED_DELIVERED'

/**
 * Ticket priority values
 */
export type TicketPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT'

/**
 * Queue interface
 */
export interface Queue {
  id: number
  name: string
  description?: string
  ticket_count?: number
  open_count?: number
}

/**
 * Ticket assignee
 */
export interface Assignee {
  id: number
  username: string
  first_name: string
  last_name: string
  full_name: string
}

/**
 * Customer info for ticket
 */
export interface TicketCustomer {
  id: number
  name: string
  email?: string
  company?: string
}

/**
 * Ticket list item (for table display)
 */
export interface Ticket extends BaseEntity {
  display_id?: string
  subject: string
  description?: string
  status: TicketStatus
  custom_status?: string
  priority: TicketPriority
  category?: string
  queue_id?: number
  queue_name?: string
  requester_id?: number
  requester_name?: string
  assigned_to_id?: number
  assigned_to_name?: string
  customer_id?: number
  customer_name?: string
  customer_email?: string
  asset_id?: number
  asset_tag?: string
  country?: string
  shipping_address?: string
  shipping_tracking?: string
  shipping_carrier?: string
  shipping_status?: string
  notes?: string
  order_id?: string
  resolved_at?: string
}

/**
 * Ticket filter parameters
 */
export interface TicketFilters {
  status?: TicketStatus | 'all'
  priority?: TicketPriority | 'all'
  queue_id?: number | 'all'
  assigned_to_id?: number
  customer_id?: number
  date_from?: string
  date_to?: string
  search?: string
}

/**
 * Ticket list request parameters
 */
export interface TicketListParams extends TicketFilters {
  page?: number
  per_page?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

/**
 * Create ticket request
 */
export interface CreateTicketRequest {
  subject: string
  queue_id: number
  description?: string
  category?: string
  priority?: TicketPriority
  customer_id?: number
  asset_id?: number
  shipping_address?: string
  shipping_tracking?: string
  shipping_carrier?: string
  country?: string
  notes?: string
  assigned_to_id?: number
}

/**
 * Update ticket request
 */
export interface UpdateTicketRequest {
  subject?: string
  description?: string
  priority?: TicketPriority
  queue_id?: number
  customer_id?: number
  asset_id?: number
  shipping_address?: string
  shipping_tracking?: string
  shipping_carrier?: string
  country?: string
  notes?: string
}

/**
 * Assign ticket request
 */
export interface AssignTicketRequest {
  assigned_to_id: number
}

/**
 * Change ticket status request
 */
export interface ChangeTicketStatusRequest {
  status: TicketStatus
  custom_status?: string
}

/**
 * Bulk action types
 */
export type BulkActionType = 'assign' | 'status' | 'delete' | 'queue'

/**
 * Bulk action request
 */
export interface BulkActionRequest {
  ticket_ids: number[]
  action: BulkActionType
  value?: string | number
}

/**
 * Ticket API response
 */
export interface TicketResponse {
  success: boolean
  data: Ticket
  message?: string
}

/**
 * Ticket list API response
 */
export interface TicketListResponse {
  success: boolean
  data: Ticket[]
  meta: {
    pagination: {
      page: number
      per_page: number
      total_items: number
      total_pages: number
      has_next: boolean
      has_prev: boolean
    }
    counts?: {
      total: number
      new: number
      in_progress: number
      resolved: number
      on_hold: number
    }
  }
}

/**
 * Status badge mapping
 */
export const STATUS_CONFIG: Record<TicketStatus, { variant: 'info' | 'warning' | 'success' | 'neutral' | 'danger'; label: string }> = {
  NEW: { variant: 'info', label: 'New' },
  IN_PROGRESS: { variant: 'warning', label: 'In Progress' },
  PROCESSING: { variant: 'warning', label: 'Processing' },
  ON_HOLD: { variant: 'neutral', label: 'On Hold' },
  RESOLVED: { variant: 'success', label: 'Resolved' },
  RESOLVED_DELIVERED: { variant: 'success', label: 'Resolved - Delivered' },
}

/**
 * Priority badge mapping
 */
export const PRIORITY_CONFIG: Record<TicketPriority, { variant: 'neutral' | 'info' | 'warning' | 'danger'; label: string }> = {
  LOW: { variant: 'neutral', label: 'Low' },
  MEDIUM: { variant: 'info', label: 'Medium' },
  HIGH: { variant: 'warning', label: 'High' },
  URGENT: { variant: 'danger', label: 'Urgent' },
}
