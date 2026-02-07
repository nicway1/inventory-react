/**
 * NotificationItem Component
 *
 * Displays a single notification with actions.
 * Features:
 * - Different icons based on notification type
 * - Read/unread visual states
 * - Time ago display
 * - Click to navigate to reference
 * - Mark as read/unread action
 * - Delete action
 */

import { memo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  AtSymbolIcon,
  TicketIcon,
  ArchiveBoxIcon,
  BellAlertIcon,
  UserGroupIcon,
  CheckIcon,
  TrashIcon,
  EnvelopeIcon,
  EnvelopeOpenIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils/cn'
import type { Notification, NotificationType } from '@/services/notifications.service'

// Props interface
interface NotificationItemProps {
  notification: Notification
  onMarkAsRead?: (id: number) => void
  onMarkAsUnread?: (id: number) => void
  onDelete?: (id: number) => void
  showActions?: boolean
  compact?: boolean
}

// Icon mapping by notification type
const typeIcons: Record<NotificationType, React.ComponentType<{ className?: string }>> = {
  mention: AtSymbolIcon,
  group_mention: UserGroupIcon,
  ticket_assigned: TicketIcon,
  ticket_updated: TicketIcon,
  asset_checkout: ArchiveBoxIcon,
  asset_checkin: ArchiveBoxIcon,
  system: BellAlertIcon,
}

// Color mapping by notification type
const typeColors: Record<NotificationType, string> = {
  mention: 'text-blue-500 bg-blue-100 dark:bg-blue-900/30',
  group_mention: 'text-purple-500 bg-purple-100 dark:bg-purple-900/30',
  ticket_assigned: 'text-orange-500 bg-orange-100 dark:bg-orange-900/30',
  ticket_updated: 'text-cyan-500 bg-cyan-100 dark:bg-cyan-900/30',
  asset_checkout: 'text-green-500 bg-green-100 dark:bg-green-900/30',
  asset_checkin: 'text-teal-500 bg-teal-100 dark:bg-teal-900/30',
  system: 'text-gray-500 bg-gray-100 dark:bg-gray-700',
}

// Format relative time
function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSecs = Math.floor(diffMs / 1000)
  const diffMins = Math.floor(diffSecs / 60)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffSecs < 60) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`

  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
  })
}

// Get navigation path for notification
function getNavigationPath(notification: Notification): string | null {
  if (!notification.reference_type || !notification.reference_id) {
    return null
  }

  switch (notification.reference_type) {
    case 'ticket':
      return `/tickets/${notification.reference_id}`
    case 'asset':
      return `/inventory/${notification.reference_id}`
    default:
      return null
  }
}

export const NotificationItem = memo(function NotificationItem({
  notification,
  onMarkAsRead,
  onMarkAsUnread,
  onDelete,
  showActions = true,
  compact = false,
}: NotificationItemProps) {
  const navigate = useNavigate()

  const Icon = typeIcons[notification.type] || BellAlertIcon
  const iconColorClass = typeColors[notification.type] || typeColors.system
  const navigationPath = getNavigationPath(notification)

  // Handle click on notification
  const handleClick = useCallback(() => {
    // Mark as read if unread
    if (!notification.is_read && onMarkAsRead) {
      onMarkAsRead(notification.id)
    }

    // Navigate if there's a reference
    if (navigationPath) {
      navigate(navigationPath)
    }
  }, [notification, onMarkAsRead, navigationPath, navigate])

  // Handle mark as read
  const handleMarkAsRead = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation()
      onMarkAsRead?.(notification.id)
    },
    [notification.id, onMarkAsRead]
  )

  // Handle mark as unread
  const handleMarkAsUnread = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation()
      onMarkAsUnread?.(notification.id)
    },
    [notification.id, onMarkAsUnread]
  )

  // Handle delete
  const handleDelete = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation()
      onDelete?.(notification.id)
    },
    [notification.id, onDelete]
  )

  return (
    <div
      className={cn(
        'group flex items-start gap-3 p-3 rounded-lg transition-colors cursor-pointer',
        notification.is_read
          ? 'bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-750'
          : 'bg-blue-50 dark:bg-blue-900/20 hover:bg-blue-100/50 dark:hover:bg-blue-900/30',
        compact ? 'p-2' : 'p-3'
      )}
      onClick={handleClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          handleClick()
        }
      }}
    >
      {/* Icon */}
      <div
        className={cn(
          'flex-shrink-0 p-2 rounded-full',
          iconColorClass,
          compact ? 'p-1.5' : 'p-2'
        )}
      >
        <Icon className={cn('w-5 h-5', compact && 'w-4 h-4')} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Title */}
        <p
          className={cn(
            'text-sm font-medium text-gray-900 dark:text-white truncate',
            !notification.is_read && 'font-semibold'
          )}
        >
          {notification.title}
        </p>

        {/* Message - hide in compact mode */}
        {!compact && (
          <p className="mt-0.5 text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
            {notification.message}
          </p>
        )}

        {/* Time */}
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-500">
          {formatTimeAgo(notification.created_at)}
        </p>
      </div>

      {/* Unread indicator */}
      {!notification.is_read && (
        <div className="flex-shrink-0 w-2 h-2 mt-2 rounded-full bg-blue-500" />
      )}

      {/* Actions - show on hover */}
      {showActions && (
        <div className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1">
          {notification.is_read ? (
            <button
              onClick={handleMarkAsUnread}
              className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
              title="Mark as unread"
            >
              <EnvelopeIcon className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={handleMarkAsRead}
              className="p-1.5 text-gray-400 hover:text-green-600 dark:hover:text-green-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
              title="Mark as read"
            >
              <CheckIcon className="w-4 h-4" />
            </button>
          )}

          <button
            onClick={handleDelete}
            className="p-1.5 text-gray-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
            title="Delete"
          >
            <TrashIcon className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  )
})

export default NotificationItem
