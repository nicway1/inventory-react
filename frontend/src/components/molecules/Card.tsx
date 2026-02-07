/**
 * Card Component
 *
 * A flexible card component with header, body, and footer slots.
 * Supports SF-style glass effect design and hover states.
 */

import React from 'react'
import { cn } from '../../utils/cn'

export interface CardProps {
  children: React.ReactNode
  className?: string
  padding?: 'none' | 'sm' | 'md' | 'lg'
  variant?: 'default' | 'glass' | 'outlined'
  hoverable?: boolean
  onClick?: () => void
}

const paddingStyles: Record<NonNullable<CardProps['padding']>, string> = {
  none: '',
  sm: 'p-3',
  md: 'p-4',
  lg: 'p-6',
}

const variantStyles: Record<NonNullable<CardProps['variant']>, string> = {
  default: cn(
    'bg-white dark:bg-gray-800',
    'border border-[#DDDBDA] dark:border-gray-700',
    'shadow-[0_2px_4px_rgba(0,0,0,0.1)]'
  ),
  glass: cn(
    'bg-white/80 dark:bg-gray-800/80',
    'backdrop-blur-glass',
    'border border-white/20 dark:border-gray-700/50',
    'shadow-[0_2px_4px_rgba(0,0,0,0.1)]'
  ),
  outlined: cn(
    'bg-transparent',
    'border border-[#DDDBDA] dark:border-gray-700'
  ),
}

export const Card: React.FC<CardProps> = ({
  children,
  className,
  padding = 'md',
  variant = 'default',
  hoverable = false,
  onClick,
}) => {
  const Component = onClick ? 'button' : 'div'

  return (
    <Component
      onClick={onClick}
      className={cn(
        'rounded',
        variantStyles[variant],
        paddingStyles[padding],
        hoverable && [
          'transition-all duration-200',
          'hover:shadow-md dark:hover:shadow-lg',
          variant === 'glass' && 'hover:shadow-glass-hover',
          'hover:border-gray-300 dark:hover:border-gray-600',
        ],
        onClick && [
          'cursor-pointer w-full text-left',
          'focus:outline-none focus:ring-2 focus:ring-[#0176D3]/50',
        ],
        className
      )}
    >
      {children}
    </Component>
  )
}

Card.displayName = 'Card'

/**
 * Card Header Component
 */
export interface CardHeaderProps {
  children: React.ReactNode
  className?: string
  action?: React.ReactNode
}

export const CardHeader: React.FC<CardHeaderProps> = ({
  children,
  className,
  action,
}) => {
  return (
    <div
      className={cn(
        'flex items-center justify-between',
        'px-4 py-3 -mx-4 -mt-4 mb-4 rounded-t',
        'bg-[#F3F3F3] dark:bg-gray-800',
        'border-b border-[#DDDBDA] dark:border-gray-700',
        className
      )}
    >
      <div className="font-semibold text-gray-900 dark:text-white text-sm">
        {children}
      </div>
      {action && <div className="flex-shrink-0 ml-4">{action}</div>}
    </div>
  )
}

CardHeader.displayName = 'CardHeader'

/**
 * Card Body Component
 */
export interface CardBodyProps {
  children: React.ReactNode
  className?: string
}

export const CardBody: React.FC<CardBodyProps> = ({ children, className }) => {
  return (
    <div className={cn('py-4', className)}>
      {children}
    </div>
  )
}

CardBody.displayName = 'CardBody'

/**
 * Card Footer Component
 */
export interface CardFooterProps {
  children: React.ReactNode
  className?: string
  align?: 'left' | 'center' | 'right' | 'between'
}

const alignStyles: Record<NonNullable<CardFooterProps['align']>, string> = {
  left: 'justify-start',
  center: 'justify-center',
  right: 'justify-end',
  between: 'justify-between',
}

export const CardFooter: React.FC<CardFooterProps> = ({
  children,
  className,
  align = 'right',
}) => {
  return (
    <div
      className={cn(
        'flex items-center gap-3',
        'pt-4 border-t border-[#DDDBDA] dark:border-gray-700',
        alignStyles[align],
        className
      )}
    >
      {children}
    </div>
  )
}

CardFooter.displayName = 'CardFooter'

/**
 * Card Title Component
 */
export interface CardTitleProps {
  children: React.ReactNode
  className?: string
  as?: 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6'
}

export const CardTitle: React.FC<CardTitleProps> = ({
  children,
  className,
  as: Component = 'h3',
}) => {
  return (
    <Component
      className={cn(
        'text-lg font-semibold text-gray-900 dark:text-white',
        className
      )}
    >
      {children}
    </Component>
  )
}

CardTitle.displayName = 'CardTitle'

/**
 * Card Description Component
 */
export interface CardDescriptionProps {
  children: React.ReactNode
  className?: string
}

export const CardDescription: React.FC<CardDescriptionProps> = ({
  children,
  className,
}) => {
  return (
    <p className={cn('text-sm text-gray-500 dark:text-gray-400 mt-1', className)}>
      {children}
    </p>
  )
}

CardDescription.displayName = 'CardDescription'
