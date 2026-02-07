/**
 * EmptyState Component
 *
 * A reusable empty state component for tables, lists, and other
 * content areas when there's no data to display.
 */

import React from 'react'
import {
  FolderOpenIcon,
  DocumentIcon,
  MagnifyingGlassIcon,
  PlusIcon,
  ExclamationTriangleIcon,
  InboxIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils/cn'

// Preset empty state types
export type EmptyStatePreset =
  | 'default'
  | 'search'
  | 'filter'
  | 'error'
  | 'folder'
  | 'document'

export interface EmptyStateProps {
  /** Title text */
  title: string
  /** Description text */
  description?: string
  /** Preset style (determines default icon) */
  preset?: EmptyStatePreset
  /** Custom icon component (overrides preset) */
  icon?: React.ElementType
  /** Primary action button */
  action?: {
    label: string
    onClick: () => void
    icon?: React.ElementType
  }
  /** Secondary action button */
  secondaryAction?: {
    label: string
    onClick: () => void
  }
  /** Size variant */
  size?: 'sm' | 'md' | 'lg'
  /** Additional class name */
  className?: string
}

// Preset icon configuration
const presetIcons: Record<EmptyStatePreset, React.ElementType> = {
  default: InboxIcon,
  search: MagnifyingGlassIcon,
  filter: FolderOpenIcon,
  error: ExclamationTriangleIcon,
  folder: FolderOpenIcon,
  document: DocumentIcon,
}

// Size configuration
const sizeConfig = {
  sm: {
    container: 'py-8',
    icon: 'w-10 h-10',
    title: 'text-base',
    description: 'text-sm',
    button: 'px-3 py-1.5 text-sm',
  },
  md: {
    container: 'py-12',
    icon: 'w-12 h-12',
    title: 'text-lg',
    description: 'text-sm',
    button: 'px-4 py-2 text-sm',
  },
  lg: {
    container: 'py-16',
    icon: 'w-16 h-16',
    title: 'text-xl',
    description: 'text-base',
    button: 'px-5 py-2.5 text-base',
  },
}

export function EmptyState({
  title,
  description,
  preset = 'default',
  icon: CustomIcon,
  action,
  secondaryAction,
  size = 'md',
  className,
}: EmptyStateProps) {
  const Icon = CustomIcon || presetIcons[preset]
  const config = sizeConfig[size]
  const ActionIcon = action?.icon || PlusIcon

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center text-center',
        config.container,
        className
      )}
    >
      {/* Icon */}
      <div className="flex items-center justify-center w-20 h-20 mb-4 bg-gray-100 rounded-full">
        <Icon className={cn('text-gray-400', config.icon)} />
      </div>

      {/* Title */}
      <h3
        className={cn(
          'font-semibold text-gray-900',
          config.title
        )}
      >
        {title}
      </h3>

      {/* Description */}
      {description && (
        <p
          className={cn(
            'mt-2 text-gray-500 max-w-sm',
            config.description
          )}
        >
          {description}
        </p>
      )}

      {/* Actions */}
      {(action || secondaryAction) && (
        <div className="flex items-center gap-3 mt-6">
          {action && (
            <button
              type="button"
              onClick={action.onClick}
              className={cn(
                'inline-flex items-center gap-2 font-medium rounded',
                'bg-[#0176D3] text-white hover:bg-[#014486]',
                'shadow-[0_1px_3px_rgba(0,0,0,0.12)] hover:shadow-[0_2px_6px_rgba(0,0,0,0.16)]',
                'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#0176D3]',
                'transition-colors',
                config.button
              )}
            >
              <ActionIcon className="w-4 h-4" />
              {action.label}
            </button>
          )}
          {secondaryAction && (
            <button
              type="button"
              onClick={secondaryAction.onClick}
              className={cn(
                'inline-flex items-center font-medium rounded',
                'text-[#0176D3] bg-white border border-[#0176D3]',
                'hover:bg-[#F4F6F9]',
                'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#0176D3]',
                'transition-colors',
                config.button
              )}
            >
              {secondaryAction.label}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

// Preset empty state components for common use cases
export function NoSearchResults({
  query,
  onClear,
  className,
}: {
  query?: string
  onClear?: () => void
  className?: string
}) {
  return (
    <EmptyState
      preset="search"
      title="No results found"
      description={
        query
          ? `No results match "${query}". Try adjusting your search or filters.`
          : 'Try adjusting your search or filters to find what you are looking for.'
      }
      action={
        onClear
          ? {
              label: 'Clear search',
              onClick: onClear,
              icon: MagnifyingGlassIcon,
            }
          : undefined
      }
      className={className}
    />
  )
}

export function NoFilterResults({
  onClearFilters,
  className,
}: {
  onClearFilters?: () => void
  className?: string
}) {
  return (
    <EmptyState
      preset="filter"
      title="No items match your filters"
      description="Try adjusting or clearing your filters to see more results."
      action={
        onClearFilters
          ? {
              label: 'Clear filters',
              onClick: onClearFilters,
              icon: FolderOpenIcon,
            }
          : undefined
      }
      className={className}
    />
  )
}

export function NoDataAvailable({
  entityName = 'items',
  onAdd,
  className,
}: {
  entityName?: string
  onAdd?: () => void
  className?: string
}) {
  return (
    <EmptyState
      preset="default"
      title={`No ${entityName} yet`}
      description={`Get started by creating your first ${entityName.replace(/s$/, '')}.`}
      action={
        onAdd
          ? {
              label: `Add ${entityName.replace(/s$/, '')}`,
              onClick: onAdd,
            }
          : undefined
      }
      className={className}
    />
  )
}

export function ErrorState({
  title = 'Something went wrong',
  description = 'An error occurred while loading the data. Please try again.',
  onRetry,
  className,
}: {
  title?: string
  description?: string
  onRetry?: () => void
  className?: string
}) {
  return (
    <EmptyState
      preset="error"
      title={title}
      description={description}
      action={
        onRetry
          ? {
              label: 'Try again',
              onClick: onRetry,
              icon: ExclamationTriangleIcon,
            }
          : undefined
      }
      className={className}
    />
  )
}

export default EmptyState
