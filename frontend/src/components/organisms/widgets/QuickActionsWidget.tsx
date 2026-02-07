/**
 * QuickActionsWidget Component
 *
 * Displays quick action buttons for common tasks:
 * - Create Ticket
 * - Create Asset
 * - Scan QR
 * - Search
 */

import { cn } from '@/utils/cn'

// Action button configuration
interface QuickAction {
  id: string
  label: string
  icon: React.ReactNode
  color: string
  hoverColor: string
}

const actions: QuickAction[] = [
  {
    id: 'create-ticket',
    label: 'Create Ticket',
    color: 'bg-green-100 text-green-600',
    hoverColor: 'hover:bg-green-200',
    icon: (
      <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 6v6m0 0v6m0-6h6m-6 0H6"
        />
      </svg>
    ),
  },
  {
    id: 'create-asset',
    label: 'Create Asset',
    color: 'bg-purple-100 text-purple-600',
    hoverColor: 'hover:bg-purple-200',
    icon: (
      <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"
        />
      </svg>
    ),
  },
  {
    id: 'scan-qr',
    label: 'Scan QR',
    color: 'bg-blue-100 text-blue-600',
    hoverColor: 'hover:bg-blue-200',
    icon: (
      <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1zm12 0h2a1 1 0 001-1V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2a1 1 0 001 1zM5 20h2a1 1 0 001-1v-2a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z"
        />
      </svg>
    ),
  },
  {
    id: 'search',
    label: 'Search',
    color: 'bg-orange-100 text-orange-600',
    hoverColor: 'hover:bg-orange-200',
    icon: (
      <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
        />
      </svg>
    ),
  },
]

export interface QuickActionsWidgetProps {
  /** Handler for action button clicks */
  onAction?: (actionId: string) => void
  /** Additional CSS classes */
  className?: string
  /** Layout variant */
  variant?: 'grid' | 'list'
}

export function QuickActionsWidget({
  onAction,
  className,
  variant = 'grid',
}: QuickActionsWidgetProps) {
  const handleClick = (actionId: string) => {
    onAction?.(actionId)
  }

  return (
    <div
      className={cn(
        'rounded-xl bg-white p-6 shadow-sm border border-gray-100',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="rounded-lg bg-yellow-100 p-2.5">
          <svg
            className="h-5 w-5 text-yellow-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 10V3L4 14h7v7l9-11h-7z"
            />
          </svg>
        </div>
        <h3 className="text-sm font-semibold text-gray-900">Quick Actions</h3>
      </div>

      {/* Action buttons */}
      {variant === 'grid' ? (
        <div className="grid grid-cols-2 gap-3">
          {actions.map((action) => (
            <button
              key={action.id}
              onClick={() => handleClick(action.id)}
              className={cn(
                'flex flex-col items-center justify-center rounded-lg p-4 transition-all duration-200',
                action.color,
                action.hoverColor,
                'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
              )}
            >
              {action.icon}
              <span className="mt-2 text-xs font-medium">{action.label}</span>
            </button>
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {actions.map((action) => (
            <button
              key={action.id}
              onClick={() => handleClick(action.id)}
              className={cn(
                'flex w-full items-center gap-3 rounded-lg px-4 py-3 transition-all duration-200',
                action.color,
                action.hoverColor,
                'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
              )}
            >
              {action.icon}
              <span className="text-sm font-medium">{action.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default QuickActionsWidget
