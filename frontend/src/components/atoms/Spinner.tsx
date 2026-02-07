/**
 * Spinner Component
 *
 * A loading spinner with multiple sizes and color variants.
 * Can be displayed inline or as a block element.
 */

import React from 'react'
import { cn } from '../../utils/cn'

export interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  variant?: 'primary' | 'secondary' | 'white' | 'gray'
  display?: 'inline' | 'block'
  className?: string
  label?: string
}

const sizeStyles: Record<NonNullable<SpinnerProps['size']>, string> = {
  sm: 'w-4 h-4 border-2',
  md: 'w-6 h-6 border-2',
  lg: 'w-8 h-8 border-3',
}

const variantStyles: Record<NonNullable<SpinnerProps['variant']>, string> = {
  primary: 'border-[#0176D3] border-t-transparent',
  secondary: 'border-[#706E6B] border-t-transparent',
  white: 'border-white border-t-transparent',
  gray: 'border-[#706E6B] border-t-transparent',
}

export const Spinner: React.FC<SpinnerProps> = ({
  size = 'md',
  variant = 'primary',
  display = 'inline',
  className,
  label = 'Loading',
}) => {
  const spinner = (
    <div
      role="status"
      aria-label={label}
      className={cn(
        'rounded-full animate-spin',
        sizeStyles[size],
        variantStyles[variant],
        className
      )}
    >
      <span className="sr-only">{label}</span>
    </div>
  )

  if (display === 'block') {
    return (
      <div className="flex items-center justify-center p-4">
        {spinner}
      </div>
    )
  }

  return spinner
}

Spinner.displayName = 'Spinner'
