/**
 * Button Component
 *
 * A versatile button component with multiple variants, sizes, and states.
 * Supports loading state, icons, and full-width mode.
 */

import React, { forwardRef } from 'react'
import { cn } from '../../utils/cn'
import { Spinner } from './Spinner'

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost' | 'outline'
  size?: 'sm' | 'md' | 'lg'
  isLoading?: boolean
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
  fullWidth?: boolean
}

const variantStyles: Record<NonNullable<ButtonProps['variant']>, string> = {
  primary: cn(
    'bg-[#0176D3] text-white',
    'hover:bg-[#014486] active:bg-[#013A6B]',
    'shadow-[0_1px_3px_rgba(0,0,0,0.12)]',
    'hover:shadow-[0_2px_6px_rgba(0,0,0,0.16)]',
    'focus:ring-[#0176D3]/50',
    'disabled:bg-[#0176D3]/50'
  ),
  secondary: cn(
    'bg-white text-[#0176D3]',
    'border border-[#0176D3]',
    'hover:bg-[#F4F6F9] active:bg-[#EEF1F6]',
    'focus:ring-[#0176D3]/50',
    'disabled:border-gray-300 disabled:text-gray-400 disabled:bg-white'
  ),
  danger: cn(
    'bg-[#C23934] text-white',
    'hover:bg-[#A61A14] active:bg-[#8E0E08]',
    'shadow-[0_1px_3px_rgba(0,0,0,0.12)]',
    'hover:shadow-[0_2px_6px_rgba(0,0,0,0.16)]',
    'focus:ring-[#C23934]/50',
    'disabled:bg-[#C23934]/50'
  ),
  ghost: cn(
    'bg-transparent text-gray-700 dark:text-gray-200',
    'hover:bg-gray-100 dark:hover:bg-gray-800',
    'active:bg-gray-200 dark:active:bg-gray-700',
    'focus:ring-gray-500/50',
    'disabled:text-gray-400'
  ),
  outline: cn(
    'bg-transparent text-[#0176D3]',
    'border border-[#0176D3]',
    'hover:bg-[#F4F6F9] dark:hover:bg-gray-800',
    'active:bg-[#EEF1F6] dark:active:bg-gray-700',
    'focus:ring-[#0176D3]/50',
    'disabled:border-gray-300 disabled:text-gray-400'
  ),
}

const sizeStyles: Record<NonNullable<ButtonProps['size']>, string> = {
  sm: 'px-4 py-2 text-sm gap-1.5',
  md: 'px-6 py-3 text-sm gap-2',
  lg: 'px-8 py-4 text-base gap-2.5',
}

const iconSizes: Record<NonNullable<ButtonProps['size']>, string> = {
  sm: 'w-4 h-4',
  md: 'w-5 h-5',
  lg: 'w-6 h-6',
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      isLoading = false,
      leftIcon,
      rightIcon,
      fullWidth = false,
      disabled,
      className,
      children,
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || isLoading

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        className={cn(
          // Base styles
          'inline-flex items-center justify-center',
          'font-medium rounded',
          'transition-all duration-200 ease-out',
          'focus:outline-none focus:ring-2 focus:ring-offset-2',
          'disabled:cursor-not-allowed disabled:opacity-60',
          // Variant and size
          variantStyles[variant],
          sizeStyles[size],
          // Full width
          fullWidth && 'w-full',
          className
        )}
        {...props}
      >
        {isLoading ? (
          <>
            <Spinner
              size={size === 'lg' ? 'md' : 'sm'}
              className={cn(iconSizes[size], 'animate-spin')}
            />
            <span className="ml-2">Loading...</span>
          </>
        ) : (
          <>
            {leftIcon && (
              <span className={cn('flex-shrink-0', iconSizes[size])}>
                {leftIcon}
              </span>
            )}
            {children}
            {rightIcon && (
              <span className={cn('flex-shrink-0', iconSizes[size])}>
                {rightIcon}
              </span>
            )}
          </>
        )}
      </button>
    )
  }
)

Button.displayName = 'Button'
