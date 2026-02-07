/**
 * EntityActivityTab Component
 *
 * Reusable component for showing entity-specific activity history.
 * Used in ticket, asset, customer, and user detail pages.
 */

import { useState, useEffect, useCallback } from 'react'
import { ClockIcon, ArrowPathIcon, ChevronLeftIcon, ChevronRightIcon } from '@heroicons/react/24/outline'
import { Button } from '@/components/atoms/Button'
import { Spinner } from '@/components/atoms/Spinner'
import { ActivityTimeline } from './ActivityTimeline'
import { cn } from '@/utils/cn'
import {
  getTicketActivities,
  getAssetActivities,
  getCustomerActivities,
} from '@/services/history.service'
import type { Activity, ActivityEntityType, ActivityListResponse } from '@/types/history'

interface EntityActivityTabProps {
  /** Type of entity */
  entityType: ActivityEntityType
  /** Entity ID */
  entityId: number
  /** Maximum activities to load per page */
  perPage?: number
  /** Show header with title */
  showHeader?: boolean
  /** Compact display mode */
  compact?: boolean
  /** Additional class names */
  className?: string
}

/**
 * Get fetch function based on entity type
 */
function getFetchFunction(
  entityType: ActivityEntityType
): (id: number, params?: { page?: number; per_page?: number }) => Promise<ActivityListResponse> {
  switch (entityType) {
    case 'ticket':
      return getTicketActivities
    case 'asset':
      return getAssetActivities
    case 'customer':
      return getCustomerActivities
    default:
      // Fallback to a generic function that returns empty data
      return async () => ({
        data: [],
        meta: { pagination: { page: 1, per_page: 20, total: 0, total_pages: 0 } },
      })
  }
}

/**
 * Get entity type label
 */
function getEntityLabel(entityType: ActivityEntityType): string {
  const labels: Record<ActivityEntityType, string> = {
    ticket: 'Ticket',
    asset: 'Asset',
    customer: 'Customer',
    user: 'User',
    company: 'Company',
    queue: 'Queue',
    accessory: 'Accessory',
    comment: 'Comment',
    attachment: 'Attachment',
    system: 'System',
  }
  return labels[entityType] || 'Entity'
}

export function EntityActivityTab({
  entityType,
  entityId,
  perPage = 20,
  showHeader = true,
  compact = false,
  className,
}: EntityActivityTabProps) {
  const [activities, setActivities] = useState<Activity[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalCount, setTotalCount] = useState(0)

  const fetchActivities = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      const fetchFn = getFetchFunction(entityType)
      const response = await fetchFn(entityId, { page, per_page: perPage })

      setActivities(response.data)
      setTotalPages(response.meta.pagination.total_pages)
      setTotalCount(response.meta.pagination.total)
    } catch (err: unknown) {
      console.error('Error fetching activities:', err)
      setError((err as Error).message || 'Failed to load activity history')
    } finally {
      setIsLoading(false)
    }
  }, [entityType, entityId, page, perPage])

  useEffect(() => {
    fetchActivities()
  }, [fetchActivities])

  const handleRefresh = () => {
    fetchActivities()
  }

  const handlePrevPage = () => {
    if (page > 1) {
      setPage(page - 1)
    }
  }

  const handleNextPage = () => {
    if (page < totalPages) {
      setPage(page + 1)
    }
  }

  return (
    <div className={cn('', className)}>
      {/* Header */}
      {showHeader && (
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <ClockIcon className="w-5 h-5 text-gray-500 dark:text-gray-400" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              {getEntityLabel(entityType)} Activity
            </h3>
            {totalCount > 0 && (
              <span className="px-2 py-0.5 text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded-full">
                {totalCount}
              </span>
            )}
          </div>

          <Button
            variant="ghost"
            size="sm"
            leftIcon={<ArrowPathIcon className={cn('w-4 h-4', isLoading && 'animate-spin')} />}
            onClick={handleRefresh}
            disabled={isLoading}
          >
            Refresh
          </Button>
        </div>
      )}

      {/* Content */}
      <ActivityTimeline
        activities={activities}
        isLoading={isLoading}
        error={error}
        showUser={true}
        showEntity={false}
        compact={compact}
        emptyMessage={`No activity history for this ${entityType}`}
      />

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <span className="text-sm text-gray-500 dark:text-gray-400">
            Page {page} of {totalPages}
          </span>

          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              leftIcon={<ChevronLeftIcon className="w-4 h-4" />}
              onClick={handlePrevPage}
              disabled={page <= 1 || isLoading}
            >
              Previous
            </Button>
            <Button
              variant="ghost"
              size="sm"
              rightIcon={<ChevronRightIcon className="w-4 h-4" />}
              onClick={handleNextPage}
              disabled={page >= totalPages || isLoading}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

/**
 * TicketActivityTab - Pre-configured for tickets
 */
export function TicketActivityTab(props: Omit<EntityActivityTabProps, 'entityType'>) {
  return <EntityActivityTab entityType="ticket" {...props} />
}

/**
 * AssetActivityTab - Pre-configured for assets
 */
export function AssetActivityTab(props: Omit<EntityActivityTabProps, 'entityType'>) {
  return <EntityActivityTab entityType="asset" {...props} />
}

/**
 * CustomerActivityTab - Pre-configured for customers
 */
export function CustomerActivityTab(props: Omit<EntityActivityTabProps, 'entityType'>) {
  return <EntityActivityTab entityType="customer" {...props} />
}

export default EntityActivityTab
