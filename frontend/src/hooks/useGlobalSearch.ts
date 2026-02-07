/**
 * useGlobalSearch Hook
 *
 * React Query hook for global search functionality.
 */

import { useQuery } from '@tanstack/react-query'
import { globalSearch, getSearchSuggestions } from '@/services/search.service'
import type { SearchApiResponse, SearchSuggestion } from '@/services/search.service'

// Query keys for search
export const searchKeys = {
  all: ['search'] as const,
  global: (query: string) => [...searchKeys.all, 'global', query] as const,
  suggestions: (query: string, type?: string) =>
    [...searchKeys.all, 'suggestions', query, type] as const,
}

export interface UseGlobalSearchOptions {
  query: string
  limit?: number
  types?: Array<'assets' | 'accessories' | 'customers' | 'tickets'>
  enabled?: boolean
}

/**
 * Hook for performing global search
 */
export function useGlobalSearch(options: UseGlobalSearchOptions) {
  const { query, limit = 5, types, enabled = true } = options

  return useQuery<SearchApiResponse, Error>({
    queryKey: searchKeys.global(query),
    queryFn: () =>
      globalSearch({
        query,
        limit,
        types,
      }),
    enabled: enabled && query.length >= 2,
    staleTime: 1000 * 30, // 30 seconds
    gcTime: 1000 * 60 * 5, // 5 minutes
  })
}

export interface UseSearchSuggestionsOptions {
  query: string
  type?: 'assets' | 'accessories' | 'customers' | 'tickets'
  limit?: number
  enabled?: boolean
}

/**
 * Hook for getting search suggestions/autocomplete
 */
export function useSearchSuggestions(options: UseSearchSuggestionsOptions) {
  const { query, type, limit = 10, enabled = true } = options

  return useQuery<SearchSuggestion[], Error>({
    queryKey: searchKeys.suggestions(query, type),
    queryFn: () => getSearchSuggestions(query, type, limit),
    enabled: enabled && query.length >= 2,
    staleTime: 1000 * 60, // 1 minute
    gcTime: 1000 * 60 * 5, // 5 minutes
  })
}
