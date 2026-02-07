/**
 * Customer Types
 *
 * Type definitions for customer entities and API responses.
 */

import type { BaseEntity, PaginatedResponse } from './common'

// Country enum values (matching Flask backend)
export type Country =
  | 'USA'
  | 'UK'
  | 'SINGAPORE'
  | 'AUSTRALIA'
  | 'JAPAN'
  | 'INDIA'
  | 'PHILIPPINES'
  | 'ISRAEL'
  | 'GERMANY'
  | 'FRANCE'
  | 'CANADA'
  | 'OTHER'

// Company reference
export interface CompanyReference {
  id: number
  name: string
}

// Asset reference for customer detail
export interface CustomerAsset {
  id: number
  asset_tag: string
  name: string
  model: string
  status: string
}

// Accessory reference for customer detail
export interface CustomerAccessory {
  id: number
  name: string
  category: string
  model_no: string
  quantity: number
  status: string
}

// Ticket reference for customer detail
export interface CustomerTicket {
  id: number
  ticket_number: string
  subject: string
  category: string
  status: string
  queue_name: string
  created_at: string
}

// Base customer data
export interface Customer extends BaseEntity {
  name: string
  email: string
  contact_number: string
  address: string
  country: Country | null
  company_id: number | null
  company: CompanyReference | null
}

// Customer list item (for table display)
export interface CustomerListItem extends Customer {
  assets_count: number
  tickets_count: number
  accessories_count: number
}

// Customer detail (full data with related entities)
export interface CustomerDetail extends Customer {
  assigned_assets: CustomerAsset[]
  assigned_accessories: CustomerAccessory[]
  related_tickets: CustomerTicket[]
  transactions?: CustomerTransaction[]
}

// Customer transaction
export interface CustomerTransaction {
  transaction_number: string
  type: 'asset' | 'accessory'
  transaction_type: string
  asset_name?: string
  asset_tag?: string
  accessory_name?: string
  accessory_category?: string
  quantity?: number
  transaction_date: string
  notes?: string
}

// Customer form data (for create/edit)
export interface CustomerFormData {
  name: string
  email: string
  contact_number: string
  address: string
  country: Country | null
  company_id: number | null
}

// Customer list query params
export interface CustomerListParams {
  page?: number
  per_page?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
  search?: string
  country?: Country | ''
  company_id?: number | ''
}

// Customer list response (paginated version)
export type CustomerListResponsePaginated = PaginatedResponse<CustomerListItem>

// Customer list API response
export interface CustomerListResponse {
  success: boolean
  data: CustomerListItem[]
  meta: {
    pagination: {
      page: number
      per_page: number
      total_items: number
      total_pages: number
      has_next: boolean
      has_prev: boolean
    }
  }
}

// Customer API response
export interface CustomerResponse {
  success: boolean
  data: CustomerDetail
  message?: string
}

// Create customer request
export interface CreateCustomerRequest {
  name: string
  contact_number: string
  address: string
  country: Country
  email?: string
  company_id?: number
}

// Update customer request
export interface UpdateCustomerRequest {
  name?: string
  contact_number?: string
  address?: string
  country?: Country
  email?: string
  company_id?: number
}

// Customer stats
export interface CustomerStats {
  total_assets: number
  open_tickets: number
  checked_out_accessories: number
}

// Country options for filters/forms
export const COUNTRY_OPTIONS: { value: Country; label: string }[] = [
  { value: 'USA', label: 'USA' },
  { value: 'UK', label: 'UK' },
  { value: 'SINGAPORE', label: 'Singapore' },
  { value: 'AUSTRALIA', label: 'Australia' },
  { value: 'JAPAN', label: 'Japan' },
  { value: 'INDIA', label: 'India' },
  { value: 'PHILIPPINES', label: 'Philippines' },
  { value: 'ISRAEL', label: 'Israel' },
  { value: 'GERMANY', label: 'Germany' },
  { value: 'FRANCE', label: 'France' },
  { value: 'CANADA', label: 'Canada' },
  { value: 'OTHER', label: 'Other' },
]

// Country badge colors (for visual distinction)
export const COUNTRY_COLORS: Record<Country, { bg: string; text: string }> = {
  USA: { bg: 'bg-blue-100', text: 'text-blue-800' },
  UK: { bg: 'bg-red-100', text: 'text-red-800' },
  SINGAPORE: { bg: 'bg-green-100', text: 'text-green-800' },
  AUSTRALIA: { bg: 'bg-yellow-100', text: 'text-yellow-800' },
  JAPAN: { bg: 'bg-indigo-100', text: 'text-indigo-800' },
  INDIA: { bg: 'bg-orange-100', text: 'text-orange-800' },
  PHILIPPINES: { bg: 'bg-purple-100', text: 'text-purple-800' },
  ISRAEL: { bg: 'bg-teal-100', text: 'text-teal-800' },
  GERMANY: { bg: 'bg-gray-100', text: 'text-gray-800' },
  FRANCE: { bg: 'bg-pink-100', text: 'text-pink-800' },
  CANADA: { bg: 'bg-rose-100', text: 'text-rose-800' },
  OTHER: { bg: 'bg-gray-100', text: 'text-gray-800' },
}
