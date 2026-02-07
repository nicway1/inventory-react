/**
 * Select Component
 *
 * A native select dropdown with label, error states, and helper text.
 * Styled to match the Input component.
 */

import React, { forwardRef } from 'react'
import { cn } from '@/utils/cn'

export interface SelectOption {
  value: string | number
  label: string
  disabled?: boolean
}

export interface SelectProps
  extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'children'> {
  label?: React.ReactNode
  error?: string
  helperText?: string
  options: SelectOption[]
  placeholder?: string
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  (
    {
      label,
      error,
      helperText,
      options,
      placeholder,
      className,
      id,
      disabled,
      ...props
    },
    ref
  ) => {
    const selectId = id || props.name

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={selectId}
            className={cn(
              'block text-xs font-medium mb-1.5 uppercase tracking-wide',
              'text-[#706E6B] dark:text-gray-400',
              disabled && 'opacity-60'
            )}
          >
            {label}
          </label>
        )}
        <select
          ref={ref}
          id={selectId}
          disabled={disabled}
          className={cn(
            // Base styles
            'w-full rounded border h-10',
            'px-3 text-sm',
            'transition-all duration-200',
            // Colors
            'bg-white dark:bg-gray-800',
            'text-gray-900 dark:text-gray-100',
            // Border
            error
              ? 'border-[#C23934] dark:border-[#C23934]'
              : 'border-[#DDDBDA] dark:border-gray-600',
            // Focus
            'focus:outline-none focus:ring-2',
            error
              ? 'focus:ring-[#C23934]/20 focus:border-[#C23934]'
              : 'focus:ring-[#0176D3]/20 focus:border-[#0176D3]',
            // Hover
            !error && 'hover:border-[#1B96FF] dark:hover:border-gray-500',
            // Disabled
            'disabled:bg-gray-100 dark:disabled:bg-gray-900',
            'disabled:text-gray-500 disabled:cursor-not-allowed',
            // Appearance
            'appearance-none bg-no-repeat bg-right',
            'cursor-pointer',
            className
          )}
          style={{
            backgroundImage: `url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e")`,
            backgroundPosition: 'right 0.5rem center',
            backgroundSize: '1.5em 1.5em',
            paddingRight: '2.5rem',
          }}
          aria-invalid={!!error}
          aria-describedby={
            error
              ? `${selectId}-error`
              : helperText
              ? `${selectId}-helper`
              : undefined
          }
          {...props}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((option) => (
            <option
              key={option.value}
              value={option.value}
              disabled={option.disabled}
            >
              {option.label}
            </option>
          ))}
        </select>
        {error && (
          <p
            id={`${selectId}-error`}
            className="mt-1.5 text-xs text-[#C23934] dark:text-[#F88078]"
            role="alert"
          >
            {error}
          </p>
        )}
        {helperText && !error && (
          <p
            id={`${selectId}-helper`}
            className="mt-1.5 text-sm text-gray-500 dark:text-gray-400"
          >
            {helperText}
          </p>
        )}
      </div>
    )
  }
)

Select.displayName = 'Select'
