/**
 * StatsCard Component
 *
 * A simple stat display card with icon, label, value, and optional trend indicator.
 * Supports multiple color variants and click-to-navigate functionality.
 */

import { cn } from '@/utils/cn'
import type { StatsCardVariant, TrendDirection } from '@/types/dashboard'

// Icon components using SVG for better performance
const Icons = {
  box: (
    <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
    </svg>
  ),
  ticket: (
    <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 5v2m0 4v2m0 4v2M5 5a2 2 0 00-2 2v3a2 2 0 110 4v3a2 2 0 002 2h14a2 2 0 002-2v-3a2 2 0 110-4V7a2 2 0 00-2-2H5z" />
    </svg>
  ),
  users: (
    <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
    </svg>
  ),
  chart: (
    <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
    </svg>
  ),
  arrowUp: (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
    </svg>
  ),
  arrowDown: (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
    </svg>
  ),
  minus: (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
    </svg>
  ),
}

// Variant color configurations
const variantStyles: Record<StatsCardVariant, { bg: string; icon: string; text: string }> = {
  blue: {
    bg: 'bg-blue-50',
    icon: 'bg-blue-100 text-blue-600',
    text: 'text-blue-600',
  },
  green: {
    bg: 'bg-green-50',
    icon: 'bg-green-100 text-green-600',
    text: 'text-green-600',
  },
  purple: {
    bg: 'bg-purple-50',
    icon: 'bg-purple-100 text-purple-600',
    text: 'text-purple-600',
  },
  orange: {
    bg: 'bg-orange-50',
    icon: 'bg-orange-100 text-orange-600',
    text: 'text-orange-600',
  },
  red: {
    bg: 'bg-red-50',
    icon: 'bg-red-100 text-red-600',
    text: 'text-red-600',
  },
  cyan: {
    bg: 'bg-cyan-50',
    icon: 'bg-cyan-100 text-cyan-600',
    text: 'text-cyan-600',
  },
  indigo: {
    bg: 'bg-indigo-50',
    icon: 'bg-indigo-100 text-indigo-600',
    text: 'text-indigo-600',
  },
  gray: {
    bg: 'bg-gray-50',
    icon: 'bg-gray-100 text-gray-600',
    text: 'text-gray-600',
  },
}

// Trend indicator colors
const trendColors: Record<TrendDirection, string> = {
  up: 'text-green-600',
  down: 'text-red-600',
  neutral: 'text-gray-500',
}

export interface StatsCardProps {
  /** Display label */
  label: string
  /** Main value to display */
  value: string | number
  /** Icon type to display */
  icon?: 'box' | 'ticket' | 'users' | 'chart'
  /** Custom icon element */
  customIcon?: React.ReactNode
  /** Color variant */
  variant?: StatsCardVariant
  /** Trend direction indicator */
  trend?: TrendDirection
  /** Trend value text (e.g., "+12%") */
  trendValue?: string
  /** Click handler for navigation */
  onClick?: () => void
  /** Additional CSS classes */
  className?: string
  /** Loading state */
  isLoading?: boolean
  /** Subtitle or description */
  subtitle?: string
}

export function StatsCard({
  label,
  value,
  icon,
  customIcon,
  variant = 'blue',
  trend,
  trendValue,
  onClick,
  className,
  isLoading = false,
  subtitle,
}: StatsCardProps) {
  const styles = variantStyles[variant]
  const IconComponent = icon ? Icons[icon] : null

  const content = (
    <div
      className={cn(
        'rounded bg-white p-6 shadow-[0_2px_4px_rgba(0,0,0,0.1)] border border-[#DDDBDA] transition-all duration-200',
        onClick && 'cursor-pointer hover:shadow-[0_4px_8px_rgba(0,0,0,0.15)] hover:border-[#1B96FF]',
        className
      )}
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        {/* Icon */}
        <div className={cn('rounded-lg p-3', styles.icon)}>
          {customIcon || IconComponent}
        </div>

        {/* Trend indicator */}
        {trend && trendValue && (
          <div className={cn('flex items-center gap-1 text-sm font-medium', trendColors[trend])}>
            {trend === 'up' && Icons.arrowUp}
            {trend === 'down' && Icons.arrowDown}
            {trend === 'neutral' && Icons.minus}
            <span>{trendValue}</span>
          </div>
        )}
      </div>

      {/* Value and label */}
      <div className="mt-4">
        {isLoading ? (
          <div className="space-y-2">
            <div className="h-8 w-20 animate-pulse rounded bg-gray-200" />
            <div className="h-4 w-24 animate-pulse rounded bg-gray-100" />
          </div>
        ) : (
          <>
            <p className="text-3xl font-bold text-gray-900">
              {typeof value === 'number' ? value.toLocaleString() : value}
            </p>
            <p className="mt-1 text-sm font-medium text-gray-500">{label}</p>
            {subtitle && (
              <p className="mt-1 text-xs text-gray-400">{subtitle}</p>
            )}
          </>
        )}
      </div>
    </div>
  )

  return content
}

export default StatsCard
