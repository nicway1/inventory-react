/**
 * Badge Component
 *
 * A badge/tag component for displaying status, labels, and counts.
 * Maps to common ticket and asset statuses in TrueLog.
 */

import React from 'react'
import { cn } from '../../utils/cn'

export interface BadgeProps {
  variant?: 'success' | 'warning' | 'danger' | 'info' | 'neutral'
  size?: 'sm' | 'md'
  dot?: boolean
  children: React.ReactNode
  className?: string
}

const variantStyles: Record<NonNullable<BadgeProps['variant']>, string> = {
  success: cn(
    'bg-[#2E844A]/10 text-[#2E844A]',
    'dark:bg-[#2E844A]/20 dark:text-[#45C65A]'
  ),
  warning: cn(
    'bg-[#FE9339]/10 text-[#B86E00]',
    'dark:bg-[#FE9339]/20 dark:text-[#FE9339]'
  ),
  danger: cn(
    'bg-[#C23934]/10 text-[#C23934]',
    'dark:bg-[#C23934]/20 dark:text-[#F88078]'
  ),
  info: cn(
    'bg-[#0176D3]/10 text-[#0176D3]',
    'dark:bg-[#0176D3]/20 dark:text-[#1B96FF]'
  ),
  neutral: cn(
    'bg-[#706E6B]/10 text-[#706E6B]',
    'dark:bg-gray-700 dark:text-gray-300'
  ),
}

const dotColors: Record<NonNullable<BadgeProps['variant']>, string> = {
  success: 'bg-[#2E844A]',
  warning: 'bg-[#FE9339]',
  danger: 'bg-[#C23934]',
  info: 'bg-[#0176D3]',
  neutral: 'bg-[#706E6B]',
}

const sizeStyles: Record<NonNullable<BadgeProps['size']>, string> = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-sm',
}

export const Badge: React.FC<BadgeProps> = ({
  variant = 'neutral',
  size = 'md',
  dot = false,
  children,
  className,
}) => {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5',
        'font-medium rounded-full',
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
    >
      {dot && (
        <span
          className={cn(
            'w-1.5 h-1.5 rounded-full flex-shrink-0',
            dotColors[variant]
          )}
        />
      )}
      {children}
    </span>
  )
}

Badge.displayName = 'Badge'

/**
 * Status mapping utilities for TrueLog
 */
export type TicketStatus = 'open' | 'in_progress' | 'resolved' | 'closed' | 'on_hold'
export type AssetStatus = 'available' | 'deployed' | 'maintenance' | 'retired' | 'lost'

export const ticketStatusToBadge: Record<TicketStatus, { variant: BadgeProps['variant']; label: string }> = {
  open: { variant: 'info', label: 'New' },
  in_progress: { variant: 'warning', label: 'In Progress' },
  resolved: { variant: 'success', label: 'Resolved' },
  closed: { variant: 'neutral', label: 'Closed' },
  on_hold: { variant: 'warning', label: 'On Hold' },
}

export const assetStatusToBadge: Record<AssetStatus, { variant: BadgeProps['variant']; label: string }> = {
  available: { variant: 'success', label: 'Available' },
  deployed: { variant: 'info', label: 'Deployed' },
  maintenance: { variant: 'warning', label: 'Maintenance' },
  retired: { variant: 'neutral', label: 'Retired' },
  lost: { variant: 'danger', label: 'Lost' },
}

/**
 * Convenience component for ticket status badges
 */
export const TicketStatusBadge: React.FC<{ status: TicketStatus; size?: BadgeProps['size'] }> = ({
  status,
  size = 'md',
}) => {
  const { variant, label } = ticketStatusToBadge[status]
  return (
    <Badge variant={variant} size={size} dot>
      {label}
    </Badge>
  )
}

/**
 * Convenience component for asset status badges
 */
export const AssetStatusBadge: React.FC<{ status: AssetStatus; size?: BadgeProps['size'] }> = ({
  status,
  size = 'md',
}) => {
  const { variant, label } = assetStatusToBadge[status]
  return (
    <Badge variant={variant} size={size} dot>
      {label}
    </Badge>
  )
}
