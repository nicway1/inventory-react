/**
 * TextArea Component
 *
 * A multi-line text input with label, error states, and helper text.
 * Styled to match the Input component.
 */

import React, { forwardRef } from 'react'
import { cn } from '@/utils/cn'

export interface TextAreaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: React.ReactNode
  error?: string
  helperText?: string
}

export const TextArea = forwardRef<HTMLTextAreaElement, TextAreaProps>(
  (
    {
      label,
      error,
      helperText,
      className,
      id,
      disabled,
      rows = 4,
      ...props
    },
    ref
  ) => {
    const textAreaId = id || props.name

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={textAreaId}
            className={cn(
              'block text-xs font-medium mb-1.5 uppercase tracking-wide',
              'text-[#706E6B] dark:text-gray-400',
              disabled && 'opacity-60'
            )}
          >
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={textAreaId}
          disabled={disabled}
          rows={rows}
          className={cn(
            // Base styles
            'w-full rounded border',
            'px-3 py-2 text-sm',
            'transition-all duration-200',
            'placeholder:text-gray-400 dark:placeholder:text-gray-500',
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
            // Resize
            'resize-y min-h-[100px]',
            className
          )}
          aria-invalid={!!error}
          aria-describedby={
            error
              ? `${textAreaId}-error`
              : helperText
              ? `${textAreaId}-helper`
              : undefined
          }
          {...props}
        />
        {error && (
          <p
            id={`${textAreaId}-error`}
            className="mt-1.5 text-xs text-[#C23934] dark:text-[#F88078]"
            role="alert"
          >
            {error}
          </p>
        )}
        {helperText && !error && (
          <p
            id={`${textAreaId}-helper`}
            className="mt-1.5 text-sm text-gray-500 dark:text-gray-400"
          >
            {helperText}
          </p>
        )}
      </div>
    )
  }
)

TextArea.displayName = 'TextArea'
