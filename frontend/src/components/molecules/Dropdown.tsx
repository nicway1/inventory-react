/**
 * Dropdown Component
 *
 * A dropdown menu component built with Headless UI.
 * Supports keyboard navigation and animations.
 */

import React, { Fragment } from 'react'
import { Menu, Transition } from '@headlessui/react'
import { ChevronDownIcon } from '@heroicons/react/24/outline'
import { cn } from '../../utils/cn'

export interface DropdownItem {
  key: string
  label: React.ReactNode
  icon?: React.ReactNode
  disabled?: boolean
  danger?: boolean
  onClick?: () => void
}

export interface DropdownProps {
  trigger: React.ReactNode
  items: (DropdownItem | 'divider')[]
  align?: 'left' | 'right'
  width?: 'auto' | 'sm' | 'md' | 'lg' | 'full'
  className?: string
}

const widthStyles: Record<NonNullable<DropdownProps['width']>, string> = {
  auto: 'w-auto min-w-[160px]',
  sm: 'w-40',
  md: 'w-56',
  lg: 'w-72',
  full: 'w-full',
}

export const Dropdown: React.FC<DropdownProps> = ({
  trigger,
  items,
  align = 'right',
  width = 'auto',
  className,
}) => {
  return (
    <Menu as="div" className={cn('relative inline-block text-left', className)}>
      <Menu.Button as={Fragment}>{trigger}</Menu.Button>

      <Transition
        as={Fragment}
        enter="transition ease-out duration-100"
        enterFrom="transform opacity-0 scale-95"
        enterTo="transform opacity-100 scale-100"
        leave="transition ease-in duration-75"
        leaveFrom="transform opacity-100 scale-100"
        leaveTo="transform opacity-0 scale-95"
      >
        <Menu.Items
          className={cn(
            'absolute z-50 mt-2',
            'rounded shadow-[0_2px_8px_rgba(0,0,0,0.16)]',
            'bg-white dark:bg-gray-800',
            'border border-[#DDDBDA] dark:border-gray-700',
            'focus:outline-none',
            'py-1',
            widthStyles[width],
            align === 'right' ? 'right-0 origin-top-right' : 'left-0 origin-top-left'
          )}
        >
          {items.map((item, index) => {
            if (item === 'divider') {
              return (
                <div
                  key={`divider-${index}`}
                  className="my-1 border-t border-gray-200 dark:border-gray-700"
                />
              )
            }

            return (
              <Menu.Item key={item.key} disabled={item.disabled}>
                {({ active }) => (
                  <button
                    type="button"
                    onClick={item.onClick}
                    disabled={item.disabled}
                    className={cn(
                      'w-full flex items-center gap-3 px-4 py-2 text-sm',
                      'transition-colors duration-150',
                      active && !item.danger && 'bg-[#F4F6F9] dark:bg-gray-700',
                      active && item.danger && 'bg-[#C23934]/10 dark:bg-[#C23934]/20',
                      item.danger
                        ? 'text-[#C23934] dark:text-[#F88078]'
                        : 'text-gray-700 dark:text-gray-200',
                      item.disabled && 'opacity-50 cursor-not-allowed'
                    )}
                  >
                    {item.icon && (
                      <span className={cn('w-5 h-5 flex-shrink-0', item.danger && 'text-[#C23934]')}>
                        {item.icon}
                      </span>
                    )}
                    <span className="flex-1 text-left">{item.label}</span>
                  </button>
                )}
              </Menu.Item>
            )
          })}
        </Menu.Items>
      </Transition>
    </Menu>
  )
}

Dropdown.displayName = 'Dropdown'

/**
 * DropdownButton Component
 *
 * A pre-styled button trigger for dropdowns.
 */
export interface DropdownButtonProps {
  children: React.ReactNode
  variant?: 'default' | 'primary' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

const buttonVariantStyles: Record<NonNullable<DropdownButtonProps['variant']>, string> = {
  default: cn(
    'bg-white dark:bg-gray-800',
    'text-gray-700 dark:text-gray-200',
    'border border-[#DDDBDA] dark:border-gray-600',
    'hover:bg-[#F4F6F9] dark:hover:bg-gray-700'
  ),
  primary: cn(
    'bg-[#0176D3] text-white',
    'shadow-[0_1px_3px_rgba(0,0,0,0.12)]',
    'hover:bg-[#014486] hover:shadow-[0_2px_6px_rgba(0,0,0,0.16)]'
  ),
  ghost: cn(
    'text-gray-700 dark:text-gray-200',
    'hover:bg-[#F4F6F9] dark:hover:bg-gray-700'
  ),
}

const buttonSizeStyles: Record<NonNullable<DropdownButtonProps['size']>, string> = {
  sm: 'px-3 py-1.5 text-sm gap-1.5',
  md: 'px-4 py-2 text-base gap-2',
  lg: 'px-5 py-2.5 text-lg gap-2',
}

const iconSizeStyles: Record<NonNullable<DropdownButtonProps['size']>, string> = {
  sm: 'w-4 h-4',
  md: 'w-5 h-5',
  lg: 'w-5 h-5',
}

export const DropdownButton = React.forwardRef<HTMLButtonElement, DropdownButtonProps>(
  ({ children, variant = 'default', size = 'md', className, ...props }, ref) => {
    return (
      <button
        ref={ref}
        type="button"
        className={cn(
          'inline-flex items-center justify-center',
          'rounded font-medium',
          'transition-colors duration-150',
          'focus:outline-none focus:ring-2 focus:ring-[#0176D3]/50',
          buttonVariantStyles[variant],
          buttonSizeStyles[size],
          className
        )}
        {...props}
      >
        {children}
        <ChevronDownIcon className={cn('ml-1', iconSizeStyles[size])} />
      </button>
    )
  }
)

DropdownButton.displayName = 'DropdownButton'

/**
 * Simple Select Dropdown
 *
 * A simplified dropdown for selecting a single value.
 */
export interface SelectDropdownProps {
  value: string
  onChange: (value: string) => void
  options: { value: string; label: string; icon?: React.ReactNode }[]
  placeholder?: string
  disabled?: boolean
  size?: 'sm' | 'md' | 'lg'
  width?: DropdownProps['width']
  className?: string
}

export const SelectDropdown: React.FC<SelectDropdownProps> = ({
  value,
  onChange,
  options,
  placeholder = 'Select...',
  disabled = false,
  size = 'md',
  width = 'auto',
  className,
}) => {
  const selectedOption = options.find((opt) => opt.value === value)

  return (
    <Dropdown
      align="left"
      width={width}
      className={className}
      trigger={
        <DropdownButton size={size} disabled={disabled}>
          {selectedOption?.icon && (
            <span className="w-5 h-5 flex-shrink-0">{selectedOption.icon}</span>
          )}
          <span className={!selectedOption ? 'text-gray-400' : ''}>
            {selectedOption?.label || placeholder}
          </span>
        </DropdownButton>
      }
      items={options.map((option) => ({
        key: option.value,
        label: option.label,
        icon: option.icon,
        onClick: () => onChange(option.value),
      }))}
    />
  )
}

SelectDropdown.displayName = 'SelectDropdown'
