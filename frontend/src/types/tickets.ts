/**
 * Ticket Types
 *
 * Type definitions for ticket management.
 */

import type { BaseEntity, SelectOption } from './common'

// Ticket Status enum values
export type TicketStatus =
  | 'New'
  | 'In Progress'
  | 'On Hold'
  | 'Resolved'
  | 'Closed'
  | 'Processing'
  | 'Resolved - Delivered'

// Ticket Priority enum values
export type TicketPriority = 'Low' | 'Medium' | 'High' | 'Critical'

// Ticket Category enum values
export type TicketCategory =
  | 'PIN_REQUEST'
  | 'REPAIR'
  | 'ASSET_CHECKOUT'
  | 'ASSET_INTAKE'
  | 'ASSET_RETURN'
  | 'INTERNAL_TRANSFER'
  | 'GENERAL'

// Queue interface
export interface Queue {
  id: number
  name: string
  description?: string
  is_active?: boolean
}

// Customer interface (simplified for dropdowns)
export interface Customer {
  id: number
  name: string
  email?: string
  company?: string
  address?: string
}

// User interface (simplified for dropdowns)
export interface UserOption {
  id: number
  username: string
  email?: string
  first_name?: string
  last_name?: string
}

// Ticket interface
export interface Ticket extends BaseEntity {
  display_id?: string
  subject: string
  description?: string
  status: TicketStatus
  custom_status?: string
  priority: TicketPriority
  category?: TicketCategory
  queue_id?: number
  queue_name?: string
  queue?: Queue
  requester_id?: number
  requester_name?: string
  requester?: UserOption
  assigned_to_id?: number
  assigned_to_name?: string
  assigned_to?: UserOption
  customer_id?: number
  customer_name?: string
  customer?: Customer
  asset_id?: number
  country?: string
  shipping_address?: string
  shipping_tracking?: string
  shipping_carrier?: string
  shipping_status?: string
  notes?: string
}

// Create Ticket request payload
export interface CreateTicketPayload {
  subject: string
  description?: string
  category?: string
  priority?: string
  queue_id: number
  customer_id?: number
  assigned_to_id?: number
  asset_id?: number
  country?: string
  shipping_address?: string
  shipping_tracking?: string
  shipping_carrier?: string
  notes?: string
}

// Update Ticket request payload
export interface UpdateTicketPayload extends Partial<CreateTicketPayload> {
  status?: string
  custom_status?: string
}

// Ticket form values (for React Hook Form)
export interface TicketFormValues {
  subject: string
  description: string
  category: string
  priority: string
  queue_id: string
  customer_id: string
  assigned_to_id: string
  notes: string
}

// Category option with description
export interface CategoryOption extends SelectOption {
  description?: string
  icon?: string
  iconColor?: string
}

// Priority options
export const PRIORITY_OPTIONS: SelectOption[] = [
  { value: 'Low', label: 'Low' },
  { value: 'Medium', label: 'Medium' },
  { value: 'High', label: 'High' },
  { value: 'Critical', label: 'Critical' },
]

// Category options
export const CATEGORY_OPTIONS: CategoryOption[] = [
  {
    value: 'PIN_REQUEST',
    label: 'PIN Request',
    description: 'Request device unlock PIN',
  },
  {
    value: 'REPAIR',
    label: 'Repair',
    description: 'Device repair or maintenance',
  },
  {
    value: 'ASSET_CHECKOUT',
    label: 'Asset Checkout',
    description: 'Deploy asset to customer',
  },
  {
    value: 'ASSET_INTAKE',
    label: 'Asset Intake',
    description: 'Receive new assets',
  },
  {
    value: 'ASSET_RETURN',
    label: 'Asset Return',
    description: 'Return asset from customer',
  },
  {
    value: 'INTERNAL_TRANSFER',
    label: 'Internal Transfer',
    description: 'Transfer asset between customers',
  },
  {
    value: 'GENERAL',
    label: 'General',
    description: 'General support request',
  },
]
