/**
 * Input Component
 *
 * A flexible input component with support for labels, icons, error states,
 * and helper text. Includes dark mode support.
 */

import React, { forwardRef } from 'react'
import { cn } from '../../utils/cn'

export interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  type?: 'text' | 'email' | 'password' | 'number' | 'search' | 'tel'
  label?: React.ReactNode
  error?: string
  helperText?: string
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      type = 'text',
      label,
      error,
      helperText,
      leftIcon,
      rightIcon,
      className,
      id,
      disabled,
      ...props
    },
    ref
  ) => {
    const inputId = id || props.name

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={inputId}
            className={cn(
              'block text-xs font-medium mb-1.5 uppercase tracking-wide',
              'text-[#706E6B] dark:text-gray-400',
              disabled && 'opacity-60'
            )}
          >
            {label}
          </label>
        )}
        <div className="relative">
          {leftIcon && (
            <div
              className={cn(
                'absolute left-3 top-1/2 -translate-y-1/2',
                'text-gray-400 dark:text-gray-500',
                'pointer-events-none',
                'w-5 h-5'
              )}
            >
              {leftIcon}
            </div>
          )}
          <input
            ref={ref}
            id={inputId}
            type={type}
            disabled={disabled}
            className={cn(
              // Base styles - Salesforce Lightning height (40px = h-10)
              'w-full rounded border h-10',
              'px-3 text-sm',
              'transition-all duration-200',
              'placeholder:text-gray-400 dark:placeholder:text-gray-500',
              // Colors
              'bg-white dark:bg-gray-800',
              'text-gray-900 dark:text-gray-100',
              // Border - Salesforce #DDDBDA
              error
                ? 'border-[#C23934] dark:border-[#C23934]'
                : 'border-[#DDDBDA] dark:border-gray-600',
              // Focus - Salesforce blue glow
              'focus:outline-none focus:ring-2',
              error
                ? 'focus:ring-[#C23934]/20 focus:border-[#C23934]'
                : 'focus:ring-[#0176D3]/20 focus:border-[#0176D3]',
              // Hover
              !error && 'hover:border-[#1B96FF] dark:hover:border-gray-500',
              // Disabled
              'disabled:bg-gray-100 dark:disabled:bg-gray-900',
              'disabled:text-gray-500 disabled:cursor-not-allowed',
              // Icon padding
              leftIcon && 'pl-10',
              rightIcon && 'pr-10',
              className
            )}
            aria-invalid={!!error}
            aria-describedby={
              error
                ? `${inputId}-error`
                : helperText
                ? `${inputId}-helper`
                : undefined
            }
            {...props}
          />
          {rightIcon && (
            <div
              className={cn(
                'absolute right-3 top-1/2 -translate-y-1/2',
                'text-gray-400 dark:text-gray-500',
                'w-5 h-5'
              )}
            >
              {rightIcon}
            </div>
          )}
        </div>
        {error && (
          <p
            id={`${inputId}-error`}
            className="mt-1.5 text-xs text-[#C23934] dark:text-[#F88078]"
            role="alert"
          >
            {error}
          </p>
        )}
        {helperText && !error && (
          <p
            id={`${inputId}-helper`}
            className="mt-1.5 text-sm text-gray-500 dark:text-gray-400"
          >
            {helperText}
          </p>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'
