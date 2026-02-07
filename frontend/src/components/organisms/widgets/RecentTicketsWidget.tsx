/**
 * RecentTicketsWidget Component
 *
 * Displays a list of the 5 most recent tickets with status badges.
 * Fetches data from GET /api/v2/tickets?per_page=5&sort=created_at&order=desc
 */

import { useRecentTickets } from '@/hooks/useDashboard'
import { cn } from '@/utils/cn'
import { formatDistanceToNow } from '@/utils/date'

// Status badge styles - Salesforce Lightning
const statusStyles: Record<string, { bg: string; text: string; label: string }> = {
  NEW: { bg: 'bg-[#0176D3]/10', text: 'text-[#0176D3]', label: 'New' },
  IN_PROGRESS: { bg: 'bg-[#FE9339]/10', text: 'text-[#B86E00]', label: 'In Progress' },
  RESOLVED: { bg: 'bg-[#2E844A]/10', text: 'text-[#2E844A]', label: 'Resolved' },
  RESOLVED_DELIVERED: { bg: 'bg-[#2E844A]/10', text: 'text-[#2E844A]', label: 'Delivered' },
}

// Priority indicator colors - Salesforce Lightning
const priorityColors: Record<string, string> = {
  URGENT: 'bg-[#C23934]',
  HIGH: 'bg-[#FE9339]',
  MEDIUM: 'bg-[#FFB75D]',
  LOW: 'bg-[#2E844A]',
}

export interface RecentTicketsWidgetProps {
  /** Number of tickets to display */
  limit?: number
  /** Click handler to navigate to a specific ticket */
  onTicketClick?: (ticketId: number) => void
  /** Click handler to view all tickets */
  onViewAll?: () => void
  /** Additional CSS classes */
  className?: string
}

export function RecentTicketsWidget({
  limit = 5,
  onTicketClick,
  onViewAll,
  className,
}: RecentTicketsWidgetProps) {
  const { data: tickets, isLoading, isError, error, refetch } = useRecentTickets({
    per_page: limit,
  })

  if (isError) {
    return (
      <div
        className={cn(
          'rounded bg-white p-6 shadow-[0_2px_4px_rgba(0,0,0,0.1)] border border-[#DDDBDA]',
          className
        )}
      >
        <div className="text-center py-4">
          <p className="text-sm text-[#C23934]">Failed to load recent tickets</p>
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

  return (
    <div
      className={cn(
        'rounded bg-white shadow-[0_2px_4px_rgba(0,0,0,0.1)] border border-[#DDDBDA]',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 bg-[#F3F3F3] border-b border-[#DDDBDA]">
        <div className="flex items-center gap-3">
          <div className="rounded bg-[#0176D3]/10 p-2">
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
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
          <h3 className="text-sm font-semibold text-gray-900">Recent Tickets</h3>
        </div>
        {onViewAll && (
          <button
            onClick={onViewAll}
            className="text-sm font-medium text-[#0176D3] hover:text-[#014486]"
          >
            View all
          </button>
        )}
      </div>

      {/* Ticket list */}
      <div className="divide-y divide-[#DDDBDA]">
        {isLoading ? (
          // Loading skeleton
          Array.from({ length: limit }).map((_, i) => (
            <div key={i} className="px-6 py-4">
              <div className="flex items-start justify-between">
                <div className="flex-1 space-y-2">
                  <div className="h-4 w-3/4 animate-pulse rounded bg-gray-200" />
                  <div className="h-3 w-1/2 animate-pulse rounded bg-gray-100" />
                </div>
                <div className="h-6 w-20 animate-pulse rounded-full bg-gray-100" />
              </div>
            </div>
          ))
        ) : tickets && tickets.length > 0 ? (
          tickets.map((ticket) => {
            const status = statusStyles[ticket.status] || statusStyles.NEW
            const priorityColor = priorityColors[ticket.priority] || priorityColors.MEDIUM

            return (
              <div
                key={ticket.id}
                className={cn(
                  'px-6 py-4 transition-colors',
                  onTicketClick && 'cursor-pointer hover:bg-[#F4F6F9]'
                )}
                onClick={() => onTicketClick?.(ticket.id)}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      {/* Priority indicator */}
                      <span
                        className={cn('h-2 w-2 rounded-full flex-shrink-0', priorityColor)}
                        title={ticket.priority}
                      />
                      {/* Ticket ID */}
                      <span className="text-xs font-medium text-gray-500">
                        #{ticket.display_id}
                      </span>
                    </div>
                    {/* Subject */}
                    <p className="mt-1 text-sm font-medium text-gray-900 truncate">
                      {ticket.subject}
                    </p>
                    {/* Customer and time */}
                    <div className="mt-1 flex items-center gap-2 text-xs text-gray-500">
                      {ticket.customer_name && (
                        <>
                          <span>{ticket.customer_name}</span>
                          <span>-</span>
                        </>
                      )}
                      <span>
                        {ticket.created_at
                          ? formatDistanceToNow(new Date(ticket.created_at))
                          : 'Unknown'}
                      </span>
                    </div>
                  </div>
                  {/* Status badge */}
                  <span
                    className={cn(
                      'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium flex-shrink-0',
                      status.bg,
                      status.text
                    )}
                  >
                    {ticket.custom_status || status.label}
                  </span>
                </div>
              </div>
            )
          })
        ) : (
          <div className="px-6 py-8 text-center">
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
                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
              />
            </svg>
            <p className="mt-2 text-sm text-gray-500">No recent tickets</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default RecentTicketsWidget
