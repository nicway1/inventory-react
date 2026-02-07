/**
 * Avatar Component
 *
 * Displays user avatars with image or initials fallback.
 * Supports multiple sizes and optional status indicator.
 */

import React, { useState } from 'react'
import { cn } from '../../utils/cn'

export interface AvatarProps {
  src?: string | null
  alt?: string
  name?: string
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  status?: 'online' | 'offline' | 'away' | 'busy'
  className?: string
}

const sizeStyles: Record<NonNullable<AvatarProps['size']>, string> = {
  xs: 'w-6 h-6 text-xs',
  sm: 'w-8 h-8 text-sm',
  md: 'w-10 h-10 text-base',
  lg: 'w-12 h-12 text-lg',
  xl: 'w-16 h-16 text-xl',
}

const statusSizeStyles: Record<NonNullable<AvatarProps['size']>, string> = {
  xs: 'w-1.5 h-1.5 border',
  sm: 'w-2 h-2 border',
  md: 'w-2.5 h-2.5 border-2',
  lg: 'w-3 h-3 border-2',
  xl: 'w-4 h-4 border-2',
}

const statusColors: Record<NonNullable<AvatarProps['status']>, string> = {
  online: 'bg-[#2E844A]',
  offline: 'bg-[#706E6B]',
  away: 'bg-[#FE9339]',
  busy: 'bg-[#C23934]',
}

// Generate background color from name for consistent colors - Salesforce Lightning
function getColorFromName(name: string): string {
  const colors = [
    'bg-[#0176D3]',
    'bg-[#7C41A1]',
    'bg-[#2E844A]',
    'bg-[#FE9339]',
    'bg-[#C23934]',
    'bg-[#014486]',
    'bg-[#5C2D91]',
  ]

  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }

  return colors[Math.abs(hash) % colors.length]
}

// Get initials from name
function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/)
  if (parts.length >= 2) {
    return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase()
  }
  return name.slice(0, 2).toUpperCase()
}

export const Avatar: React.FC<AvatarProps> = ({
  src,
  alt,
  name = '',
  size = 'md',
  status,
  className,
}) => {
  const [imageError, setImageError] = useState(false)
  const showImage = src && !imageError
  const initials = name ? getInitials(name) : '?'
  const bgColor = getColorFromName(name || 'default')

  return (
    <div className={cn('relative inline-flex flex-shrink-0', className)}>
      {showImage ? (
        <img
          src={src}
          alt={alt || name || 'Avatar'}
          onError={() => setImageError(true)}
          className={cn(
            'rounded-full object-cover',
            sizeStyles[size]
          )}
        />
      ) : (
        <div
          className={cn(
            'rounded-full flex items-center justify-center',
            'font-medium text-white',
            sizeStyles[size],
            bgColor
          )}
          aria-label={alt || name || 'Avatar'}
        >
          {initials}
        </div>
      )}
      {status && (
        <span
          className={cn(
            'absolute bottom-0 right-0 rounded-full',
            'border-white dark:border-gray-900',
            statusSizeStyles[size],
            statusColors[status]
          )}
          aria-label={`Status: ${status}`}
        />
      )}
    </div>
  )
}

Avatar.displayName = 'Avatar'

/**
 * Avatar Group Component
 *
 * Displays a group of avatars with overlap styling.
 */
export interface AvatarGroupProps {
  avatars: Array<Omit<AvatarProps, 'status' | 'size'>>
  size?: AvatarProps['size']
  max?: number
  className?: string
}

export const AvatarGroup: React.FC<AvatarGroupProps> = ({
  avatars,
  size = 'md',
  max = 4,
  className,
}) => {
  const visibleAvatars = avatars.slice(0, max)
  const remainingCount = avatars.length - max

  const overlapStyles: Record<NonNullable<AvatarProps['size']>, string> = {
    xs: '-ml-2',
    sm: '-ml-2.5',
    md: '-ml-3',
    lg: '-ml-4',
    xl: '-ml-5',
  }

  return (
    <div className={cn('flex items-center', className)}>
      {visibleAvatars.map((avatar, index) => (
        <div
          key={index}
          className={cn(
            'ring-2 ring-white dark:ring-gray-900 rounded-full',
            index > 0 && overlapStyles[size]
          )}
        >
          <Avatar {...avatar} size={size} />
        </div>
      ))}
      {remainingCount > 0 && (
        <div
          className={cn(
            'rounded-full flex items-center justify-center',
            'bg-gray-200 dark:bg-gray-700',
            'text-gray-600 dark:text-gray-300',
            'font-medium ring-2 ring-white dark:ring-gray-900',
            sizeStyles[size],
            overlapStyles[size]
          )}
        >
          +{remainingCount}
        </div>
      )}
    </div>
  )
}

AvatarGroup.displayName = 'AvatarGroup'
