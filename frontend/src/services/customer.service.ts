/**
 * Customer Service
 *
 * API methods for customer CRUD operations.
 */

import { apiClient } from './api'
import type {
  Customer,
  CustomerListItem,
  CustomerDetail,
  CustomerFormData,
  CustomerListParams,
  CustomerListResponse,
  CustomerTransaction,
} from '@/types/customer'
import type { CompanyReference } from '@/types/customer'

/**
 * Get paginated list of customers
 */
export async function getCustomers(
  params: CustomerListParams = {}
): Promise<CustomerListResponse> {
  const queryParams = new URLSearchParams()

  if (params.page) queryParams.append('page', String(params.page))
  if (params.per_page) queryParams.append('per_page', String(params.per_page))
  if (params.sort_by) queryParams.append('sort_by', params.sort_by)
  if (params.sort_order) queryParams.append('sort_order', params.sort_order)
  if (params.search) queryParams.append('search', params.search)
  if (params.country) queryParams.append('country', params.country)
  if (params.company_id) queryParams.append('company_id', String(params.company_id))

  const response = await apiClient.get<CustomerListResponse>(
    `/v2/customers?${queryParams.toString()}`
  )
  return response.data
}

/**
 * Get customer by ID
 */
export async function getCustomer(id: number): Promise<CustomerDetail> {
  const response = await apiClient.get<{ data: CustomerDetail }>(
    `/v2/customers/${id}`
  )
  return response.data.data
}

/**
 * Create a new customer
 */
export async function createCustomer(
  data: CustomerFormData
): Promise<Customer> {
  const response = await apiClient.post<{ data: Customer }>(
    '/v2/customers',
    data
  )
  return response.data.data
}

/**
 * Update an existing customer
 */
export async function updateCustomer(
  id: number,
  data: CustomerFormData
): Promise<Customer> {
  const response = await apiClient.put<{ data: Customer }>(
    `/v2/customers/${id}`,
    data
  )
  return response.data.data
}

/**
 * Delete a customer
 */
export async function deleteCustomer(id: number): Promise<void> {
  await apiClient.delete(`/v2/customers/${id}`)
}

/**
 * Get customer transactions
 */
export async function getCustomerTransactions(
  id: number
): Promise<CustomerTransaction[]> {
  const response = await apiClient.get<CustomerTransaction[]>(
    `/inventory/api/customer-users/${id}/transactions`
  )
  return response.data
}

/**
 * Get all companies for filter/dropdown
 */
export async function getCompanies(): Promise<CompanyReference[]> {
  const response = await apiClient.get<{ data: CompanyReference[] }>(
    '/v2/companies'
  )
  return response.data.data
}

/**
 * Get unique countries from customers for filter
 */
export async function getCustomerCountries(): Promise<string[]> {
  const response = await apiClient.get<{ data: string[] }>(
    '/v2/customers/countries'
  )
  return response.data.data
}

/**
 * Customer tickets query parameters
 */
export interface CustomerTicketsParams {
  page?: number
  per_page?: number
  status?: string
  sort?: string
  order?: 'asc' | 'desc'
}

/**
 * Customer tickets response
 */
export interface CustomerTicketsResponse {
  success: boolean
  data: Array<{
    id: number
    display_id: string
    subject: string
    status: string
    category?: string
    created_at: string
    resolved_at?: string
    assets_count?: number
    assigned_to?: {
      id: number
      username: string
    }
  }>
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
      open: number
      resolved: number
    }
  }
}

/**
 * Get tickets for a customer
 */
export async function getCustomerTickets(
  customerId: number,
  params: CustomerTicketsParams = {}
): Promise<CustomerTicketsResponse> {
  const searchParams = new URLSearchParams()

  if (params.page) searchParams.append('page', String(params.page))
  if (params.per_page) searchParams.append('per_page', String(params.per_page))
  if (params.status) searchParams.append('status', params.status)
  if (params.sort) searchParams.append('sort', params.sort)
  if (params.order) searchParams.append('order', params.order)

  const queryString = searchParams.toString()
  const url = queryString
    ? `/v2/customers/${customerId}/tickets?${queryString}`
    : `/v2/customers/${customerId}/tickets`

  const response = await apiClient.get<CustomerTicketsResponse>(url)
  return response.data
}

export const customerService = {
  getCustomers,
  getCustomer,
  createCustomer,
  updateCustomer,
  deleteCustomer,
  getCustomerTransactions,
  getCompanies,
  getCustomerCountries,
  getCustomerTickets,
}

export default customerService
