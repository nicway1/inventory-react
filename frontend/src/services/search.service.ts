/**
 * Search Service
 *
 * API methods for global search functionality.
 */

import { apiClient } from './api'

/**
 * Search result item from API
 */
export interface SearchResultAsset {
  id: number
  name: string
  asset_tag?: string
  serial_num?: string
  status?: string
  customer?: string
  country?: string
  manufacturer?: string
  model?: string
  item_type: 'asset'
}

export interface SearchResultTicket {
  id: number
  display_id?: string
  subject: string
  description?: string
  status?: string
  priority?: string
  category?: string
  requester?: { id: number; name: string; email: string }
  assigned_to?: { id: number; name: string; email: string }
  item_type: 'ticket'
}

export interface SearchResultAccessory {
  id: number
  name: string
  category?: string
  manufacturer?: string
  model_no?: string
  available_quantity?: number
  total_quantity?: number
  country?: string
  item_type: 'accessory'
}

export interface SearchResultCustomer {
  id: number
  name: string
  email?: string
  contact_number?: string
  company?: string
  address?: string
  item_type: 'customer'
}

export interface SearchApiResponse {
  data: {
    assets: SearchResultAsset[]
    tickets: SearchResultTicket[]
    accessories: SearchResultAccessory[]
    customers: SearchResultCustomer[]
    related_tickets?: SearchResultTicket[]
  }
  counts: {
    assets: number
    accessories: number
    customers: number
    tickets: number
    related_tickets?: number
    total: number
  }
  query: string
  pagination?: {
    page: number
    limit: number
    total: number
    pages: number
  }
  search_types?: string[]
}

export interface SearchOptions {
  query: string
  limit?: number
  page?: number
  types?: Array<'assets' | 'accessories' | 'customers' | 'tickets'>
  includeRelated?: boolean
}

/**
 * Perform global search across all entity types
 */
export async function globalSearch(options: SearchOptions): Promise<SearchApiResponse> {
  const params = new URLSearchParams()

  params.append('q', options.query)

  if (options.limit) {
    params.append('limit', String(options.limit))
  }

  if (options.page) {
    params.append('page', String(options.page))
  }

  if (options.types && options.types.length > 0) {
    params.append('types', options.types.join(','))
  }

  if (options.includeRelated !== undefined) {
    params.append('include_related', String(options.includeRelated))
  }

  const response = await apiClient.get<SearchApiResponse>(`/v2/search?${params.toString()}`)
  return response.data
}

/**
 * Get search suggestions for autocomplete
 */
export interface SearchSuggestion {
  text: string
  type: string
}

export interface SearchSuggestionsResponse {
  suggestions: SearchSuggestion[]
}

export async function getSearchSuggestions(
  query: string,
  entityType?: 'assets' | 'accessories' | 'customers' | 'tickets',
  limit?: number
): Promise<SearchSuggestion[]> {
  if (query.length < 2) {
    return []
  }

  const params = new URLSearchParams()
  params.append('q', query)

  if (entityType) {
    params.append('type', entityType)
  }

  if (limit) {
    params.append('limit', String(limit))
  }

  const response = await apiClient.get<SearchSuggestionsResponse>(
    `/v2/search/suggestions?${params.toString()}`
  )
  return response.data.suggestions
}

export const searchService = {
  globalSearch,
  getSearchSuggestions,
}

export default searchService
