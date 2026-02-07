/**
 * PageLayout Component
 *
 * Main page layout template matching Flask TrueLog exactly:
 * - Header (80px) - Logo, Nav, Search, User
 * - TabSystem (44px) - App launcher, Tabs
 * - Main Content (remaining height, scrollable)
 *
 * No sidebar - navigation is handled via tabs and header.
 */

import { type ReactNode, useEffect } from 'react'
import { cn } from '@/utils/cn'
import { Header } from '@/components/organisms/Header'
import { TabSystem } from '@/components/organisms/TabSystem'
import { Breadcrumb, type BreadcrumbItem } from '@/components/molecules/Breadcrumb'
import { useTheme } from '@/providers/ThemeProvider'

interface PageLayoutProps {
  children: ReactNode
  /** Page title displayed in the header area */
  title?: string
  /** Subtitle or description */
  subtitle?: string
  /** Breadcrumb navigation items */
  breadcrumbs?: BreadcrumbItem[]
  /** Action buttons rendered on the right side of the header */
  actions?: ReactNode
  /** Additional class names for the main content area */
  className?: string
  /** Whether to show a full-width layout (no padding) */
  fullWidth?: boolean
  /** Whether to show a loading state */
  isLoading?: boolean
}

export function PageLayout({
  children,
  title,
  subtitle,
  breadcrumbs,
  actions,
  className,
  fullWidth = false,
  isLoading = false,
}: PageLayoutProps) {
  const { resolvedTheme } = useTheme()

  // Apply theme class to body for global styling
  useEffect(() => {
    const body = document.body
    body.classList.remove('light', 'dark', 'liquid-glass')
    body.classList.add(resolvedTheme)
  }, [resolvedTheme])

  return (
    <div className={cn(
      'min-h-screen flex flex-col',
      // Background colors matching Flask TrueLog
      'bg-[#f3f4f6] dark:bg-gray-950'
    )}>
      {/* Header - 80px height, fixed at top */}
      <Header />

      {/* Tab System - 44px height */}
      <TabSystem />

      {/* Main Content Area - Takes remaining height */}
      <main className="flex-1 overflow-auto">
        {/* Page Header with Breadcrumbs, Title, and Actions */}
        {(breadcrumbs || title || actions) && (
          <div className="bg-white dark:bg-gray-900 border-b border-[#dddbda] dark:border-gray-800">
            <div
              className={cn(
                'py-6',
                fullWidth ? 'px-4 sm:px-6' : 'px-4 sm:px-6 lg:px-8'
              )}
            >
              {/* Breadcrumbs */}
              {breadcrumbs && breadcrumbs.length > 0 && (
                <Breadcrumb items={breadcrumbs} className="mb-4" />
              )}

              {/* Title and Actions Row */}
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                {/* Title */}
                {(title || subtitle) && (
                  <div>
                    {title && (
                      <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
                        {title}
                      </h1>
                    )}
                    {subtitle && (
                      <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                        {subtitle}
                      </p>
                    )}
                  </div>
                )}

                {/* Actions */}
                {actions && (
                  <div className="flex items-center gap-3 flex-shrink-0">
                    {actions}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Main Content */}
        <div
          className={cn(
            'py-6',
            fullWidth ? '' : 'px-4 sm:px-6 lg:px-8',
            className
          )}
        >
          {isLoading ? (
            <div className="flex items-center justify-center min-h-[400px]">
              <div className="flex flex-col items-center gap-4">
                {/* Loading Spinner */}
                <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Loading...
                </p>
              </div>
            </div>
          ) : (
            children
          )}
        </div>
      </main>
    </div>
  )
}

/**
 * Simple content wrapper for pages without the full layout.
 * Useful for auth pages or standalone pages.
 */
interface ContentLayoutProps {
  children: ReactNode
  className?: string
}

export function ContentLayout({ children, className }: ContentLayoutProps) {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex flex-col">
      <main className={cn('flex-1', className)}>{children}</main>
    </div>
  )
}
