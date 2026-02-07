/**
 * TicketStatsWidget Component
 *
 * Displays ticket statistics including total count and breakdown by status.
 * Fetches data from GET /api/v2/dashboard/widgets/ticket_stats/data
 */

import { useTicketStats } from '@/hooks/useDashboard'
import { cn } from '@/utils/cn'

// Status badge colors - Salesforce Lightning
const statusColors: Record<string, { bg: string; text: string }> = {
  open: { bg: 'bg-[#0176D3]/10', text: 'text-[#0176D3]' },
  in_progress: { bg: 'bg-[#FE9339]/10', text: 'text-[#B86E00]' },
  resolved: { bg: 'bg-[#2E844A]/10', text: 'text-[#2E844A]' },
}

export interface TicketStatsWidgetProps {
  /** Time period for stats */
  timePeriod?: '7d' | '30d' | '90d'
  /** Whether to show resolved tickets */
  showResolved?: boolean
  /** Click handler to navigate to tickets */
  onNavigate?: () => void
  /** Additional CSS classes */
  className?: string
}

export function TicketStatsWidget({
  timePeriod = '30d',
  showResolved = true,
  onNavigate,
  className,
}: TicketStatsWidgetProps) {
  const { data, isLoading, isError, error, refetch } = useTicketStats({
    time_period: timePeriod,
    show_resolved: showResolved,
  })

  if (isError) {
    return (
      <div
        className={cn(
          'rounded bg-white p-6 shadow-[0_2px_4px_rgba(0,0,0,0.1)] border border-[#DDDBDA]',
          className
        )}
      >
        <div className="text-center">
          <p className="text-sm text-[#C23934]">Failed to load ticket stats</p>
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
          <div className="rounded bg-[#2E844A]/10 p-2.5">
            <svg
              className="h-5 w-5 text-[#2E844A]"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 5v2m0 4v2m0 4v2M5 5a2 2 0 00-2 2v3a2 2 0 110 4v3a2 2 0 002 2h14a2 2 0 002-2v-3a2 2 0 110-4V7a2 2 0 00-2-2H5z"
              />
            </svg>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900">Ticket Overview</h3>
            <p className="text-xs text-gray-500">Last {timePeriod === '7d' ? '7 days' : timePeriod === '90d' ? '90 days' : '30 days'}</p>
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
          <div className="space-y-2">
            <div className="h-6 w-full animate-pulse rounded bg-gray-100" />
            <div className="h-6 w-full animate-pulse rounded bg-gray-100" />
            <div className="h-6 w-full animate-pulse rounded bg-gray-100" />
          </div>
        </div>
      ) : (
        <>
          <p className="text-4xl font-bold text-gray-900 mb-4">
            {stats?.total.toLocaleString() ?? 0}
          </p>

          {/* Status breakdown */}
          <div className="space-y-2">
            <StatusRow
              label="Open"
              value={stats?.open ?? 0}
              total={stats?.total ?? 1}
              colorKey="open"
            />
            <StatusRow
              label="In Progress"
              value={stats?.in_progress ?? 0}
              total={stats?.total ?? 1}
              colorKey="in_progress"
            />
            {showResolved && stats?.resolved !== undefined && (
              <StatusRow
                label="Resolved"
                value={stats.resolved}
                total={stats?.total ?? 1}
                colorKey="resolved"
              />
            )}
          </div>
        </>
      )}
    </div>
  )
}

interface StatusRowProps {
  label: string
  value: number
  total: number
  colorKey: string
}

function StatusRow({ label, value, total, colorKey }: StatusRowProps) {
  const colors = statusColors[colorKey] || statusColors.open
  const percentage = total > 0 ? Math.round((value / total) * 100) : 0

  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <span
          className={cn(
            'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
            colors.bg,
            colors.text
          )}
        >
          {label}
        </span>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-sm font-semibold text-gray-900">{value.toLocaleString()}</span>
        <span className="text-xs text-gray-500">({percentage}%)</span>
      </div>
    </div>
  )
}

export default TicketStatsWidget
