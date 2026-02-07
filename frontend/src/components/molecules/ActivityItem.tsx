/**
 * ActivityItem Component
 *
 * Displays a single activity log entry with icon, user info,
 * content, and timestamp.
 */

import { Link } from 'react-router-dom'
import {
  PlusCircleIcon,
  PencilIcon,
  TrashIcon,
  UserPlusIcon,
  ArrowPathIcon,
  ChatBubbleLeftIcon,
  PaperClipIcon,
  ArrowRightOnRectangleIcon,
  ArrowLeftOnRectangleIcon,
  ArrowDownTrayIcon,
  ArrowUpTrayIcon,
  Squares2X2Icon,
  ClockIcon,
  ComputerDesktopIcon,
  TicketIcon,
  UserIcon,
  BuildingOfficeIcon,
  FolderIcon,
  TagIcon,
  WrenchScrewdriverIcon,
} from '@heroicons/react/24/outline'
import { Avatar } from '@/components/atoms/Avatar'
import { Badge } from '@/components/atoms/Badge'
import { cn } from '@/utils/cn'
import { formatRelativeTime, formatDateTime } from '@/utils/date'
import type { Activity, ActivityAction, ActivityEntityType, ACTIVITY_TYPES } from '@/types/history'

interface ActivityItemProps {
  activity: Activity
  showUser?: boolean
  showEntity?: boolean
  compact?: boolean
  className?: string
}

/**
 * Get icon component for activity action
 */
function getActionIcon(action?: ActivityAction, type?: string) {
  // Check specific type first
  if (type?.includes('ticket')) return TicketIcon
  if (type?.includes('asset')) return ComputerDesktopIcon
  if (type?.includes('customer')) return UserIcon
  if (type?.includes('user')) return UserIcon
  if (type?.includes('company')) return BuildingOfficeIcon
  if (type?.includes('queue')) return FolderIcon
  if (type?.includes('category')) return TagIcon
  if (type?.includes('accessory')) return WrenchScrewdriverIcon

  // Fall back to action-based icons
  const iconMap: Record<ActivityAction, typeof ClockIcon> = {
    create: PlusCircleIcon,
    update: PencilIcon,
    delete: TrashIcon,
    assign: UserPlusIcon,
    status_change: ArrowPathIcon,
    comment: ChatBubbleLeftIcon,
    attachment: PaperClipIcon,
    login: ArrowRightOnRectangleIcon,
    logout: ArrowLeftOnRectangleIcon,
    export: ArrowDownTrayIcon,
    import: ArrowUpTrayIcon,
    bulk_action: Squares2X2Icon,
  }

  return action ? iconMap[action] || ClockIcon : ClockIcon
}

/**
 * Get color classes for activity action
 */
function getActionColors(action?: ActivityAction, type?: string): { bg: string; text: string; border: string } {
  // Check specific type patterns
  if (type?.includes('created')) {
    return {
      bg: 'bg-green-100 dark:bg-green-900/30',
      text: 'text-green-600 dark:text-green-400',
      border: 'border-green-200 dark:border-green-800',
    }
  }
  if (type?.includes('updated')) {
    return {
      bg: 'bg-blue-100 dark:bg-blue-900/30',
      text: 'text-blue-600 dark:text-blue-400',
      border: 'border-blue-200 dark:border-blue-800',
    }
  }
  if (type?.includes('deleted')) {
    return {
      bg: 'bg-red-100 dark:bg-red-900/30',
      text: 'text-red-600 dark:text-red-400',
      border: 'border-red-200 dark:border-red-800',
    }
  }
  if (type?.includes('assigned')) {
    return {
      bg: 'bg-purple-100 dark:bg-purple-900/30',
      text: 'text-purple-600 dark:text-purple-400',
      border: 'border-purple-200 dark:border-purple-800',
    }
  }
  if (type?.includes('status')) {
    return {
      bg: 'bg-orange-100 dark:bg-orange-900/30',
      text: 'text-orange-600 dark:text-orange-400',
      border: 'border-orange-200 dark:border-orange-800',
    }
  }
  if (type?.includes('comment') || type?.includes('mention')) {
    return {
      bg: 'bg-teal-100 dark:bg-teal-900/30',
      text: 'text-teal-600 dark:text-teal-400',
      border: 'border-teal-200 dark:border-teal-800',
    }
  }
  if (type?.includes('login')) {
    return {
      bg: 'bg-green-100 dark:bg-green-900/30',
      text: 'text-green-600 dark:text-green-400',
      border: 'border-green-200 dark:border-green-800',
    }
  }
  if (type?.includes('logout')) {
    return {
      bg: 'bg-gray-100 dark:bg-gray-700/30',
      text: 'text-gray-600 dark:text-gray-400',
      border: 'border-gray-200 dark:border-gray-700',
    }
  }

  // Fall back to action-based colors
  const colorMap: Record<ActivityAction, { bg: string; text: string; border: string }> = {
    create: {
      bg: 'bg-green-100 dark:bg-green-900/30',
      text: 'text-green-600 dark:text-green-400',
      border: 'border-green-200 dark:border-green-800',
    },
    update: {
      bg: 'bg-blue-100 dark:bg-blue-900/30',
      text: 'text-blue-600 dark:text-blue-400',
      border: 'border-blue-200 dark:border-blue-800',
    },
    delete: {
      bg: 'bg-red-100 dark:bg-red-900/30',
      text: 'text-red-600 dark:text-red-400',
      border: 'border-red-200 dark:border-red-800',
    },
    assign: {
      bg: 'bg-purple-100 dark:bg-purple-900/30',
      text: 'text-purple-600 dark:text-purple-400',
      border: 'border-purple-200 dark:border-purple-800',
    },
    status_change: {
      bg: 'bg-orange-100 dark:bg-orange-900/30',
      text: 'text-orange-600 dark:text-orange-400',
      border: 'border-orange-200 dark:border-orange-800',
    },
    comment: {
      bg: 'bg-teal-100 dark:bg-teal-900/30',
      text: 'text-teal-600 dark:text-teal-400',
      border: 'border-teal-200 dark:border-teal-800',
    },
    attachment: {
      bg: 'bg-cyan-100 dark:bg-cyan-900/30',
      text: 'text-cyan-600 dark:text-cyan-400',
      border: 'border-cyan-200 dark:border-cyan-800',
    },
    login: {
      bg: 'bg-green-100 dark:bg-green-900/30',
      text: 'text-green-600 dark:text-green-400',
      border: 'border-green-200 dark:border-green-800',
    },
    logout: {
      bg: 'bg-gray-100 dark:bg-gray-700/30',
      text: 'text-gray-600 dark:text-gray-400',
      border: 'border-gray-200 dark:border-gray-700',
    },
    export: {
      bg: 'bg-indigo-100 dark:bg-indigo-900/30',
      text: 'text-indigo-600 dark:text-indigo-400',
      border: 'border-indigo-200 dark:border-indigo-800',
    },
    import: {
      bg: 'bg-indigo-100 dark:bg-indigo-900/30',
      text: 'text-indigo-600 dark:text-indigo-400',
      border: 'border-indigo-200 dark:border-indigo-800',
    },
    bulk_action: {
      bg: 'bg-yellow-100 dark:bg-yellow-900/30',
      text: 'text-yellow-600 dark:text-yellow-400',
      border: 'border-yellow-200 dark:border-yellow-800',
    },
  }

  return action
    ? colorMap[action]
    : {
        bg: 'bg-gray-100 dark:bg-gray-700/30',
        text: 'text-gray-600 dark:text-gray-400',
        border: 'border-gray-200 dark:border-gray-700',
      }
}

/**
 * Get entity link for activity
 */
function getEntityLink(activity: Activity): string | null {
  const { entity_type, reference_id } = activity

  if (!reference_id) return null

  // Infer entity type from activity type if not explicitly set
  const type = entity_type || inferEntityType(activity.type)

  switch (type) {
    case 'ticket':
      return `/tickets/${reference_id}`
    case 'asset':
      return `/inventory/assets/${reference_id}`
    case 'customer':
      return `/customers/${reference_id}`
    case 'user':
      return `/admin/users/${reference_id}`
    case 'company':
      return `/admin/companies/${reference_id}`
    case 'queue':
      return `/admin/queues/${reference_id}`
    default:
      return null
  }
}

/**
 * Infer entity type from activity type string
 */
function inferEntityType(type?: string): ActivityEntityType | null {
  if (!type) return null
  if (type.includes('ticket')) return 'ticket'
  if (type.includes('asset')) return 'asset'
  if (type.includes('customer')) return 'customer'
  if (type.includes('user')) return 'user'
  if (type.includes('company')) return 'company'
  if (type.includes('queue')) return 'queue'
  if (type.includes('accessory')) return 'accessory'
  return null
}

/**
 * Format activity type for display
 */
function formatActivityType(type: string): string {
  return type
    .replace(/_/g, ' ')
    .replace(/admin /gi, '')
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
}

/**
 * Infer action from activity type
 */
function inferAction(type?: string): ActivityAction | undefined {
  if (!type) return undefined
  if (type.includes('created')) return 'create'
  if (type.includes('updated')) return 'update'
  if (type.includes('deleted')) return 'delete'
  if (type.includes('assigned')) return 'assign'
  if (type.includes('status')) return 'status_change'
  if (type.includes('comment') || type.includes('mention')) return 'comment'
  if (type.includes('attachment')) return 'attachment'
  if (type.includes('login')) return 'login'
  if (type.includes('logout')) return 'logout'
  if (type.includes('export')) return 'export'
  if (type.includes('import')) return 'import'
  return undefined
}

export function ActivityItem({
  activity,
  showUser = true,
  showEntity = true,
  compact = false,
  className,
}: ActivityItemProps) {
  const action = activity.action || inferAction(activity.type)
  const colors = getActionColors(action, activity.type)
  const Icon = getActionIcon(action, activity.type)
  const entityLink = showEntity ? getEntityLink(activity) : null

  if (compact) {
    return (
      <div className={cn('flex items-start gap-3 py-2', className)}>
        {/* Icon */}
        <div className={cn('w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0', colors.bg)}>
          <Icon className={cn('w-3.5 h-3.5', colors.text)} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <p className="text-sm text-gray-900 dark:text-white truncate">
            {activity.content}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {showUser && activity.user_name && `${activity.user_name} - `}
            {formatRelativeTime(activity.created_at)}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div
      className={cn(
        'flex items-start gap-4 p-4 rounded-lg border bg-white dark:bg-gray-800',
        colors.border,
        className
      )}
    >
      {/* Icon */}
      <div className={cn('w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0', colors.bg)}>
        <Icon className={cn('w-5 h-5', colors.text)} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Header row */}
        <div className="flex items-center gap-2 mb-1">
          {/* Activity type badge */}
          <Badge
            variant="neutral"
            size="sm"
            className={cn('font-medium', colors.text, colors.bg)}
          >
            {formatActivityType(activity.type)}
          </Badge>

          {/* Entity link */}
          {entityLink && (
            <Link
              to={entityLink}
              className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
            >
              View {inferEntityType(activity.type)}
            </Link>
          )}
        </div>

        {/* Content */}
        <p className="text-sm text-gray-900 dark:text-white">
          {activity.content}
        </p>

        {/* Changes list */}
        {activity.changes && activity.changes.length > 0 && (
          <div className="mt-2 pl-3 border-l-2 border-gray-200 dark:border-gray-700">
            {activity.changes.map((change, index) => (
              <div key={index} className="text-xs text-gray-600 dark:text-gray-400 py-0.5">
                <span className="font-medium">{change.field}:</span>{' '}
                <span className="text-red-500 line-through">{String(change.old_value || '-')}</span>
                {' -> '}
                <span className="text-green-600">{String(change.new_value || '-')}</span>
              </div>
            ))}
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center gap-3 mt-2">
          {/* User */}
          {showUser && activity.user_name && (
            <div className="flex items-center gap-2">
              <Avatar name={activity.user_name} size="xs" />
              <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
                {activity.user_name}
              </span>
            </div>
          )}

          {/* Timestamp */}
          <span className="text-xs text-gray-500 dark:text-gray-500" title={formatDateTime(activity.created_at)}>
            {formatRelativeTime(activity.created_at)}
          </span>

          {/* Unread indicator */}
          {!activity.is_read && (
            <span className="w-2 h-2 rounded-full bg-blue-500" title="Unread" />
          )}
        </div>
      </div>
    </div>
  )
}

export default ActivityItem
