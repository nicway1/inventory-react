/**
 * InventoryStatsWidget Component
 *
 * Displays inventory statistics including total assets and breakdown by type.
 * Fetches data from GET /api/v2/dashboard/widgets/inventory_stats/data
 */

import { useInventoryStats } from '@/hooks/useDashboard'
import { cn } from '@/utils/cn'

export interface InventoryStatsWidgetProps {
  /** Click handler to navigate to inventory */
  onNavigate?: () => void
  /** Additional CSS classes */
  className?: string
}

export function InventoryStatsWidget({
  onNavigate,
  className,
}: InventoryStatsWidgetProps) {
  const { data, isLoading, isError, error, refetch } = useInventoryStats()

  if (isError) {
    return (
      <div
        className={cn(
          'rounded bg-white p-6 shadow-[0_2px_4px_rgba(0,0,0,0.1)] border border-[#DDDBDA]',
          className
        )}
      >
        <div className="text-center">
          <p className="text-sm text-[#C23934]">Failed to load inventory stats</p>
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
          <div className="rounded bg-[#7C41A1]/10 p-2.5">
            <svg
              className="h-5 w-5 text-[#7C41A1]"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"
              />
            </svg>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900">Inventory Overview</h3>
            <p className="text-xs text-gray-500">All assets</p>
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
          <div className="grid grid-cols-2 gap-4">
            <div className="h-16 animate-pulse rounded bg-gray-100" />
            <div className="h-16 animate-pulse rounded bg-gray-100" />
          </div>
        </div>
      ) : (
        <>
          <p className="text-4xl font-bold text-gray-900 mb-4">
            {stats?.total.toLocaleString() ?? 0}
          </p>

          {/* Type breakdown */}
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded bg-[#0176D3]/10 p-3">
              <div className="flex items-center gap-2 mb-1">
                <svg
                  className="h-4 w-4 text-[#0176D3]"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                  />
                </svg>
                <span className="text-xs font-medium text-[#0176D3]">Tech Assets</span>
              </div>
              <p className="text-xl font-bold text-[#014486]">
                {stats?.tech_assets.toLocaleString() ?? 0}
              </p>
            </div>

            <div className="rounded bg-[#FE9339]/10 p-3">
              <div className="flex items-center gap-2 mb-1">
                <svg
                  className="h-4 w-4 text-[#FE9339]"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"
                  />
                </svg>
                <span className="text-xs font-medium text-[#B86E00]">Accessories</span>
              </div>
              <p className="text-xl font-bold text-[#8B5500]">
                {stats?.accessories.toLocaleString() ?? 0}
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default InventoryStatsWidget
