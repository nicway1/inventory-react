/**
 * AdminLayout Component
 *
 * Layout template for admin pages with sidebar navigation.
 * Provides navigation between admin sections and consistent styling.
 */

import { type ReactNode } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  HomeIcon,
  UsersIcon,
  BuildingOfficeIcon,
  QueueListIcon,
  Cog6ToothIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils/cn'
import { PageLayout } from './PageLayout'

interface AdminLayoutProps {
  children: ReactNode
  title?: string
  subtitle?: string
  actions?: ReactNode
}

interface NavItem {
  name: string
  href: string
  icon: React.ComponentType<{ className?: string }>
}

const adminNavItems: NavItem[] = [
  { name: 'Dashboard', href: '/admin', icon: HomeIcon },
  { name: 'Users', href: '/admin/users', icon: UsersIcon },
  { name: 'Companies', href: '/admin/companies', icon: BuildingOfficeIcon },
  { name: 'Queues', href: '/admin/queues', icon: QueueListIcon },
  { name: 'Settings', href: '/admin/settings', icon: Cog6ToothIcon },
]

function AdminSidebar() {
  const location = useLocation()

  return (
    <div className="w-64 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 min-h-full">
      {/* Admin Header */}
      <div className="px-4 py-5 border-b border-gray-200 dark:border-gray-800">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-[#747474] to-[#5a5a5a] flex items-center justify-center">
            <Cog6ToothIcon className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Admin
            </h2>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              System Administration
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="p-4 space-y-1">
        {adminNavItems.map((item) => {
          const isActive =
            location.pathname === item.href ||
            (item.href !== '/admin' && location.pathname.startsWith(item.href))
          const isExactMatch = location.pathname === item.href

          return (
            <NavLink
              key={item.name}
              to={item.href}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150',
                (isActive && item.href === '/admin' && isExactMatch) ||
                  (isActive && item.href !== '/admin')
                  ? 'bg-[#0176d3] text-white shadow-sm'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
              )}
            >
              <item.icon
                className={cn(
                  'w-5 h-5 flex-shrink-0',
                  (isActive && item.href === '/admin' && isExactMatch) ||
                    (isActive && item.href !== '/admin')
                    ? 'text-white'
                    : 'text-gray-400'
                )}
              />
              {item.name}
            </NavLink>
          )
        })}
      </nav>

      {/* Quick Stats */}
      <div className="mt-auto p-4 border-t border-gray-200 dark:border-gray-800">
        <div className="text-xs text-gray-500 dark:text-gray-400 mb-2 font-medium uppercase tracking-wider">
          Quick Info
        </div>
        <div className="space-y-2 text-sm text-gray-600 dark:text-gray-300">
          <div className="flex items-center gap-2">
            <ChartBarIcon className="w-4 h-4 text-gray-400" />
            <span>View Reports</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export function AdminLayout({
  children,
  title,
  subtitle,
  actions,
}: AdminLayoutProps) {
  return (
    <PageLayout>
      <div className="flex min-h-[calc(100vh-124px)]">
        {/* Sidebar */}
        <AdminSidebar />

        {/* Main Content */}
        <div className="flex-1 bg-[#f3f4f6] dark:bg-gray-950">
          {/* Page Header */}
          {(title || actions) && (
            <div className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 px-6 py-4">
              <div className="flex items-center justify-between">
                <div>
                  {title && (
                    <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                      {title}
                    </h1>
                  )}
                  {subtitle && (
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                      {subtitle}
                    </p>
                  )}
                </div>
                {actions && <div className="flex items-center gap-3">{actions}</div>}
              </div>
            </div>
          )}

          {/* Page Content */}
          <div className="p-6">{children}</div>
        </div>
      </div>
    </PageLayout>
  )
}

export default AdminLayout
