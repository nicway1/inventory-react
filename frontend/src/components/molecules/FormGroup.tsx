/**
 * FormGroup Component
 *
 * A form field wrapper that combines label, input, and error message.
 * Integrates with react-hook-form for validation.
 */

import React from 'react'
import {
  useFormContext,
  Controller,
  type FieldPath,
  type FieldValues,
  type ControllerRenderProps,
} from 'react-hook-form'
import { cn } from '../../utils/cn'
import { Input, type InputProps } from '../atoms/Input'

export interface FormGroupProps<TFieldValues extends FieldValues = FieldValues>
  extends Omit<InputProps, 'name' | 'error' | 'label'> {
  name: FieldPath<TFieldValues>
  label: string
  required?: boolean
  helperText?: string
  className?: string
}

export function FormGroup<TFieldValues extends FieldValues = FieldValues>({
  name,
  label,
  required = false,
  helperText,
  className,
  ...inputProps
}: FormGroupProps<TFieldValues>) {
  const {
    control,
    formState: { errors },
  } = useFormContext<TFieldValues>()

  // Get nested error message
  const getNestedError = (name: string, errors: Record<string, any>): string | undefined => {
    const parts = name.split('.')
    let current = errors

    for (const part of parts) {
      if (current[part] === undefined) return undefined
      current = current[part]
    }

    return current?.message
  }

  const errorMessage = getNestedError(name, errors)

  return (
    <div className={cn('w-full', className)}>
      <Controller
        name={name}
        control={control}
        render={({ field }: { field: ControllerRenderProps<TFieldValues, FieldPath<TFieldValues>> }) => (
          <Input
            {...inputProps}
            {...field}
            label={
              <span>
                {label}
                {required && (
                  <span className="text-[#C23934] ml-1" aria-hidden="true">
                    *
                  </span>
                )}
              </span>
            }
            error={errorMessage}
            helperText={helperText}
            aria-required={required}
          />
        )}
      />
    </div>
  )
}

FormGroup.displayName = 'FormGroup'

/**
 * Standalone FormLabel Component
 */
export interface FormLabelProps {
  htmlFor?: string
  required?: boolean
  children: React.ReactNode
  className?: string
}

export const FormLabel: React.FC<FormLabelProps> = ({
  htmlFor,
  required = false,
  children,
  className,
}) => {
  return (
    <label
      htmlFor={htmlFor}
      className={cn(
        'block text-xs font-medium mb-1.5 uppercase tracking-wide',
        'text-[#706E6B] dark:text-gray-400',
        className
      )}
    >
      {children}
      {required && (
        <span className="text-[#C23934] ml-1" aria-hidden="true">
          *
        </span>
      )}
    </label>
  )
}

FormLabel.displayName = 'FormLabel'

/**
 * Form Error Message Component
 */
export interface FormErrorProps {
  message?: string
  className?: string
}

export const FormError: React.FC<FormErrorProps> = ({ message, className }) => {
  if (!message) return null

  return (
    <p
      className={cn('mt-1.5 text-xs text-[#C23934] dark:text-[#F88078]', className)}
      role="alert"
    >
      {message}
    </p>
  )
}

FormError.displayName = 'FormError'

/**
 * Form Helper Text Component
 */
export interface FormHelperTextProps {
  children: React.ReactNode
  className?: string
}

export const FormHelperText: React.FC<FormHelperTextProps> = ({
  children,
  className,
}) => {
  return (
    <p className={cn('mt-1.5 text-sm text-gray-500 dark:text-gray-400', className)}>
      {children}
    </p>
  )
}

FormHelperText.displayName = 'FormHelperText'

/**
 * Form Section Component - for grouping related form fields
 */
export interface FormSectionProps {
  title?: string
  description?: string
  children: React.ReactNode
  className?: string
}

export const FormSection: React.FC<FormSectionProps> = ({
  title,
  description,
  children,
  className,
}) => {
  return (
    <div className={cn('space-y-4', className)}>
      {(title || description) && (
        <div className="mb-4">
          {title && (
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">
              {title}
            </h3>
          )}
          {description && (
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {description}
            </p>
          )}
        </div>
      )}
      {children}
    </div>
  )
}

FormSection.displayName = 'FormSection'

/**
 * Form Actions Component - for form submit/cancel buttons
 */
export interface FormActionsProps {
  children: React.ReactNode
  className?: string
  align?: 'left' | 'center' | 'right' | 'between'
}

const alignStyles: Record<NonNullable<FormActionsProps['align']>, string> = {
  left: 'justify-start',
  center: 'justify-center',
  right: 'justify-end',
  between: 'justify-between',
}

export const FormActions: React.FC<FormActionsProps> = ({
  children,
  className,
  align = 'right',
}) => {
  return (
    <div
      className={cn(
        'flex items-center gap-3 pt-4',
        'border-t border-[#DDDBDA] dark:border-gray-700',
        alignStyles[align],
        className
      )}
    >
      {children}
    </div>
  )
}

FormActions.displayName = 'FormActions'
