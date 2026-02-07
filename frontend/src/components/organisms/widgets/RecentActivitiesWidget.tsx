/**
 * RecentActivitiesWidget Component
 *
 * Displays a list of recent system activities.
 * Shows user, action, and timestamp for each activity.
 * Fetches data from GET /api/v2/dashboard/widgets/recent_activities/data
 */

import { useWidgetData } from '@/hooks/useDashboard'
import { cn } from '@/utils/cn'
import { formatDistanceToNow } from '@/utils/date'

interface Activity {
  id: number
  user_name?: string
  user_id?: number
  content: string
  created_at: string
  type?: string
}

interface RecentActivitiesData {
  widget_id: string
  generated_at: string
  values: {
    activities: Activity[]
  }
}

export interface RecentActivitiesWidgetProps {
  /** Number of activities to display */
  limit?: number
  /** Additional CSS classes */
  className?: string
}

export function RecentActivitiesWidget({
  limit = 5,
  className,
}: RecentActivitiesWidgetProps) {
  const { data, isLoading, isError, error, refetch } = useWidgetData<RecentActivitiesData>(
    'recent_activities',
    { limit }
  )

  if (isError) {
    return (
      <div
        className={cn(
          'rounded bg-white p-6 shadow-[0_2px_4px_rgba(0,0,0,0.1)] border border-[#DDDBDA]',
          className
        )}
      >
        <div className="text-center">
          <p className="text-sm text-[#C23934]">Failed to load recent activities</p>
          <p className="mt-1 text-xs text-gray-500">{error?.message}</p>
          <button
            type="button"
            onClick={() => refetch()}
            className="mt-3 text-sm font-medium text-[#0176D3] hover:text-[#014486]"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  const activities = data?.values?.activities ?? []

  return (
    <div
      className={cn(
        'rounded bg-white p-6 shadow-[0_2px_4px_rgba(0,0,0,0.1)] border border-[#DDDBDA]',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="rounded bg-[#057B6B]/10 p-2.5">
          <svg
            className="h-5 w-5 text-[#057B6B]"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>
        <div>
          <h3 className="text-sm font-semibold text-gray-900">Recent Activities</h3>
          <p className="text-xs text-gray-500">System activity log</p>
        </div>
      </div>

      {/* Activities list */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: limit }).map((_, i) => (
            <div key={i} className="flex items-start gap-3 pb-3 border-b border-gray-100">
              <div className="w-2 h-2 rounded-full bg-gray-200 mt-2 animate-pulse" />
              <div className="flex-1 space-y-2">
                <div className="h-4 w-3/4 animate-pulse rounded bg-gray-100" />
                <div className="h-3 w-1/4 animate-pulse rounded bg-gray-100" />
              </div>
            </div>
          ))}
        </div>
      ) : activities.length > 0 ? (
        <div className="space-y-3">
          {activities.slice(0, limit).map((activity, index) => (
            <div
              key={activity.id || index}
              className={cn(
                'flex items-start gap-3 pb-3',
                index < activities.length - 1 && 'border-b border-gray-100'
              )}
            >
              {/* Activity indicator */}
              <div className="w-2 h-2 rounded-full bg-[#0176D3] mt-2 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-800 leading-relaxed">
                  {activity.content}
                </p>
                <div className="flex items-center gap-2 mt-1">
                  {activity.user_name && (
                    <>
                      <span className="text-xs font-medium text-gray-600">
                        {activity.user_name}
                      </span>
                      <span className="text-gray-300">-</span>
                    </>
                  )}
                  <span className="text-xs text-gray-500">
                    {activity.created_at
                      ? formatDistanceToNow(new Date(activity.created_at))
                      : 'Unknown'}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-6">
          <svg
            className="mx-auto h-12 w-12 text-gray-300"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <p className="mt-2 text-sm text-gray-500">No recent activities</p>
        </div>
      )}
    </div>
  )
}

export default RecentActivitiesWidget
