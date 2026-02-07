/**
 * Header Component
 *
 * Global header matching Flask TrueLog design with:
 * - Fixed 80px height (h-20)
 * - Three sections: Left (logo + nav), Center (search), Right (user menu)
 * - TrueLog branding with logo and "Asset Management" text
 * - Navigation buttons: Inventory, Tickets, History (admin), Tracking (dev), Import
 * - Theme toggle, Notifications, User profile, Logout
 */

import { Fragment, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Menu, Transition } from '@headlessui/react'
import {
  MagnifyingGlassIcon,
  BellIcon,
  Bars3Icon,
  SunIcon,
  MoonIcon,
  UserCircleIcon,
  ArrowRightOnRectangleIcon,
  ArchiveBoxIcon,
  TicketIcon,
  ClockIcon,
  TruckIcon,
  ArrowUpTrayIcon,
  UsersIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils/cn'
import { useUIStore } from '@/store/ui.store'
import { useAuthStore } from '@/store/auth.store'
import { useTheme, type Theme } from '@/providers/ThemeProvider'

// Navigation item type
interface NavItem {
  name: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  requiresAdmin?: boolean
  requiresDeveloper?: boolean
}

// Navigation items matching Flask app
const navigationItems: NavItem[] = [
  { name: 'Inventory', href: '/inventory', icon: ArchiveBoxIcon },
  { name: 'Tickets', href: '/tickets', icon: TicketIcon },
  { name: 'Customers', href: '/customers', icon: UsersIcon },
  { name: 'History', href: '/history', icon: ClockIcon, requiresAdmin: true },
  { name: 'Tracking', href: '/tracking', icon: TruckIcon, requiresDeveloper: true },
  { name: 'Import', href: '/import', icon: ArrowUpTrayIcon },
]

// Theme Toggle Button - Simple light/dark toggle
function ThemeToggle() {
  const { theme, setTheme } = useTheme()

  const toggleTheme = () => {
    setTheme(theme === 'light' ? 'dark' : 'light')
  }

  return (
    <button
      onClick={toggleTheme}
      className="flex items-center px-3 py-2 text-sm font-medium text-gray-900 hover:text-truelog-dark hover:bg-truelog-light/10 rounded-md transition-colors dark:text-gray-200 dark:hover:text-white"
      title={`Switch to ${theme === 'light' ? 'Dark' : 'Light'} Theme`}
    >
      {theme === 'light' ? (
        <MoonIcon className="w-5 h-5" aria-hidden="true" />
      ) : (
        <SunIcon className="w-5 h-5" aria-hidden="true" />
      )}
    </button>
  )
}

// Notification Bell with badge
function NotificationBell() {
  const [notificationCount] = useState(3) // TODO: Replace with real notification count
  const [isOpen, setIsOpen] = useState(false)

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center px-3 py-2 text-sm font-medium text-gray-900 hover:text-truelog-dark hover:bg-truelog-light/10 rounded-md transition-colors relative dark:text-gray-200 dark:hover:text-white"
      >
        <BellIcon className="w-5 h-5" aria-hidden="true" />
        {notificationCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
            {notificationCount > 99 ? '99+' : notificationCount}
          </span>
        )}
      </button>

      {/* Notifications Dropdown */}
      <Transition
        show={isOpen}
        as={Fragment}
        enter="transition ease-out duration-100"
        enterFrom="transform opacity-0 scale-95"
        enterTo="transform opacity-100 scale-100"
        leave="transition ease-in duration-75"
        leaveFrom="transform opacity-100 scale-100"
        leaveTo="transform opacity-0 scale-95"
      >
        <div className="absolute right-0 mt-2 w-80 bg-white dark:bg-gray-800 rounded-lg shadow-lg ring-1 ring-black/5 dark:ring-white/10 z-50">
          <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Notifications</h3>
            <button className="text-xs text-blue-600 dark:text-blue-400 hover:underline">
              Mark all read
            </button>
          </div>
          <div className="max-h-96 overflow-y-auto">
            <div className="p-8 text-center text-gray-500 dark:text-gray-400">
              <BellIcon className="w-8 h-8 mx-auto mb-2 text-gray-400" />
              No notifications
            </div>
          </div>
        </div>
      </Transition>
    </div>
  )
}

// User Profile Link and Logout
function UserSection() {
  const { user, logout } = useAuthStore()

  if (!user) return null

  const handleLogout = () => {
    logout()
  }

  return (
    <>
      <Link
        to="/profile"
        className="flex items-center px-3 py-2 text-sm font-medium text-gray-900 hover:text-truelog-dark hover:bg-truelog-light/10 rounded-md transition-colors dark:text-gray-200 dark:hover:text-white"
      >
        <UserCircleIcon className="w-5 h-5 mr-2" aria-hidden="true" />
        {user.username}
      </Link>
      <button
        onClick={handleLogout}
        className="flex items-center px-3 py-2 text-sm font-medium text-gray-900 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors dark:text-gray-200 dark:hover:text-red-400 dark:hover:bg-red-900/20"
      >
        <ArrowRightOnRectangleIcon className="w-5 h-5 mr-2" aria-hidden="true" />
        Logout
      </button>
    </>
  )
}

// Global Search Input
function GlobalSearch() {
  const [query, setQuery] = useState('')

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    // TODO: Implement global search
    console.log('Search:', query)
  }

  return (
    <form onSubmit={handleSearch} className="flex-1 w-full max-w-3xl relative" id="globalSearchContainer">
      <div className="relative group">
        {/* Gradient border effect on focus */}
        <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-500 to-purple-500 rounded-xl opacity-0 group-focus-within:opacity-100 blur transition duration-300" />
        <div className="relative bg-white dark:bg-gray-800 rounded-lg">
          {/* Search Icon */}
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none z-10">
            <MagnifyingGlassIcon
              className="h-5 w-5 text-gray-400 group-focus-within:text-blue-500 transition-colors"
              aria-hidden="true"
            />
          </div>
          {/* Search Input */}
          <input
            type="search"
            name="q"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="block w-full pl-10 pr-16 py-3 border-2 border-gray-200 dark:border-gray-700 rounded-lg leading-5 bg-white dark:bg-gray-800 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:border-blue-500 text-sm shadow-sm transition-all duration-200 hover:border-gray-300 dark:hover:border-gray-600 text-gray-900 dark:text-white"
            placeholder="Search assets, tickets, accessories, customers..."
            aria-label="Global search"
          />
          {/* Keyboard Shortcut Hint */}
          <div className="absolute inset-y-0 right-3 flex items-center pointer-events-none z-10">
            <kbd className="inline-flex items-center px-2 py-1 text-xs font-semibold text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded shadow-sm">
              /
            </kbd>
          </div>
        </div>
      </div>
    </form>
  )
}

// Navigation Button Component
function NavButton({ item }: { item: NavItem }) {
  const location = useLocation()
  const isActive = location.pathname.startsWith(item.href)

  return (
    <Link
      to={item.href}
      className={cn(
        'flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors',
        isActive
          ? 'text-truelog-dark bg-truelog-light/20'
          : 'text-gray-900 hover:text-truelog-dark hover:bg-truelog-light/10 dark:text-gray-200 dark:hover:text-white'
      )}
    >
      <item.icon className="w-4 h-4 mr-1.5" aria-hidden="true" />
      {item.name}
    </Link>
  )
}

// Mobile Menu Toggle
function MobileMenuToggle() {
  const { toggleMobileMenu } = useUIStore()

  return (
    <button
      type="button"
      onClick={toggleMobileMenu}
      className="lg:hidden flex items-center justify-center w-10 h-10 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
    >
      <span className="sr-only">Open sidebar</span>
      <Bars3Icon className="h-6 w-6" aria-hidden="true" />
    </button>
  )
}

// TrueLog Logo Component
function TrueLogLogo() {
  return (
    <Link to="/" className="flex items-center space-x-3">
      {/* Logo image - try React public folder first, then Flask static */}
      <img
        src="/images/truelglogo.png"
        alt="TrueLog Logo"
        className="h-14 w-auto object-contain"
        onError={(e) => {
          // Fallback to Flask static path
          const target = e.target as HTMLImageElement
          if (!target.src.includes('/static/')) {
            target.src = '/static/images/truelglogo.png'
          }
        }}
      />
      <span className="text-2xl font-bold text-truelog-dark dark:text-truelog">
        Asset Management
      </span>
    </Link>
  )
}

// Main Header Export
export function Header() {
  const { user } = useAuthStore()
  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin'
  const isDeveloper = user?.role === 'developer'

  // Filter navigation items based on user role
  const filteredNavItems = navigationItems.filter((item) => {
    if (item.requiresAdmin && !isAdmin) return false
    if (item.requiresDeveloper && !isDeveloper) return false
    return true
  })

  return (
    <header className="bg-white dark:bg-gray-900 shadow-lg border-b border-gray-200 dark:border-gray-800 h-20 z-[2000] relative">
      <div className="w-full px-8 h-full">
        <div className="flex items-center gap-6 h-full w-full overflow-visible">
          {/* Left side: Logo and primary navigation */}
          <div className="flex items-center gap-4 flex-wrap min-w-fit">
            {/* Mobile menu toggle */}
            <MobileMenuToggle />

            {/* Logo and Name */}
            <TrueLogLogo />

            {user && (
              <>
                {/* Vertical Divider - hidden on mobile */}
                <div className="hidden lg:block h-10 w-px bg-gray-300 dark:bg-gray-600" />

                {/* Navigation Buttons */}
                <div className="hidden lg:flex flex-wrap items-center gap-1">
                  {filteredNavItems.map((item) => (
                    <NavButton key={item.name} item={item} />
                  ))}
                </div>
              </>
            )}
          </div>

          {/* Center: Global Search */}
          {user && <GlobalSearch />}

          {/* Right side navigation */}
          <div className="flex items-center gap-3 ml-auto">
            {user ? (
              <>
                <ThemeToggle />
                <NotificationBell />
                <UserSection />
              </>
            ) : (
              <Link
                to="/login"
                className="flex items-center px-3 py-2 text-sm font-medium text-gray-900 hover:text-truelog-dark hover:bg-truelog-light/10 rounded-md dark:text-gray-200 dark:hover:text-white"
              >
                <ArrowRightOnRectangleIcon className="w-5 h-5 mr-2 rotate-180" aria-hidden="true" />
                Login
              </Link>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}
