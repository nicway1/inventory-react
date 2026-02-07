/**
 * Breadcrumb Component
 *
 * Navigation breadcrumb following Home > Section > Page pattern.
 * Supports clickable links with current page displayed as text.
 */

import { Link } from 'react-router-dom'
import { HomeIcon, ChevronRightIcon } from '@heroicons/react/20/solid'
import { cn } from '@/utils/cn'

export interface BreadcrumbItem {
  label: string
  href?: string
}

interface BreadcrumbProps {
  items: BreadcrumbItem[]
  className?: string
}

export function Breadcrumb({ items, className }: BreadcrumbProps) {
  return (
    <nav className={cn('flex', className)} aria-label="Breadcrumb">
      <ol className="flex items-center space-x-2">
        {/* Home link */}
        <li>
          <Link
            to="/"
            className="text-[#706E6B] hover:text-[#0176D3] dark:text-gray-500 dark:hover:text-gray-400 transition-colors"
          >
            <HomeIcon className="h-5 w-5 flex-shrink-0" aria-hidden="true" />
            <span className="sr-only">Home</span>
          </Link>
        </li>

        {/* Breadcrumb items */}
        {items.map((item, index) => {
          const isLast = index === items.length - 1

          return (
            <li key={index} className="flex items-center">
              <ChevronRightIcon
                className="h-5 w-5 flex-shrink-0 text-[#DDDBDA] dark:text-gray-600"
                aria-hidden="true"
              />
              {isLast || !item.href ? (
                <span
                  className={cn(
                    'ml-2 text-sm font-medium',
                    isLast
                      ? 'text-gray-700 dark:text-gray-200'
                      : 'text-gray-500 dark:text-gray-400'
                  )}
                  aria-current={isLast ? 'page' : undefined}
                >
                  {item.label}
                </span>
              ) : (
                <Link
                  to={item.href}
                  className="ml-2 text-sm font-medium text-[#706E6B] hover:text-[#0176D3] dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
                >
                  {item.label}
                </Link>
              )}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
