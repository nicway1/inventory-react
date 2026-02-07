/**
 * QueueStatsWidget Component
 *
 * Displays queue ticket counts in a grid layout.
 * Fetches data from GET /api/v2/dashboard/widgets/queue_stats/data
 */

import { useWidgetData } from '@/hooks/useDashboard'
import { cn } from '@/utils/cn'

interface QueueData {
  id: number
  name: string
  open_count: number
  total_count: number
}

interface QueueStatsData {
  widget_id: string
  generated_at: string
  values: {
    queues: QueueData[]
  }
}

export interface QueueStatsWidgetProps {
  /** Click handler for navigating to a specific queue */
  onQueueClick?: (queueId: number) => void
  /** Additional CSS classes */
  className?: string
}

export function QueueStatsWidget({
  onQueueClick,
  className,
}: QueueStatsWidgetProps) {
  const { data, isLoading, isError, error, refetch } = useWidgetData<QueueStatsData>(
    'queue_stats'
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
          <p className="text-sm text-[#C23934]">Failed to load queue stats</p>
          <p className="mt-1 text-xs text-gray-500">{error?.message}</p>
          <button
            onClick={() => refetch()}
            className="mt-3 text-sm font-medium text-[#0176D3] hover:text-[#014486]"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  const queues = data?.values?.queues ?? []

  return (
    <div
      className={cn(
        'rounded bg-white p-6 shadow-[0_2px_4px_rgba(0,0,0,0.1)] border border-[#DDDBDA]',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="rounded bg-[#FE9339]/10 p-2.5">
          <svg
            className="h-5 w-5 text-[#FE9339]"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
            />
          </svg>
        </div>
        <div>
          <h3 className="text-sm font-semibold text-gray-900">Queue Overview</h3>
          <p className="text-xs text-gray-500">Open tickets by queue</p>
        </div>
      </div>

      {/* Queue grid */}
      {isLoading ? (
        <div className="grid grid-cols-2 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-20 animate-pulse rounded bg-gray-100" />
          ))}
        </div>
      ) : queues.length > 0 ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {queues.map((queue) => {
            const percentage = queue.total_count > 0
              ? Math.round((queue.open_count / queue.total_count) * 100)
              : 0

            return (
              <div
                key={queue.id}
                onClick={() => onQueueClick?.(queue.id)}
                className={cn(
                  'p-3 rounded border border-[#DDDBDA] transition-all duration-150',
                  onQueueClick && 'cursor-pointer hover:border-[#FE9339] hover:shadow-sm'
                )}
              >
                <div className="text-xs font-semibold text-gray-800 mb-1 truncate">
                  {queue.name}
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold text-[#FE9339]">
                    {queue.open_count}
                  </span>
                  <span className="text-xs text-gray-500">
                    / {queue.total_count}
                  </span>
                </div>
                {/* Progress bar */}
                <div className="mt-2 h-1 bg-gray-200 rounded overflow-hidden">
                  <div
                    className="h-full bg-[#FE9339] transition-all duration-300"
                    style={{ width: `${percentage}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <div className="text-center py-6">
          <p className="text-sm text-gray-500">No queues available</p>
        </div>
      )}
    </div>
  )
}

export default QueueStatsWidget
