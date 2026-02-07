/**
 * Header Component
 *
 * Global header with:
 * - Global search input
 * - Notification bell with badge
 * - User dropdown menu
 * - Theme toggle (light/dark/system)
 * - Mobile menu toggle button
 */

import { Fragment, useState } from 'react'
import { Menu, Transition } from '@headlessui/react'
import {
  MagnifyingGlassIcon,
  BellIcon,
  Bars3Icon,
  SunIcon,
  MoonIcon,
  ComputerDesktopIcon,
  UserCircleIcon,
  Cog6ToothIcon,
  ArrowRightOnRectangleIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils/cn'
import { useUIStore } from '@/store/ui.store'
import { useAuthStore } from '@/store/auth.store'
import { useTheme, type Theme } from '@/providers/ThemeProvider'

// Theme Toggle Button
function ThemeToggle() {
  const { theme, setTheme } = useTheme()

  const themeOptions: { value: Theme; label: string; icon: typeof SunIcon }[] = [
    { value: 'light', label: 'Light', icon: SunIcon },
    { value: 'dark', label: 'Dark', icon: MoonIcon },
    { value: 'system', label: 'System', icon: ComputerDesktopIcon },
  ]

  const currentThemeIcon = themeOptions.find((t) => t.value === theme)?.icon || SunIcon
  const CurrentIcon = currentThemeIcon

  return (
    <Menu as="div" className="relative">
      <Menu.Button className="flex items-center justify-center w-10 h-10 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors">
        <span className="sr-only">Toggle theme</span>
        <CurrentIcon className="h-5 w-5" aria-hidden="true" />
      </Menu.Button>

      <Transition
        as={Fragment}
        enter="transition ease-out duration-100"
        enterFrom="transform opacity-0 scale-95"
        enterTo="transform opacity-100 scale-100"
        leave="transition ease-in duration-75"
        leaveFrom="transform opacity-100 scale-100"
        leaveTo="transform opacity-0 scale-95"
      >
        <Menu.Items className="absolute right-0 z-10 mt-2 w-36 origin-top-right rounded-lg bg-white dark:bg-gray-800 py-1 shadow-lg ring-1 ring-black/5 dark:ring-white/10 focus:outline-none">
          {themeOptions.map((option) => (
            <Menu.Item key={option.value}>
              {({ active }) => (
                <button
                  onClick={() => setTheme(option.value)}
                  className={cn(
                    'flex w-full items-center gap-3 px-4 py-2 text-sm',
                    active
                      ? 'bg-gray-100 dark:bg-gray-700'
                      : 'text-gray-700 dark:text-gray-200',
                    theme === option.value && 'text-primary-600 dark:text-primary-400'
                  )}
                >
                  <option.icon className="h-4 w-4" aria-hidden="true" />
                  {option.label}
                </button>
              )}
            </Menu.Item>
          ))}
        </Menu.Items>
      </Transition>
    </Menu>
  )
}

// Notification Bell
function NotificationBell() {
  const [notificationCount] = useState(3) // TODO: Replace with real notification count

  return (
    <button
      type="button"
      className="relative flex items-center justify-center w-10 h-10 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
    >
      <span className="sr-only">View notifications</span>
      <BellIcon className="h-5 w-5" aria-hidden="true" />
      {notificationCount > 0 && (
        <span className="absolute top-1 right-1 flex items-center justify-center min-w-[18px] h-[18px] px-1 text-xs font-medium text-white bg-danger-500 rounded-full">
          {notificationCount > 99 ? '99+' : notificationCount}
        </span>
      )}
    </button>
  )
}

// User Dropdown Menu
function UserMenu() {
  const { user, logout } = useAuthStore()

  if (!user) return null

  const initials =
    `${user.first_name?.[0] || ''}${user.last_name?.[0] || ''}`.toUpperCase() ||
    user.username[0].toUpperCase()

  const handleLogout = () => {
    logout()
    // TODO: Redirect to login page
  }

  return (
    <Menu as="div" className="relative">
      <Menu.Button className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
        <div className="flex-shrink-0 w-8 h-8 bg-primary-100 dark:bg-primary-900 rounded-full flex items-center justify-center">
          <span className="text-sm font-medium text-primary-700 dark:text-primary-300">
            {initials}
          </span>
        </div>
        <span className="hidden sm:block text-sm font-medium text-gray-700 dark:text-gray-200">
          {user.first_name} {user.last_name}
        </span>
      </Menu.Button>

      <Transition
        as={Fragment}
        enter="transition ease-out duration-100"
        enterFrom="transform opacity-0 scale-95"
        enterTo="transform opacity-100 scale-100"
        leave="transition ease-in duration-75"
        leaveFrom="transform opacity-100 scale-100"
        leaveTo="transform opacity-0 scale-95"
      >
        <Menu.Items className="absolute right-0 z-10 mt-2 w-56 origin-top-right rounded-lg bg-white dark:bg-gray-800 py-1 shadow-lg ring-1 ring-black/5 dark:ring-white/10 focus:outline-none">
          {/* User Info */}
          <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              {user.first_name} {user.last_name}
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
              {user.email}
            </p>
          </div>

          {/* Menu Items */}
          <div className="py-1">
            <Menu.Item>
              {({ active }) => (
                <a
                  href="/profile"
                  className={cn(
                    'flex items-center gap-3 px-4 py-2 text-sm',
                    active
                      ? 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
                      : 'text-gray-700 dark:text-gray-200'
                  )}
                >
                  <UserCircleIcon className="h-4 w-4" aria-hidden="true" />
                  Your Profile
                </a>
              )}
            </Menu.Item>
            <Menu.Item>
              {({ active }) => (
                <a
                  href="/settings"
                  className={cn(
                    'flex items-center gap-3 px-4 py-2 text-sm',
                    active
                      ? 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
                      : 'text-gray-700 dark:text-gray-200'
                  )}
                >
                  <Cog6ToothIcon className="h-4 w-4" aria-hidden="true" />
                  Settings
                </a>
              )}
            </Menu.Item>
          </div>

          {/* Logout */}
          <div className="py-1 border-t border-gray-200 dark:border-gray-700">
            <Menu.Item>
              {({ active }) => (
                <button
                  onClick={handleLogout}
                  className={cn(
                    'flex w-full items-center gap-3 px-4 py-2 text-sm',
                    active
                      ? 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
                      : 'text-gray-700 dark:text-gray-200'
                  )}
                >
                  <ArrowRightOnRectangleIcon
                    className="h-4 w-4"
                    aria-hidden="true"
                  />
                  Sign out
                </button>
              )}
            </Menu.Item>
          </div>
        </Menu.Items>
      </Transition>
    </Menu>
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
    <form onSubmit={handleSearch} className="relative flex-1 max-w-md">
      <div className="relative">
        <MagnifyingGlassIcon
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400"
          aria-hidden="true"
        />
        <input
          type="search"
          name="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="block w-full pl-10 pr-4 py-2 text-sm bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:bg-white dark:focus:bg-gray-700 focus:ring-2 focus:ring-primary-500 transition-all"
          placeholder="Search tickets, devices, customers..."
        />
      </div>
    </form>
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

// Main Header Export
export function Header() {
  return (
    <header className="sticky top-0 z-40 flex h-16 shrink-0 items-center gap-4 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 px-4 sm:px-6">
      {/* Mobile menu toggle */}
      <MobileMenuToggle />

      {/* Search */}
      <div className="flex flex-1 items-center gap-4">
        <GlobalSearch />
      </div>

      {/* Right side actions */}
      <div className="flex items-center gap-2">
        <ThemeToggle />
        <NotificationBell />
        <div className="hidden sm:block h-6 w-px bg-gray-200 dark:bg-gray-700" />
        <UserMenu />
      </div>
    </header>
  )
}
