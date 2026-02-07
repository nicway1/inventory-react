/**
 * Icon Component
 *
 * A wrapper component for @heroicons/react that provides consistent sizing
 * and styling across the application.
 */

import React from 'react'
import { cn } from '../../utils/cn'

export interface IconProps {
  icon: React.ForwardRefExoticComponent<
    Omit<React.SVGProps<SVGSVGElement>, 'ref'> & {
      title?: string
      titleId?: string
    } & React.RefAttributes<SVGSVGElement>
  >
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  className?: string
  label?: string
}

const sizeStyles: Record<NonNullable<IconProps['size']>, string> = {
  xs: 'w-3 h-3',
  sm: 'w-4 h-4',
  md: 'w-5 h-5',
  lg: 'w-6 h-6',
  xl: 'w-8 h-8',
}

export const Icon: React.FC<IconProps> = ({
  icon: IconComponent,
  size = 'md',
  className,
  label,
}) => {
  return (
    <IconComponent
      className={cn(
        'flex-shrink-0',
        sizeStyles[size],
        className
      )}
      aria-hidden={!label}
      aria-label={label}
    />
  )
}

Icon.displayName = 'Icon'

/**
 * Common icon sizes as Tailwind classes for direct use
 */
export const iconSizes = {
  xs: 'w-3 h-3',
  sm: 'w-4 h-4',
  md: 'w-5 h-5',
  lg: 'w-6 h-6',
  xl: 'w-8 h-8',
} as const

/**
 * Icon button wrapper for clickable icons
 */
export interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  icon: IconProps['icon']
  size?: IconProps['size']
  variant?: 'ghost' | 'outline' | 'subtle'
  label: string
}

const buttonVariantStyles: Record<NonNullable<IconButtonProps['variant']>, string> = {
  ghost: cn(
    'hover:bg-[#F4F6F9] dark:hover:bg-gray-800',
    'active:bg-[#EEF1F6] dark:active:bg-gray-700'
  ),
  outline: cn(
    'border border-[#DDDBDA] dark:border-gray-600',
    'hover:bg-[#F4F6F9] dark:hover:bg-gray-800',
    'active:bg-[#EEF1F6] dark:active:bg-gray-700'
  ),
  subtle: cn(
    'text-[#706E6B] hover:text-gray-700',
    'dark:text-gray-400 dark:hover:text-gray-200'
  ),
}

const buttonSizeStyles: Record<NonNullable<IconProps['size']>, string> = {
  xs: 'p-1',
  sm: 'p-1.5',
  md: 'p-2',
  lg: 'p-2.5',
  xl: 'p-3',
}

export const IconButton: React.FC<IconButtonProps> = ({
  icon,
  size = 'md',
  variant = 'ghost',
  label,
  className,
  disabled,
  ...props
}) => {
  return (
    <button
      type="button"
      aria-label={label}
      disabled={disabled}
      className={cn(
        'inline-flex items-center justify-center',
        'rounded transition-colors duration-150',
        'focus:outline-none focus:ring-2 focus:ring-[#0176D3]/50',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        buttonVariantStyles[variant],
        buttonSizeStyles[size],
        className
      )}
      {...props}
    >
      <Icon icon={icon} size={size} />
    </button>
  )
}

IconButton.displayName = 'IconButton'
