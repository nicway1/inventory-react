/**
 * Sidebar Component
 *
 * Collapsible sidebar navigation with:
 * - Expanded/collapsed states
 * - Navigation items with icons
 * - Active state indication
 * - TrueLog logo at top
 * - User profile section at bottom
 * - Mobile slide-out drawer
 * - Dark mode support
 */

import { Fragment } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { Dialog, Transition } from '@headlessui/react'
import {
  HomeIcon,
  TicketIcon,
  CubeIcon,
  PuzzlePieceIcon,
  UsersIcon,
  ChartBarIcon,
  Cog6ToothIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils/cn'
import { useUIStore } from '@/store/ui.store'
import { useAuthStore } from '@/store/auth.store'

interface NavItem {
  name: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  adminOnly?: boolean
}

const navigation: NavItem[] = [
  { name: 'Dashboard', href: '/dashboard', icon: HomeIcon },
  { name: 'Tickets', href: '/tickets', icon: TicketIcon },
  { name: 'Inventory', href: '/inventory', icon: CubeIcon },
  { name: 'Accessories', href: '/accessories', icon: PuzzlePieceIcon },
  { name: 'Customers', href: '/customers', icon: UsersIcon },
  { name: 'Reports', href: '/reports', icon: ChartBarIcon },
  { name: 'Admin', href: '/admin', icon: Cog6ToothIcon, adminOnly: true },
]

// TrueLog Logo Component
function Logo({ collapsed }: { collapsed: boolean }) {
  return (
    <div className="flex items-center h-16 px-4">
      <div className="flex items-center gap-3">
        {/* Logo Icon */}
        <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-br from-primary-500 to-primary-600 rounded-lg flex items-center justify-center">
          <span className="text-white font-bold text-lg">T</span>
        </div>
        {/* Logo Text */}
        <Transition
          show={!collapsed}
          enter="transition-opacity duration-200"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="transition-opacity duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <span className="text-xl font-semibold text-gray-900 dark:text-white whitespace-nowrap">
            TrueLog
          </span>
        </Transition>
      </div>
    </div>
  )
}

// Navigation Item Component
function NavItemLink({
  item,
  collapsed,
  onClick,
}: {
  item: NavItem
  collapsed: boolean
  onClick?: () => void
}) {
  const location = useLocation()
  const isActive =
    location.pathname === item.href ||
    location.pathname.startsWith(`${item.href}/`)

  return (
    <NavLink
      to={item.href}
      onClick={onClick}
      className={cn(
        'group flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-all duration-200',
        isActive
          ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/50 dark:text-primary-300'
          : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-300 dark:hover:bg-gray-800 dark:hover:text-white',
        collapsed && 'justify-center px-2'
      )}
      title={collapsed ? item.name : undefined}
    >
      <item.icon
        className={cn(
          'flex-shrink-0 h-5 w-5 transition-colors',
          isActive
            ? 'text-primary-600 dark:text-primary-400'
            : 'text-gray-400 group-hover:text-gray-500 dark:text-gray-500 dark:group-hover:text-gray-300'
        )}
        aria-hidden="true"
      />
      <Transition
        show={!collapsed}
        enter="transition-opacity duration-200"
        enterFrom="opacity-0"
        enterTo="opacity-100"
        leave="transition-opacity duration-200"
        leaveFrom="opacity-100"
        leaveTo="opacity-0"
      >
        <span className="whitespace-nowrap">{item.name}</span>
      </Transition>
    </NavLink>
  )
}

// User Profile Section
function UserProfile({ collapsed }: { collapsed: boolean }) {
  const user = useAuthStore((state) => state.user)

  if (!user) return null

  const initials = `${user.first_name?.[0] || ''}${user.last_name?.[0] || ''}`.toUpperCase() || user.username[0].toUpperCase()

  return (
    <div
      className={cn(
        'flex items-center gap-3 p-3 mx-3 mb-3 rounded-lg bg-gray-50 dark:bg-gray-800',
        collapsed && 'justify-center mx-2 p-2'
      )}
    >
      {/* Avatar */}
      <div className="flex-shrink-0 w-8 h-8 bg-primary-100 dark:bg-primary-900 rounded-full flex items-center justify-center">
        <span className="text-sm font-medium text-primary-700 dark:text-primary-300">
          {initials}
        </span>
      </div>

      {/* User Info */}
      <Transition
        show={!collapsed}
        enter="transition-opacity duration-200"
        enterFrom="opacity-0"
        enterTo="opacity-100"
        leave="transition-opacity duration-200"
        leaveFrom="opacity-100"
        leaveTo="opacity-0"
      >
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
            {user.first_name} {user.last_name}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 truncate capitalize">
            {user.role}
          </p>
        </div>
      </Transition>
    </div>
  )
}

// Desktop Sidebar
function DesktopSidebar() {
  const { sidebarCollapsed, toggleSidebar } = useUIStore()
  const user = useAuthStore((state) => state.user)
  const isAdmin = user?.role === 'admin'

  const filteredNavigation = navigation.filter(
    (item) => !item.adminOnly || isAdmin
  )

  return (
    <div
      className={cn(
        'hidden lg:fixed lg:inset-y-0 lg:flex lg:flex-col transition-all duration-300 ease-in-out',
        sidebarCollapsed ? 'lg:w-20' : 'lg:w-64'
      )}
    >
      <div className="flex flex-col flex-1 min-h-0 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800">
        {/* Logo */}
        <Logo collapsed={sidebarCollapsed} />

        {/* Collapse Toggle */}
        <button
          onClick={toggleSidebar}
          className="absolute top-5 -right-3 z-10 flex items-center justify-center w-6 h-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-full shadow-sm hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
          aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {sidebarCollapsed ? (
            <ChevronRightIcon className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronLeftIcon className="w-4 h-4 text-gray-500" />
          )}
        </button>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {filteredNavigation.map((item) => (
            <NavItemLink
              key={item.name}
              item={item}
              collapsed={sidebarCollapsed}
            />
          ))}
        </nav>

        {/* User Profile */}
        <UserProfile collapsed={sidebarCollapsed} />
      </div>
    </div>
  )
}

// Mobile Sidebar (Drawer)
function MobileSidebar() {
  const { isMobileMenuOpen, setMobileMenuOpen } = useUIStore()
  const user = useAuthStore((state) => state.user)
  const isAdmin = user?.role === 'admin'

  const filteredNavigation = navigation.filter(
    (item) => !item.adminOnly || isAdmin
  )

  const handleClose = () => setMobileMenuOpen(false)

  return (
    <Transition.Root show={isMobileMenuOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50 lg:hidden" onClose={handleClose}>
        {/* Backdrop */}
        <Transition.Child
          as={Fragment}
          enter="transition-opacity ease-linear duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="transition-opacity ease-linear duration-300"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-gray-900/80" />
        </Transition.Child>

        <div className="fixed inset-0 flex">
          {/* Sidebar Panel */}
          <Transition.Child
            as={Fragment}
            enter="transition ease-in-out duration-300 transform"
            enterFrom="-translate-x-full"
            enterTo="translate-x-0"
            leave="transition ease-in-out duration-300 transform"
            leaveFrom="translate-x-0"
            leaveTo="-translate-x-full"
          >
            <Dialog.Panel className="relative mr-16 flex w-full max-w-xs flex-1">
              {/* Close button */}
              <Transition.Child
                as={Fragment}
                enter="ease-in-out duration-300"
                enterFrom="opacity-0"
                enterTo="opacity-100"
                leave="ease-in-out duration-300"
                leaveFrom="opacity-100"
                leaveTo="opacity-0"
              >
                <div className="absolute left-full top-0 flex w-16 justify-center pt-5">
                  <button
                    type="button"
                    className="-m-2.5 p-2.5"
                    onClick={handleClose}
                  >
                    <span className="sr-only">Close sidebar</span>
                    <XMarkIcon
                      className="h-6 w-6 text-white"
                      aria-hidden="true"
                    />
                  </button>
                </div>
              </Transition.Child>

              {/* Sidebar Content */}
              <div className="flex grow flex-col gap-y-5 overflow-y-auto bg-white dark:bg-gray-900 px-0">
                {/* Logo */}
                <Logo collapsed={false} />

                {/* Navigation */}
                <nav className="flex-1 px-3 py-4 space-y-1">
                  {filteredNavigation.map((item) => (
                    <NavItemLink
                      key={item.name}
                      item={item}
                      collapsed={false}
                      onClick={handleClose}
                    />
                  ))}
                </nav>

                {/* User Profile */}
                <UserProfile collapsed={false} />
              </div>
            </Dialog.Panel>
          </Transition.Child>
        </div>
      </Dialog>
    </Transition.Root>
  )
}

// Main Sidebar Export
export function Sidebar() {
  return (
    <>
      <DesktopSidebar />
      <MobileSidebar />
    </>
  )
}
