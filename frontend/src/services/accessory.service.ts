/**
 * Accessory Service
 *
 * API methods for accessory CRUD operations.
 */

import { apiClient } from './api'
import type {
  Accessory,
  AccessoryFilters,
} from '@/types/inventory'

const ACCESSORIES_BASE_URL = '/v2/accessories'

/**
 * Accessory list query parameters
 */
export interface AccessoryListParams {
  page?: number
  per_page?: number
  search?: string
  category?: string
  manufacturer?: string
  country?: string
  company_id?: number
  sort?: string
  order?: 'asc' | 'desc'
}

/**
 * Accessory API response
 */
export interface AccessoryResponse {
  success: boolean
  data: Accessory
  message?: string
}

/**
 * Accessory list API response
 */
export interface AccessoryListResponse {
  success: boolean
  data: Accessory[]
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

/**
 * Create accessory request
 */
export interface CreateAccessoryRequest {
  name: string
  category: string
  manufacturer?: string
  model_no?: string
  total_quantity?: number
  country?: string
  notes?: string
  image_url?: string
  company_id?: number
  aliases?: string[]
}

/**
 * Update accessory request
 */
export interface UpdateAccessoryRequest extends Partial<CreateAccessoryRequest> {}

/**
 * Accessory checkin request
 */
export interface AccessoryCheckinRequest {
  customer_id: number
  quantity?: number
  condition?: string
  notes?: string
  ticket_id?: number
}

/**
 * Accessory return request
 */
export interface AccessoryReturnRequest {
  quantity?: number
  customer_id?: number
  notes?: string
}

/**
 * Accessory checkin response
 */
export interface AccessoryCheckinResponse {
  success: boolean
  data: {
    id: number
    accessory: {
      id: number
      name: string
      available_quantity: number
      total_quantity: number
    }
    customer: {
      id: number
      name: string
    }
    quantity_returned: number
    condition?: string
    transaction_id: number
    checked_in_at: string
  }
  message?: string
}

/**
 * Build query string from parameters
 */
function buildQueryString(params: AccessoryListParams): string {
  const searchParams = new URLSearchParams()

  if (params.page) searchParams.append('page', String(params.page))
  if (params.per_page) searchParams.append('per_page', String(params.per_page))
  if (params.search) searchParams.append('search', params.search)
  if (params.category) searchParams.append('category', params.category)
  if (params.manufacturer) searchParams.append('manufacturer', params.manufacturer)
  if (params.country) searchParams.append('country', params.country)
  if (params.company_id) searchParams.append('company_id', String(params.company_id))
  if (params.sort) searchParams.append('sort', params.sort)
  if (params.order) searchParams.append('order', params.order)

  return searchParams.toString()
}

/**
 * Get list of accessories with pagination and filters
 */
export async function getAccessories(
  params: AccessoryListParams = {}
): Promise<AccessoryListResponse> {
  const queryString = buildQueryString(params)
  const url = queryString ? `${ACCESSORIES_BASE_URL}?${queryString}` : ACCESSORIES_BASE_URL
  const response = await apiClient.get<AccessoryListResponse>(url)
  return response.data
}

/**
 * Get a single accessory by ID
 */
export async function getAccessory(accessoryId: number): Promise<AccessoryResponse> {
  const response = await apiClient.get<AccessoryResponse>(
    `${ACCESSORIES_BASE_URL}/${accessoryId}`
  )
  return response.data
}

/**
 * Create a new accessory
 */
export async function createAccessory(
  data: CreateAccessoryRequest
): Promise<AccessoryResponse> {
  const response = await apiClient.post<AccessoryResponse>(ACCESSORIES_BASE_URL, data)
  return response.data
}

/**
 * Update an existing accessory
 */
export async function updateAccessory(
  accessoryId: number,
  data: UpdateAccessoryRequest
): Promise<AccessoryResponse> {
  const response = await apiClient.put<AccessoryResponse>(
    `${ACCESSORIES_BASE_URL}/${accessoryId}`,
    data
  )
  return response.data
}

/**
 * Delete an accessory
 */
export async function deleteAccessory(accessoryId: number): Promise<void> {
  await apiClient.delete(`${ACCESSORIES_BASE_URL}/${accessoryId}`)
}

/**
 * Check in (return) an accessory from a customer
 */
export async function checkinAccessory(
  accessoryId: number,
  data: AccessoryCheckinRequest
): Promise<AccessoryCheckinResponse> {
  const response = await apiClient.post<AccessoryCheckinResponse>(
    `${ACCESSORIES_BASE_URL}/${accessoryId}/checkin`,
    data
  )
  return response.data
}

/**
 * Return an accessory to inventory
 */
export async function returnAccessory(
  accessoryId: number,
  data: AccessoryReturnRequest
): Promise<AccessoryResponse> {
  const response = await apiClient.post<AccessoryResponse>(
    `${ACCESSORIES_BASE_URL}/${accessoryId}/return`,
    data
  )
  return response.data
}

/**
 * Accessory service object with all methods
 */
export const accessoryService = {
  getAccessories,
  getAccessory,
  createAccessory,
  updateAccessory,
  deleteAccessory,
  checkinAccessory,
  returnAccessory,
}

export default accessoryService
