/**
 * ActivityTimeline Component
 *
 * Displays a vertical timeline of activity log entries.
 * Can be used standalone or within entity detail pages.
 */

import { Fragment } from 'react'
import { ClockIcon } from '@heroicons/react/24/outline'
import { cn } from '@/utils/cn'
import { formatDate } from '@/utils/date'
import { ActivityItem } from './ActivityItem'
import { Spinner } from '@/components/atoms/Spinner'
import type { Activity } from '@/types/history'

interface ActivityTimelineProps {
  activities: Activity[]
  isLoading?: boolean
  error?: string | null
  showUser?: boolean
  showEntity?: boolean
  compact?: boolean
  groupByDate?: boolean
  maxHeight?: string
  emptyMessage?: string
  className?: string
}

/**
 * Group activities by date
 */
function groupActivitiesByDate(activities: Activity[]): Record<string, Activity[]> {
  const groups: Record<string, Activity[]> = {}

  activities.forEach((activity) => {
    const date = new Date(activity.created_at).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })

    if (!groups[date]) {
      groups[date] = []
    }
    groups[date].push(activity)
  })

  return groups
}

/**
 * Empty state component
 */
function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-center py-12">
      <ClockIcon className="w-12 h-12 mx-auto text-gray-300 dark:text-gray-600 mb-4" />
      <p className="text-sm text-gray-500 dark:text-gray-400">{message}</p>
    </div>
  )
}

/**
 * Error state component
 */
function ErrorState({ error }: { error: string }) {
  return (
    <div className="text-center py-12">
      <div className="w-12 h-12 mx-auto rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center mb-4">
        <ClockIcon className="w-6 h-6 text-red-500 dark:text-red-400" />
      </div>
      <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
    </div>
  )
}

/**
 * Loading state component
 */
function LoadingState() {
  return (
    <div className="flex items-center justify-center py-12">
      <Spinner size="lg" label="Loading activities..." />
    </div>
  )
}

/**
 * Date group header
 */
function DateGroupHeader({ date }: { date: string }) {
  const isToday =
    date ===
    new Date().toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })

  const isYesterday =
    date ===
    new Date(Date.now() - 86400000).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })

  let displayDate = date
  if (isToday) displayDate = 'Today'
  else if (isYesterday) displayDate = 'Yesterday'

  return (
    <div className="sticky top-0 z-10 py-2 px-4 bg-gray-100 dark:bg-gray-900">
      <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
        {displayDate}
      </span>
    </div>
  )
}

export function ActivityTimeline({
  activities,
  isLoading = false,
  error = null,
  showUser = true,
  showEntity = true,
  compact = false,
  groupByDate = false,
  maxHeight,
  emptyMessage = 'No activity yet',
  className,
}: ActivityTimelineProps) {
  if (isLoading) {
    return <LoadingState />
  }

  if (error) {
    return <ErrorState error={error} />
  }

  if (activities.length === 0) {
    return <EmptyState message={emptyMessage} />
  }

  // Group activities by date if requested
  if (groupByDate) {
    const groupedActivities = groupActivitiesByDate(activities)
    const dateGroups = Object.keys(groupedActivities)

    return (
      <div
        className={cn('relative', className)}
        style={{ maxHeight: maxHeight || undefined, overflowY: maxHeight ? 'auto' : undefined }}
      >
        {dateGroups.map((date) => (
          <div key={date}>
            <DateGroupHeader date={date} />
            <div className="space-y-2 px-4 pb-4">
              {groupedActivities[date].map((activity) => (
                <ActivityItem
                  key={activity.id}
                  activity={activity}
                  showUser={showUser}
                  showEntity={showEntity}
                  compact={compact}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    )
  }

  // Simple list without grouping
  return (
    <div
      className={cn('relative', className)}
      style={{ maxHeight: maxHeight || undefined, overflowY: maxHeight ? 'auto' : undefined }}
    >
      {/* Timeline line */}
      {!compact && (
        <div className="absolute left-[1.25rem] top-0 bottom-0 w-0.5 bg-gray-200 dark:bg-gray-700" />
      )}

      {/* Activities */}
      <div className={cn('space-y-3', !compact && 'pl-4')}>
        {activities.map((activity, index) => (
          <div key={activity.id} className="relative">
            {/* Timeline dot */}
            {!compact && (
              <div className="absolute left-0 top-5 w-2.5 h-2.5 rounded-full bg-blue-500 border-2 border-white dark:border-gray-900 -ml-4" />
            )}

            <ActivityItem
              activity={activity}
              showUser={showUser}
              showEntity={showEntity}
              compact={compact}
            />
          </div>
        ))}
      </div>
    </div>
  )
}

/**
 * ActivityTimelineCard - Wrapped version with card styling
 */
interface ActivityTimelineCardProps extends ActivityTimelineProps {
  title?: string
  headerAction?: React.ReactNode
}

export function ActivityTimelineCard({
  title = 'Activity',
  headerAction,
  ...props
}: ActivityTimelineCardProps) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <ClockIcon className="w-5 h-5 text-gray-500 dark:text-gray-400" />
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{title}</h3>
          {props.activities && props.activities.length > 0 && (
            <span className="px-2 py-0.5 text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded-full">
              {props.activities.length}
            </span>
          )}
        </div>
        {headerAction}
      </div>

      {/* Timeline content */}
      <div className="p-4">
        <ActivityTimeline {...props} />
      </div>
    </div>
  )
}

export default ActivityTimeline
