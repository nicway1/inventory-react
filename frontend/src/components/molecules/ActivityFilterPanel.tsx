/**
 * ActivityFilterPanel Component
 *
 * Provides filtering options for the activity/history log.
 * Includes date range, action type, entity type, and user filters.
 */

import { useState, useEffect } from 'react'
import {
  FunnelIcon,
  XMarkIcon,
  MagnifyingGlassIcon,
  CalendarIcon,
  ChevronDownIcon,
} from '@heroicons/react/24/outline'
import { Button } from '@/components/atoms/Button'
import { Input } from '@/components/atoms/Input'
import { cn } from '@/utils/cn'
import type { ActivityFilters, ActivityAction, ActivityEntityType } from '@/types/history'

interface ActivityFilterPanelProps {
  filters: ActivityFilters
  onFiltersChange: (filters: ActivityFilters) => void
  users?: { id: number; name: string }[]
  isLoading?: boolean
  className?: string
}

/**
 * Action type options
 */
const ACTION_OPTIONS: { value: ActivityAction | 'all'; label: string }[] = [
  { value: 'all', label: 'All Actions' },
  { value: 'create', label: 'Create' },
  { value: 'update', label: 'Update' },
  { value: 'delete', label: 'Delete' },
  { value: 'assign', label: 'Assign' },
  { value: 'status_change', label: 'Status Change' },
  { value: 'comment', label: 'Comment' },
  { value: 'attachment', label: 'Attachment' },
  { value: 'login', label: 'Login' },
  { value: 'logout', label: 'Logout' },
]

/**
 * Entity type options
 */
const ENTITY_OPTIONS: { value: ActivityEntityType | 'all'; label: string }[] = [
  { value: 'all', label: 'All Entities' },
  { value: 'ticket', label: 'Tickets' },
  { value: 'asset', label: 'Assets' },
  { value: 'customer', label: 'Customers' },
  { value: 'user', label: 'Users' },
  { value: 'company', label: 'Companies' },
  { value: 'queue', label: 'Queues' },
  { value: 'accessory', label: 'Accessories' },
]

/**
 * Date range presets
 */
const DATE_PRESETS = [
  { label: 'Today', days: 0 },
  { label: 'Last 7 days', days: 7 },
  { label: 'Last 30 days', days: 30 },
  { label: 'Last 90 days', days: 90 },
  { label: 'This year', days: 365 },
]

/**
 * Custom select component
 */
function FilterSelect<T extends string | number>({
  label,
  value,
  options,
  onChange,
  className,
}: {
  label: string
  value: T | 'all'
  options: { value: T | 'all'; label: string }[]
  onChange: (value: T | 'all') => void
  className?: string
}) {
  return (
    <div className={cn('relative', className)}>
      <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
        {label}
      </label>
      <div className="relative">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value as T | 'all')}
          className={cn(
            'w-full appearance-none rounded-lg border border-gray-300 dark:border-gray-600',
            'bg-white dark:bg-gray-800 text-gray-900 dark:text-white',
            'px-3 py-2 pr-10 text-sm',
            'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'cursor-pointer'
          )}
        >
          {options.map((option) => (
            <option key={String(option.value)} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <ChevronDownIcon className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
      </div>
    </div>
  )
}

export function ActivityFilterPanel({
  filters,
  onFiltersChange,
  users = [],
  isLoading = false,
  className,
}: ActivityFilterPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [localSearch, setLocalSearch] = useState(filters.search || '')

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      if (localSearch !== filters.search) {
        onFiltersChange({ ...filters, search: localSearch || undefined })
      }
    }, 300)

    return () => clearTimeout(timer)
  }, [localSearch])

  // Update local search when filters change externally
  useEffect(() => {
    setLocalSearch(filters.search || '')
  }, [filters.search])

  /**
   * Handle filter change
   */
  const handleFilterChange = <K extends keyof ActivityFilters>(
    key: K,
    value: ActivityFilters[K]
  ) => {
    onFiltersChange({
      ...filters,
      [key]: value === 'all' ? undefined : value,
    })
  }

  /**
   * Handle date preset selection
   */
  const handleDatePreset = (days: number) => {
    const now = new Date()
    let from: Date

    if (days === 0) {
      // Today
      from = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    } else {
      from = new Date(now.getTime() - days * 24 * 60 * 60 * 1000)
    }

    onFiltersChange({
      ...filters,
      date_from: from.toISOString().split('T')[0],
      date_to: now.toISOString().split('T')[0],
    })
  }

  /**
   * Clear all filters
   */
  const handleClearFilters = () => {
    setLocalSearch('')
    onFiltersChange({})
  }

  /**
   * Check if any filters are active
   */
  const hasActiveFilters =
    filters.search ||
    (filters.action && filters.action !== 'all') ||
    (filters.entity_type && filters.entity_type !== 'all') ||
    (filters.user_id && filters.user_id !== 'all') ||
    filters.date_from ||
    filters.date_to

  // Prepare user options
  const userOptions: { value: number | 'all'; label: string }[] = [
    { value: 'all', label: 'All Users' },
    ...users.map((user) => ({ value: user.id, label: user.name })),
  ]

  return (
    <div className={cn('bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700', className)}>
      {/* Main filter bar */}
      <div className="p-4">
        <div className="flex flex-wrap items-center gap-4">
          {/* Search input */}
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search activities..."
                value={localSearch}
                onChange={(e) => setLocalSearch(e.target.value)}
                className={cn(
                  'w-full rounded-lg border border-gray-300 dark:border-gray-600',
                  'bg-white dark:bg-gray-800 text-gray-900 dark:text-white',
                  'pl-10 pr-4 py-2 text-sm',
                  'placeholder:text-gray-400 dark:placeholder:text-gray-500',
                  'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                )}
              />
            </div>
          </div>

          {/* Quick filters */}
          <FilterSelect
            label="Action"
            value={filters.action || 'all'}
            options={ACTION_OPTIONS}
            onChange={(value) => handleFilterChange('action', value)}
            className="w-[150px]"
          />

          <FilterSelect
            label="Entity"
            value={filters.entity_type || 'all'}
            options={ENTITY_OPTIONS}
            onChange={(value) => handleFilterChange('entity_type', value)}
            className="w-[150px]"
          />

          {/* Toggle advanced filters */}
          <Button
            variant="ghost"
            size="sm"
            leftIcon={<FunnelIcon className="w-4 h-4" />}
            onClick={() => setIsExpanded(!isExpanded)}
            className={cn(isExpanded && 'bg-gray-100 dark:bg-gray-700')}
          >
            More Filters
            {hasActiveFilters && (
              <span className="ml-1 px-1.5 py-0.5 text-xs bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-400 rounded-full">
                Active
              </span>
            )}
          </Button>

          {/* Clear filters */}
          {hasActiveFilters && (
            <Button
              variant="ghost"
              size="sm"
              leftIcon={<XMarkIcon className="w-4 h-4" />}
              onClick={handleClearFilters}
            >
              Clear
            </Button>
          )}
        </div>
      </div>

      {/* Expanded filters */}
      {isExpanded && (
        <div className="px-4 pb-4 border-t border-gray-200 dark:border-gray-700 pt-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* User filter */}
            {users.length > 0 && (
              <FilterSelect
                label="User"
                value={filters.user_id || 'all'}
                options={userOptions}
                onChange={(value) => handleFilterChange('user_id', value)}
              />
            )}

            {/* Date from */}
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                Date From
              </label>
              <div className="relative">
                <CalendarIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="date"
                  value={filters.date_from || ''}
                  onChange={(e) => handleFilterChange('date_from', e.target.value || undefined)}
                  className={cn(
                    'w-full rounded-lg border border-gray-300 dark:border-gray-600',
                    'bg-white dark:bg-gray-800 text-gray-900 dark:text-white',
                    'pl-10 pr-3 py-2 text-sm',
                    'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                  )}
                />
              </div>
            </div>

            {/* Date to */}
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                Date To
              </label>
              <div className="relative">
                <CalendarIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="date"
                  value={filters.date_to || ''}
                  onChange={(e) => handleFilterChange('date_to', e.target.value || undefined)}
                  className={cn(
                    'w-full rounded-lg border border-gray-300 dark:border-gray-600',
                    'bg-white dark:bg-gray-800 text-gray-900 dark:text-white',
                    'pl-10 pr-3 py-2 text-sm',
                    'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                  )}
                />
              </div>
            </div>

            {/* Date presets */}
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                Quick Date Range
              </label>
              <div className="flex flex-wrap gap-1">
                {DATE_PRESETS.map((preset) => (
                  <button
                    key={preset.label}
                    onClick={() => handleDatePreset(preset.days)}
                    className={cn(
                      'px-2 py-1 text-xs rounded-md transition-colors',
                      'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400',
                      'hover:bg-blue-100 dark:hover:bg-blue-900/30 hover:text-blue-600 dark:hover:text-blue-400'
                    )}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ActivityFilterPanel
