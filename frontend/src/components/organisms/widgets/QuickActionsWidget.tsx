/**
 * QuickActionsWidget Component
 *
 * Displays quick action buttons for common tasks:
 * - New Ticket
 * - Add Asset
 * - Add Customer
 * - Reports
 * - Inventory
 *
 * Actions are permission-aware based on user role.
 */

import { cn } from '@/utils/cn'
import { useAuthStore } from '@/store/auth.store'

// Action button configuration
interface QuickAction {
  id: string
  label: string
  icon: React.ReactNode
  iconColor: string
  permissions?: string[]
}

const allActions: QuickAction[] = [
  {
    id: 'new-ticket',
    label: 'New Ticket',
    iconColor: 'text-[#0176D3]',
    icon: (
      <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
    ),
  },
  {
    id: 'add-asset',
    label: 'Add Asset',
    iconColor: 'text-[#7C41A1]',
    permissions: ['SUPER_ADMIN', 'DEVELOPER', 'COUNTRY_ADMIN'],
    icon: (
      <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
        />
      </svg>
    ),
  },
  {
    id: 'add-customer',
    label: 'Add Customer',
    iconColor: 'text-[#2E844A]',
    permissions: ['SUPER_ADMIN', 'DEVELOPER', 'COUNTRY_ADMIN'],
    icon: (
      <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"
        />
      </svg>
    ),
  },
  {
    id: 'reports',
    label: 'Reports',
    iconColor: 'text-[#FE9339]',
    permissions: ['SUPER_ADMIN', 'DEVELOPER'],
    icon: (
      <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
        />
      </svg>
    ),
  },
  {
    id: 'inventory',
    label: 'Inventory',
    iconColor: 'text-[#057B6B]',
    permissions: ['SUPER_ADMIN', 'DEVELOPER', 'SUPERVISOR', 'COUNTRY_ADMIN'],
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
  const { user } = useAuthStore()
  const userType = user?.user_type || ''

  // Filter actions based on user permissions
  const actions = allActions.filter((action) => {
    if (!action.permissions) return true
    return action.permissions.includes(userType)
  })

  const handleClick = (actionId: string) => {
    onAction?.(actionId)
  }

  return (
    <div
      className={cn(
        'rounded bg-white p-6 shadow-[0_2px_4px_rgba(0,0,0,0.1)] border border-[#DDDBDA]',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="rounded bg-[#FFB75D]/20 p-2.5">
          <svg
            className="h-5 w-5 text-[#B86E00]"
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
        <div>
          <h3 className="text-sm font-semibold text-gray-900">Quick Actions</h3>
          <p className="text-xs text-gray-500">Common tasks</p>
        </div>
      </div>

      {/* Action buttons */}
      {variant === 'grid' ? (
        <div className="grid grid-cols-2 gap-2">
          {actions.map((action) => (
            <button
              type="button"
              key={action.id}
              onClick={() => handleClick(action.id)}
              className={cn(
                'flex flex-col items-center justify-center rounded p-3',
                'border border-[#DDDBDA] transition-all duration-150',
                'hover:border-[#0176D3] hover:shadow-sm',
                'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#0176D3]'
              )}
            >
              <span className={action.iconColor}>{action.icon}</span>
              <span className="mt-1.5 text-xs font-medium text-gray-800">{action.label}</span>
            </button>
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {actions.map((action) => (
            <button
              type="button"
              key={action.id}
              onClick={() => handleClick(action.id)}
              className={cn(
                'flex w-full items-center gap-3 rounded px-3 py-2.5',
                'border border-[#DDDBDA] transition-all duration-150',
                'hover:border-[#0176D3] hover:shadow-sm',
                'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#0176D3]'
              )}
            >
              <span className={action.iconColor}>{action.icon}</span>
              <span className="text-sm font-medium text-gray-800">{action.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default QuickActionsWidget
