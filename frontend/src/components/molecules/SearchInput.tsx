/**
 * SearchInput Component
 *
 * A search input with debouncing, clear button, loading state,
 * and optional suggestions dropdown.
 */

import React, { useState, useRef, useEffect, useCallback } from 'react'
import { Combobox, Transition } from '@headlessui/react'
import { MagnifyingGlassIcon, XMarkIcon } from '@heroicons/react/24/outline'
import { cn } from '../../utils/cn'
import { useDebounce } from '../../hooks/useDebounce'
import { Spinner } from '../atoms/Spinner'

export interface SearchSuggestion {
  id: string | number
  label: string
  description?: string
  icon?: React.ReactNode
  data?: unknown
}

export interface SearchInputProps {
  value?: string
  onChange?: (value: string) => void
  onSearch?: (value: string) => void
  onSelect?: (suggestion: SearchSuggestion) => void
  suggestions?: SearchSuggestion[]
  isLoading?: boolean
  placeholder?: string
  debounceMs?: number
  showClearButton?: boolean
  autoFocus?: boolean
  disabled?: boolean
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

const sizeStyles: Record<NonNullable<SearchInputProps['size']>, string> = {
  sm: 'py-1.5 pl-9 pr-8 text-sm',
  md: 'py-2 pl-10 pr-10 text-base',
  lg: 'py-3 pl-12 pr-12 text-lg',
}

const iconSizeStyles: Record<NonNullable<SearchInputProps['size']>, string> = {
  sm: 'w-4 h-4',
  md: 'w-5 h-5',
  lg: 'w-6 h-6',
}

const iconPositionStyles: Record<NonNullable<SearchInputProps['size']>, string> = {
  sm: 'left-2.5',
  md: 'left-3',
  lg: 'left-4',
}

const clearButtonPositionStyles: Record<NonNullable<SearchInputProps['size']>, string> = {
  sm: 'right-2',
  md: 'right-3',
  lg: 'right-4',
}

export const SearchInput: React.FC<SearchInputProps> = ({
  value: controlledValue,
  onChange,
  onSearch,
  onSelect,
  suggestions = [],
  isLoading = false,
  placeholder = 'Search...',
  debounceMs = 300,
  showClearButton = true,
  autoFocus = false,
  disabled = false,
  size = 'md',
  className,
}) => {
  const [internalValue, setInternalValue] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  // Use controlled or uncontrolled value
  const value = controlledValue !== undefined ? controlledValue : internalValue
  const debouncedValue = useDebounce(value, debounceMs)

  // Handle value changes
  const handleChange = useCallback(
    (newValue: string) => {
      if (controlledValue === undefined) {
        setInternalValue(newValue)
      }
      onChange?.(newValue)
    },
    [controlledValue, onChange]
  )

  // Trigger search on debounced value change
  useEffect(() => {
    onSearch?.(debouncedValue)
  }, [debouncedValue, onSearch])

  // Handle clear
  const handleClear = useCallback(() => {
    handleChange('')
    inputRef.current?.focus()
  }, [handleChange])

  // Handle keyboard events
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Escape') {
        handleClear()
      }
    },
    [handleClear]
  )

  // Handle suggestion selection
  const handleSelect = useCallback(
    (suggestion: SearchSuggestion | null) => {
      if (suggestion) {
        handleChange(suggestion.label)
        onSelect?.(suggestion)
      }
    },
    [handleChange, onSelect]
  )

  const showSuggestions = suggestions.length > 0 && value.length > 0

  if (suggestions.length > 0 || onSelect) {
    // Render with suggestions dropdown
    return (
      <Combobox value={null} onChange={handleSelect} disabled={disabled}>
        <div className={cn('relative', className)}>
          <div className="relative">
            {/* Search icon */}
            <div
              className={cn(
                'absolute top-1/2 -translate-y-1/2',
                'text-gray-400 dark:text-gray-500',
                'pointer-events-none',
                iconPositionStyles[size]
              )}
            >
              {isLoading ? (
                <Spinner size="sm" className={iconSizeStyles[size]} />
              ) : (
                <MagnifyingGlassIcon className={iconSizeStyles[size]} />
              )}
            </div>

            <Combobox.Input
              ref={inputRef}
              value={value}
              onChange={(e) => handleChange(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              autoFocus={autoFocus}
              className={cn(
                'w-full rounded border h-10',
                'bg-white dark:bg-gray-800',
                'text-gray-900 dark:text-gray-100',
                'border-[#DDDBDA] dark:border-gray-600',
                'placeholder:text-gray-400 dark:placeholder:text-gray-500',
                'focus:outline-none focus:ring-2',
                'focus:ring-[#0176D3]/20 focus:border-[#0176D3]',
                'hover:border-[#1B96FF] dark:hover:border-gray-500',
                'disabled:bg-gray-100 dark:disabled:bg-gray-900',
                'disabled:cursor-not-allowed',
                'transition-all duration-200',
                sizeStyles[size]
              )}
            />

            {/* Clear button */}
            {showClearButton && value && (
              <button
                type="button"
                onClick={handleClear}
                className={cn(
                  'absolute top-1/2 -translate-y-1/2',
                  'text-gray-400 hover:text-gray-600',
                  'dark:text-gray-500 dark:hover:text-gray-300',
                  'transition-colors duration-150',
                  clearButtonPositionStyles[size]
                )}
              >
                <XMarkIcon className={iconSizeStyles[size]} />
              </button>
            )}
          </div>

          {/* Suggestions dropdown */}
          <Transition
            show={showSuggestions}
            enter="transition ease-out duration-100"
            enterFrom="transform opacity-0 scale-95"
            enterTo="transform opacity-100 scale-100"
            leave="transition ease-in duration-75"
            leaveFrom="transform opacity-100 scale-100"
            leaveTo="transform opacity-0 scale-95"
          >
            <Combobox.Options
              className={cn(
                'absolute z-50 w-full mt-1',
                'rounded shadow-[0_2px_8px_rgba(0,0,0,0.16)]',
                'bg-white dark:bg-gray-800',
                'border border-[#DDDBDA] dark:border-gray-700',
                'max-h-60 overflow-auto',
                'py-1',
                'focus:outline-none'
              )}
            >
              {suggestions.map((suggestion) => (
                <Combobox.Option
                  key={suggestion.id}
                  value={suggestion}
                  className={({ active }) =>
                    cn(
                      'flex items-center gap-3 px-4 py-2 cursor-pointer',
                      'transition-colors duration-150',
                      active
                        ? 'bg-[#0176D3]/10 dark:bg-[#0176D3]/20'
                        : 'hover:bg-[#F4F6F9] dark:hover:bg-gray-700/50'
                    )
                  }
                >
                  {suggestion.icon && (
                    <span className="w-5 h-5 flex-shrink-0 text-gray-400">
                      {suggestion.icon}
                    </span>
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                      {suggestion.label}
                    </div>
                    {suggestion.description && (
                      <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
                        {suggestion.description}
                      </div>
                    )}
                  </div>
                </Combobox.Option>
              ))}
            </Combobox.Options>
          </Transition>
        </div>
      </Combobox>
    )
  }

  // Simple search input without suggestions
  return (
    <div className={cn('relative', className)}>
      {/* Search icon */}
      <div
        className={cn(
          'absolute top-1/2 -translate-y-1/2',
          'text-gray-400 dark:text-gray-500',
          'pointer-events-none',
          iconPositionStyles[size]
        )}
      >
        {isLoading ? (
          <Spinner size="sm" className={iconSizeStyles[size]} />
        ) : (
          <MagnifyingGlassIcon className={iconSizeStyles[size]} />
        )}
      </div>

      <input
        ref={inputRef}
        type="search"
        value={value}
        onChange={(e) => handleChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        autoFocus={autoFocus}
        disabled={disabled}
        className={cn(
          'w-full rounded border h-10',
          'bg-white dark:bg-gray-800',
          'text-gray-900 dark:text-gray-100',
          'border-[#DDDBDA] dark:border-gray-600',
          'placeholder:text-gray-400 dark:placeholder:text-gray-500',
          'focus:outline-none focus:ring-2',
          'focus:ring-[#0176D3]/20 focus:border-[#0176D3]',
          'hover:border-[#1B96FF] dark:hover:border-gray-500',
          'disabled:bg-gray-100 dark:disabled:bg-gray-900',
          'disabled:cursor-not-allowed',
          'transition-all duration-200',
          // Hide native search cancel button
          '[&::-webkit-search-cancel-button]:hidden',
          sizeStyles[size]
        )}
      />

      {/* Clear button */}
      {showClearButton && value && (
        <button
          type="button"
          onClick={handleClear}
          className={cn(
            'absolute top-1/2 -translate-y-1/2',
            'text-gray-400 hover:text-gray-600',
            'dark:text-gray-500 dark:hover:text-gray-300',
            'transition-colors duration-150',
            clearButtonPositionStyles[size]
          )}
        >
          <XMarkIcon className={iconSizeStyles[size]} />
        </button>
      )}
    </div>
  )
}

SearchInput.displayName = 'SearchInput'
