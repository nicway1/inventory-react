/**
 * CustomerStatsWidget Component
 *
 * Displays customer statistics with total count.
 * Fetches data from GET /api/v2/dashboard/widgets/customer_stats/data
 */

import { useWidgetData } from '@/hooks/useDashboard'
import { cn } from '@/utils/cn'

interface CustomerStatsData {
  widget_id: string
  generated_at: string
  values: {
    total: number
  }
}

export interface CustomerStatsWidgetProps {
  /** Click handler to navigate to customers */
  onNavigate?: () => void
  /** Additional CSS classes */
  className?: string
}

export function CustomerStatsWidget({
  onNavigate,
  className,
}: CustomerStatsWidgetProps) {
  const { data, isLoading, isError, error, refetch } = useWidgetData<CustomerStatsData>(
    'customer_stats'
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
          <p className="text-sm text-[#C23934]">Failed to load customer stats</p>
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

  const stats = data?.values

  return (
    <div
      className={cn(
        'rounded bg-white p-6 shadow-[0_2px_4px_rgba(0,0,0,0.1)] border border-[#DDDBDA] transition-all duration-200',
        onNavigate && 'cursor-pointer hover:shadow-[0_4px_8px_rgba(0,0,0,0.15)] hover:border-[#1B96FF]',
        className
      )}
      onClick={(e) => {
        if (onNavigate) {
          e.preventDefault()
          onNavigate()
        }
      }}
      onKeyDown={(e) => {
        if (onNavigate && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault()
          onNavigate()
        }
      }}
      role={onNavigate ? 'button' : undefined}
      tabIndex={onNavigate ? 0 : undefined}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="rounded bg-[#0176D3]/10 p-2.5">
            <svg
              className="h-5 w-5 text-[#0176D3]"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"
              />
            </svg>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900">Customer Overview</h3>
            <p className="text-xs text-gray-500">Registered customers</p>
          </div>
        </div>
        {onNavigate && (
          <svg
            className="h-5 w-5 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        )}
      </div>

      {/* Total count */}
      {isLoading ? (
        <div className="space-y-3">
          <div className="h-10 w-24 animate-pulse rounded bg-gray-200" />
          <div className="h-4 w-32 animate-pulse rounded bg-gray-100" />
        </div>
      ) : (
        <>
          <p className="text-4xl font-bold text-[#0176D3] mb-2">
            {stats?.total.toLocaleString() ?? 0}
          </p>
          <p className="text-sm text-gray-500">Registered Customers</p>
          {onNavigate && (
            <div className="mt-4 flex items-center gap-1 text-sm font-medium text-[#0176D3]">
              <span>Manage Customers</span>
              <svg
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default CustomerStatsWidget
