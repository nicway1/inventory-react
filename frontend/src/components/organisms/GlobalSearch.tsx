/**
 * GlobalSearch Component
 *
 * A global search bar with live suggestions dropdown.
 * Matches the Flask TrueLog search design with:
 * - Gradient border on focus
 * - Grouped search results by type (assets, tickets, accessories, customers)
 * - Keyboard navigation (arrow keys, enter, escape)
 * - "/" keyboard shortcut to focus
 * - Debounced input
 * - Click outside to dismiss
 */

import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  MagnifyingGlassIcon,
  ComputerDesktopIcon,
  TicketIcon,
  CubeIcon,
  UserIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils/cn'
import { useDebounce } from '@/hooks/useDebounce'
import { Spinner } from '../atoms/Spinner'
import { apiClient } from '@/services/api'

// Type colors matching Flask TrueLog
const TYPE_COLORS = {
  asset: '#2e844a',
  ticket: '#ff5d2d',
  accessory: '#fe9339',
  customer: '#9050e9',
} as const

type SearchResultType = keyof typeof TYPE_COLORS

interface SearchResultItem {
  id: number | string
  type: SearchResultType
  title: string
  subtitle?: string
  status?: string
  statusVariant?: 'success' | 'warning' | 'danger' | 'info' | 'neutral'
  url: string
}

interface SearchApiResponse {
  data: {
    assets: Array<{
      id: number
      name: string
      asset_tag?: string
      serial_num?: string
      status?: string
      customer?: string
      item_type: string
    }>
    tickets: Array<{
      id: number
      display_id?: string
      subject: string
      status?: string
      requester?: { name: string }
      item_type: string
    }>
    accessories: Array<{
      id: number
      name: string
      category?: string
      manufacturer?: string
      available_quantity?: number
      item_type: string
    }>
    customers: Array<{
      id: number
      name: string
      email?: string
      company?: string
      item_type: string
    }>
  }
  counts: {
    assets: number
    accessories: number
    customers: number
    tickets: number
    total: number
  }
  query: string
}

// Transform API response to unified search results
function transformSearchResults(data: SearchApiResponse): SearchResultItem[] {
  const results: SearchResultItem[] = []

  // Add assets
  data.data.assets?.forEach((asset) => {
    results.push({
      id: asset.id,
      type: 'asset',
      title: asset.name || asset.asset_tag || `Asset #${asset.id}`,
      subtitle: [asset.serial_num, asset.customer].filter(Boolean).join(' - '),
      status: asset.status,
      statusVariant: getAssetStatusVariant(asset.status),
      url: `/inventory/assets/${asset.id}`,
    })
  })

  // Add tickets
  data.data.tickets?.forEach((ticket) => {
    results.push({
      id: ticket.id,
      type: 'ticket',
      title: ticket.subject || `Ticket ${ticket.display_id || `#${ticket.id}`}`,
      subtitle: ticket.requester?.name || ticket.display_id,
      status: formatTicketStatus(ticket.status),
      statusVariant: getTicketStatusVariant(ticket.status),
      url: `/tickets/${ticket.id}`,
    })
  })

  // Add accessories
  data.data.accessories?.forEach((accessory) => {
    results.push({
      id: accessory.id,
      type: 'accessory',
      title: accessory.name,
      subtitle: [accessory.category, accessory.manufacturer].filter(Boolean).join(' - '),
      status: accessory.available_quantity !== undefined ? `${accessory.available_quantity} available` : undefined,
      statusVariant: accessory.available_quantity && accessory.available_quantity > 0 ? 'success' : 'warning',
      url: `/inventory/accessories/${accessory.id}`,
    })
  })

  // Add customers
  data.data.customers?.forEach((customer) => {
    results.push({
      id: customer.id,
      type: 'customer',
      title: customer.name,
      subtitle: customer.email || customer.company,
      url: `/customers/${customer.id}`,
    })
  })

  return results
}

function formatTicketStatus(status?: string): string | undefined {
  if (!status) return undefined
  const statusMap: Record<string, string> = {
    open: 'New',
    in_progress: 'In Progress',
    resolved: 'Resolved',
    closed: 'Closed',
    on_hold: 'On Hold',
  }
  return statusMap[status] || status.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
}

function getTicketStatusVariant(status?: string): 'success' | 'warning' | 'danger' | 'info' | 'neutral' {
  if (!status) return 'neutral'
  const variantMap: Record<string, 'success' | 'warning' | 'danger' | 'info' | 'neutral'> = {
    open: 'info',
    in_progress: 'warning',
    resolved: 'success',
    closed: 'neutral',
    on_hold: 'warning',
  }
  return variantMap[status] || 'neutral'
}

function getAssetStatusVariant(status?: string): 'success' | 'warning' | 'danger' | 'info' | 'neutral' {
  if (!status) return 'neutral'
  const lowerStatus = status.toLowerCase()
  if (lowerStatus.includes('available') || lowerStatus.includes('ready')) return 'success'
  if (lowerStatus.includes('deployed')) return 'info'
  if (lowerStatus.includes('repair') || lowerStatus.includes('maintenance')) return 'warning'
  if (lowerStatus.includes('retired') || lowerStatus.includes('disposed')) return 'neutral'
  return 'neutral'
}

function getTypeIcon(type: SearchResultType): React.ReactNode {
  const iconClass = 'w-5 h-5'
  switch (type) {
    case 'asset':
      return <ComputerDesktopIcon className={iconClass} />
    case 'ticket':
      return <TicketIcon className={iconClass} />
    case 'accessory':
      return <CubeIcon className={iconClass} />
    case 'customer':
      return <UserIcon className={iconClass} />
    default:
      return <MagnifyingGlassIcon className={iconClass} />
  }
}

function getTypeLabel(type: SearchResultType): string {
  const labels: Record<SearchResultType, string> = {
    asset: 'Assets',
    ticket: 'Tickets',
    accessory: 'Accessories',
    customer: 'Customers',
  }
  return labels[type] || type
}

// Fetch search results
async function fetchSearchResults(query: string): Promise<SearchApiResponse> {
  if (!query || query.length < 2) {
    return {
      data: { assets: [], tickets: [], accessories: [], customers: [] },
      counts: { assets: 0, tickets: 0, accessories: 0, customers: 0, total: 0 },
      query: '',
    }
  }
  const response = await apiClient.get<SearchApiResponse>('/v2/search', {
    params: { q: query, limit: 5 },
  })
  return response.data
}

export interface GlobalSearchProps {
  className?: string
}

export function GlobalSearch({ className }: GlobalSearchProps) {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [isOpen, setIsOpen] = useState(false)
  const [isFocused, setIsFocused] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)

  const inputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Debounce search query (200ms as specified)
  const debouncedQuery = useDebounce(query, 200)

  // Fetch search results using React Query
  const {
    data: searchData,
    isLoading,
    isFetching,
  } = useQuery({
    queryKey: ['globalSearch', debouncedQuery],
    queryFn: () => fetchSearchResults(debouncedQuery),
    enabled: debouncedQuery.length >= 2,
    staleTime: 1000 * 30, // 30 seconds
  })

  // Transform results
  const results = useMemo(() => {
    if (!searchData) return []
    return transformSearchResults(searchData)
  }, [searchData])

  // Group results by type
  const groupedResults = useMemo(() => {
    const groups: Record<SearchResultType, SearchResultItem[]> = {
      asset: [],
      ticket: [],
      accessory: [],
      customer: [],
    }
    results.forEach((result) => {
      groups[result.type].push(result)
    })
    return groups
  }, [results])

  // Flatten for keyboard navigation
  const flatResults = useMemo(() => {
    return Object.values(groupedResults).flat()
  }, [groupedResults])

  // Show dropdown when focused and has query
  const showDropdown = isOpen && query.length >= 2

  // Handle input change
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value)
    setSelectedIndex(-1)
    setIsOpen(true)
  }, [])

  // Handle result selection
  const handleSelect = useCallback(
    (result: SearchResultItem) => {
      setIsOpen(false)
      setQuery('')
      navigate(result.url)
    },
    [navigate]
  )

  // Handle "Search All" button
  const handleSearchAll = useCallback(() => {
    if (query.trim()) {
      setIsOpen(false)
      navigate(`/search?q=${encodeURIComponent(query.trim())}`)
      setQuery('')
    }
  }, [query, navigate])

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (!showDropdown) {
        if (e.key === 'Enter' && query.trim()) {
          handleSearchAll()
        }
        return
      }

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault()
          setSelectedIndex((prev) => (prev < flatResults.length - 1 ? prev + 1 : prev))
          break
        case 'ArrowUp':
          e.preventDefault()
          setSelectedIndex((prev) => (prev > 0 ? prev - 1 : -1))
          break
        case 'Enter':
          e.preventDefault()
          if (selectedIndex >= 0 && selectedIndex < flatResults.length) {
            handleSelect(flatResults[selectedIndex])
          } else {
            handleSearchAll()
          }
          break
        case 'Escape':
          e.preventDefault()
          setIsOpen(false)
          inputRef.current?.blur()
          break
      }
    },
    [showDropdown, selectedIndex, flatResults, handleSelect, handleSearchAll, query]
  )

  // Handle focus
  const handleFocus = useCallback(() => {
    setIsFocused(true)
    if (query.length >= 2) {
      setIsOpen(true)
    }
  }, [query])

  // Handle blur
  const handleBlur = useCallback(() => {
    setIsFocused(false)
  }, [])

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // "/" keyboard shortcut to focus search
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is typing in an input/textarea
      if (
        e.key === '/' &&
        !['INPUT', 'TEXTAREA', 'SELECT'].includes((e.target as HTMLElement).tagName) &&
        !(e.target as HTMLElement).isContentEditable
      ) {
        e.preventDefault()
        inputRef.current?.focus()
      }
    }

    document.addEventListener('keydown', handleGlobalKeyDown)
    return () => document.removeEventListener('keydown', handleGlobalKeyDown)
  }, [])

  // Show loading state
  const showLoading = isLoading || isFetching

  return (
    <div ref={containerRef} className={cn('relative flex-1 max-w-3xl', className)}>
      {/* Search Input with gradient border on focus */}
      <div
        className={cn(
          'relative rounded-xl p-[2px]',
          isFocused
            ? 'bg-gradient-to-r from-blue-500 to-purple-500'
            : 'bg-transparent'
        )}
      >
        <div className="relative">
          {/* Left Icon */}
          <div
            className={cn(
              'absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none transition-colors duration-200',
              isFocused ? 'text-blue-500' : 'text-gray-400'
            )}
          >
            <MagnifyingGlassIcon className="w-5 h-5" />
          </div>

          {/* Input */}
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={handleInputChange}
            onFocus={handleFocus}
            onBlur={handleBlur}
            onKeyDown={handleKeyDown}
            placeholder="Search assets, tickets, accessories, customers..."
            className={cn(
              'w-full rounded-xl bg-white dark:bg-gray-800',
              'border-2 border-gray-200 dark:border-gray-700',
              'focus:border-blue-500 dark:focus:border-blue-500',
              'focus:outline-none',
              'pl-10 pr-16 py-3',
              'text-gray-900 dark:text-gray-100',
              'placeholder:text-gray-400 dark:placeholder:text-gray-500',
              'transition-all duration-200'
            )}
          />

          {/* Right Section */}
          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
            {/* Loading Spinner */}
            {showLoading && <Spinner size="sm" variant="primary" />}

            {/* Keyboard hint "/" badge */}
            {!showLoading && !query && (
              <kbd className="hidden sm:inline-flex items-center justify-center px-2 py-1 text-xs font-medium text-gray-400 dark:text-gray-500 bg-gray-100 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded">
                /
              </kbd>
            )}
          </div>
        </div>
      </div>

      {/* Suggestions Dropdown */}
      {showDropdown && (
        <div
          className={cn(
            'absolute z-50 w-full mt-2',
            'bg-white dark:bg-gray-800',
            'rounded-xl shadow-2xl',
            'border border-gray-200 dark:border-gray-700',
            'overflow-hidden'
          )}
        >
          {/* Header */}
          <div className="px-4 py-3 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-gray-700 dark:to-gray-700 border-b border-gray-200 dark:border-gray-700">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Quick Results
            </span>
            {searchData?.counts?.total !== undefined && searchData.counts.total > 0 && (
              <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
                ({searchData.counts.total} found)
              </span>
            )}
          </div>

          {/* Results */}
          <div className="max-h-[400px] overflow-y-auto">
            {results.length > 0 ? (
              <div className="py-2">
                {/* Grouped results */}
                {(Object.entries(groupedResults) as [SearchResultType, SearchResultItem[]][]).map(
                  ([type, items]) =>
                    items.length > 0 && (
                      <div key={type} className="mb-2 last:mb-0">
                        {/* Group Header */}
                        <div className="px-4 py-1.5 flex items-center gap-2">
                          <span
                            className="w-2 h-2 rounded-full"
                            style={{ backgroundColor: TYPE_COLORS[type] }}
                          />
                          <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                            {getTypeLabel(type)}
                          </span>
                        </div>

                        {/* Group Items */}
                        {items.map((result) => {
                          const flatIndex = flatResults.findIndex(
                            (r) => r.id === result.id && r.type === result.type
                          )
                          const isSelected = flatIndex === selectedIndex

                          return (
                            <button
                              key={`${result.type}-${result.id}`}
                              type="button"
                              onClick={() => handleSelect(result)}
                              onMouseEnter={() => setSelectedIndex(flatIndex)}
                              className={cn(
                                'w-full flex items-center gap-3 px-4 py-2.5 text-left',
                                'transition-all duration-150',
                                isSelected
                                  ? 'bg-gradient-to-r from-blue-50 to-transparent dark:from-blue-900/20 border-l-2 border-blue-500'
                                  : 'hover:bg-gray-50 dark:hover:bg-gray-700/50 border-l-2 border-transparent'
                              )}
                            >
                              {/* Type Icon */}
                              <span
                                className="flex-shrink-0 p-1.5 rounded-lg"
                                style={{
                                  backgroundColor: `${TYPE_COLORS[result.type]}15`,
                                  color: TYPE_COLORS[result.type],
                                }}
                              >
                                {getTypeIcon(result.type)}
                              </span>

                              {/* Content */}
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                  <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                                    {result.title}
                                  </span>
                                  {result.status && (
                                    <span
                                      className={cn(
                                        'inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full',
                                        result.statusVariant === 'success' &&
                                          'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
                                        result.statusVariant === 'warning' &&
                                          'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
                                        result.statusVariant === 'danger' &&
                                          'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
                                        result.statusVariant === 'info' &&
                                          'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
                                        result.statusVariant === 'neutral' &&
                                          'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
                                      )}
                                    >
                                      {result.status}
                                    </span>
                                  )}
                                </div>
                                {result.subtitle && (
                                  <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                                    {result.subtitle}
                                  </p>
                                )}
                              </div>

                              {/* Arrow */}
                              <ChevronRightIcon
                                className={cn(
                                  'flex-shrink-0 w-4 h-4 transition-opacity',
                                  isSelected
                                    ? 'text-blue-500 opacity-100'
                                    : 'text-gray-400 opacity-0 group-hover:opacity-100'
                                )}
                              />
                            </button>
                          )
                        })}
                      </div>
                    )
                )}
              </div>
            ) : debouncedQuery.length >= 2 && !showLoading ? (
              <div className="px-4 py-8 text-center">
                <MagnifyingGlassIcon className="w-8 h-8 mx-auto text-gray-300 dark:text-gray-600 mb-2" />
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  No results found for "{debouncedQuery}"
                </p>
              </div>
            ) : null}
          </div>

          {/* Footer - Search All Button */}
          {query.trim() && (
            <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
              <button
                type="button"
                onClick={handleSearchAll}
                className={cn(
                  'w-full flex items-center justify-center gap-2 px-4 py-2.5',
                  'bg-gradient-to-r from-blue-500 to-purple-500',
                  'text-white text-sm font-medium',
                  'rounded-lg',
                  'hover:from-blue-600 hover:to-purple-600',
                  'transition-all duration-200'
                )}
              >
                <MagnifyingGlassIcon className="w-4 h-4" />
                Search All for "{query}"
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

GlobalSearch.displayName = 'GlobalSearch'
