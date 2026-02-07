/**
 * TabSystem Component
 *
 * Salesforce-style tab system with:
 * - App launcher (9-dot waffle icon)
 * - Console label
 * - Horizontal scrolling tab list
 * - Active tab indicator (blue underline)
 * - Close button on closable tabs
 * - New tab button
 * - Keyboard shortcuts
 * - Dark mode support
 * - React Router integration
 * - sessionStorage persistence
 */

import { Fragment, useEffect, useRef, useCallback } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Menu, Transition } from '@headlessui/react'
import {
  HomeIcon,
  TicketIcon,
  CubeIcon,
  PuzzlePieceIcon,
  ChartBarIcon,
  XMarkIcon,
  PlusIcon,
  Squares2X2Icon,
  UsersIcon,
  Cog6ToothIcon,
  WrenchScrewdriverIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils/cn'
import { useTabStore, type Tab, type TabIconType } from '@/store/tabs.store'
import { useTheme } from '@/providers/ThemeProvider'

/**
 * Icon mapping for tab types
 */
const TAB_ICONS: Record<TabIconType, React.ComponentType<{ className?: string }>> = {
  home: HomeIcon,
  ticket: TicketIcon,
  asset: CubeIcon,
  accessory: PuzzlePieceIcon,
  inventory: CubeIcon,
  report: ChartBarIcon,
  dev: WrenchScrewdriverIcon,
  customer: UsersIcon,
  admin: Cog6ToothIcon,
  settings: Cog6ToothIcon,
}

/**
 * App launcher menu items with colored icons
 */
const APP_LAUNCHER_ITEMS = [
  { name: 'Dashboard', url: '/dashboard', icon: HomeIcon, color: 'bg-blue-500' },
  { name: 'Tickets', url: '/tickets', icon: TicketIcon, color: 'bg-green-500' },
  { name: 'Inventory', url: '/inventory', icon: CubeIcon, color: 'bg-purple-500' },
  { name: 'Customers', url: '/customers', icon: UsersIcon, color: 'bg-pink-500' },
  { name: 'Reports', url: '/reports', icon: ChartBarIcon, color: 'bg-teal-500' },
  { name: 'Admin', url: '/admin', icon: Cog6ToothIcon, color: 'bg-gray-500' },
]

/**
 * URL to icon type mapping for automatic icon detection
 */
const URL_TO_ICON: Record<string, TabIconType> = {
  '/dashboard': 'home',
  '/tickets': 'ticket',
  '/inventory': 'inventory',
  '/inventory/assets': 'asset',
  '/inventory/accessories': 'accessory',
  '/customers': 'customer',
  '/reports': 'report',
  '/admin': 'admin',
  '/settings': 'settings',
}

/**
 * Get icon type from URL
 */
function getIconFromUrl(url: string): TabIconType {
  // Check exact match first
  if (URL_TO_ICON[url]) {
    return URL_TO_ICON[url]
  }
  // Sort prefixes by length (longest first) to match most specific route
  const sortedPrefixes = Object.entries(URL_TO_ICON).sort(
    ([a], [b]) => b.length - a.length
  )
  // Check prefix match (most specific first)
  for (const [prefix, icon] of sortedPrefixes) {
    if (url.startsWith(prefix)) {
      return icon
    }
  }
  return 'home'
}

/**
 * App Launcher Button (9-dot waffle icon)
 */
function AppLauncher() {
  const navigate = useNavigate()
  const { openNewTab, setActiveTab, getTabByUrl } = useTabStore()

  const handleItemClick = (item: typeof APP_LAUNCHER_ITEMS[0]) => {
    // Check if tab exists
    const existingTab = getTabByUrl(item.url)
    if (existingTab) {
      setActiveTab(existingTab.id)
      navigate(item.url)
    } else {
      openNewTab(item.url, item.name, getIconFromUrl(item.url))
      navigate(item.url)
    }
  }

  return (
    <Menu as="div" className="relative">
      <Menu.Button
        className={cn(
          'flex items-center justify-center w-9 h-9 rounded',
          'text-[#0176d3] hover:bg-[#0176d3]/10',
          'dark:text-[#60a5fa] dark:hover:bg-[#60a5fa]/10',
          'transition-colors'
        )}
        aria-label="App Launcher"
      >
        <Squares2X2Icon className="h-6 w-6" />
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
        <Menu.Items
          className={cn(
            'absolute left-0 z-50 mt-2 w-72 origin-top-left rounded-lg py-2 shadow-lg',
            'bg-white ring-1 ring-black/5',
            'dark:bg-gray-800 dark:ring-white/10',
            'focus:outline-none'
          )}
        >
          <div className="px-4 py-2 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
              App Launcher
            </h3>
          </div>
          <div className="grid grid-cols-3 gap-2 p-3">
            {APP_LAUNCHER_ITEMS.map((item) => (
              <Menu.Item key={item.name}>
                {({ active }) => (
                  <button
                    onClick={() => handleItemClick(item)}
                    className={cn(
                      'flex flex-col items-center gap-2 p-3 rounded-lg transition-colors',
                      active && 'bg-gray-100 dark:bg-gray-700'
                    )}
                  >
                    <div className={cn('p-2 rounded-lg', item.color)}>
                      <item.icon className="h-5 w-5 text-white" />
                    </div>
                    <span className="text-xs text-gray-700 dark:text-gray-300 text-center">
                      {item.name}
                    </span>
                  </button>
                )}
              </Menu.Item>
            ))}
          </div>
        </Menu.Items>
      </Transition>
    </Menu>
  )
}

/**
 * Console Label
 */
function ConsoleLabel() {
  return (
    <div
      className={cn(
        'flex items-center px-4 h-full',
        'border-r border-[#dddbda] dark:border-[#374151]'
      )}
    >
      <span className="text-base font-bold text-[#0176d3] dark:text-[#60a5fa] whitespace-nowrap">
        Service Console
      </span>
    </div>
  )
}

/**
 * Individual Tab Component
 */
function TabItem({
  tab,
  isActive,
  onClose,
  onClick,
}: {
  tab: Tab
  isActive: boolean
  onClose: () => void
  onClick: () => void
}) {
  const Icon = TAB_ICONS[tab.icon] || HomeIcon

  return (
    <button
      onClick={onClick}
      className={cn(
        'group relative flex items-center gap-2 px-3 h-10',
        'min-w-[140px] max-w-[240px]',
        'border border-[#dddbda] dark:border-[#374151]',
        'rounded-t transition-colors',
        // Remove bottom border to connect with content
        'border-b-0',
        // Background colors
        isActive
          ? 'bg-white dark:bg-gray-900'
          : 'bg-[#f3f3f3] dark:bg-gray-800 hover:bg-[#e5e5e5] dark:hover:bg-gray-700',
        // Focus ring
        'focus:outline-none focus:ring-2 focus:ring-[#0176d3] dark:focus:ring-[#60a5fa] focus:ring-inset'
      )}
      style={{ borderRadius: '0.25rem 0.25rem 0 0' }}
      title={tab.title}
    >
      {/* Active indicator (blue underline) */}
      {isActive && (
        <div
          className={cn(
            'absolute bottom-0 left-0 right-0 h-[3px]',
            'bg-[#0176d3] dark:bg-[#60a5fa]'
          )}
        />
      )}

      {/* Tab icon */}
      <Icon
        className={cn(
          'flex-shrink-0 h-4 w-4',
          isActive
            ? 'text-[#0176d3] dark:text-[#60a5fa]'
            : 'text-gray-500 dark:text-gray-400'
        )}
      />

      {/* Tab title */}
      <span
        className={cn(
          'flex-1 text-sm truncate text-left',
          isActive
            ? 'text-gray-900 dark:text-white font-medium'
            : 'text-gray-600 dark:text-[#d1d5db]'
        )}
      >
        {tab.title}
      </span>

      {/* Close button (only for closable tabs) */}
      {tab.closable && (
        <button
          onClick={(e) => {
            e.stopPropagation()
            onClose()
          }}
          className={cn(
            'flex-shrink-0 p-0.5 rounded',
            'opacity-0 group-hover:opacity-100',
            'hover:bg-gray-200 dark:hover:bg-gray-600',
            'transition-opacity'
          )}
          aria-label={`Close ${tab.title} tab`}
        >
          <XMarkIcon className="h-4 w-4 text-gray-500 hover:text-red-500 dark:text-gray-400 dark:hover:text-red-400" />
        </button>
      )}
    </button>
  )
}

/**
 * New Tab Button
 */
function NewTabButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center justify-center w-8 h-8 ml-1',
        'rounded hover:bg-gray-200 dark:hover:bg-gray-700',
        'text-gray-600 dark:text-gray-400',
        'transition-colors',
        'focus:outline-none focus:ring-2 focus:ring-[#0176d3] dark:focus:ring-[#60a5fa]'
      )}
      aria-label="New tab"
      title="New tab (Ctrl+T)"
    >
      <PlusIcon className="h-5 w-5" />
    </button>
  )
}

/**
 * Main TabSystem Component
 */
export function TabSystem() {
  const navigate = useNavigate()
  const location = useLocation()
  const { resolvedTheme } = useTheme()
  const tabListRef = useRef<HTMLDivElement>(null)

  const {
    tabs,
    activeTabId,
    setActiveTab,
    removeTab,
    openNewTab,
    closeActiveTab,
    jumpToHomeTab,
  } = useTabStore()

  // Sync active tab with current URL
  useEffect(() => {
    const currentTab = tabs.find((t) => t.id === activeTabId)
    if (currentTab && currentTab.url !== location.pathname) {
      // Check if there's a tab matching the current URL
      const matchingTab = tabs.find((t) => t.url === location.pathname)
      if (matchingTab) {
        setActiveTab(matchingTab.id)
      }
    }
  }, [location.pathname, tabs, activeTabId, setActiveTab])

  // Navigate when active tab changes
  useEffect(() => {
    const activeTab = tabs.find((t) => t.id === activeTabId)
    if (activeTab && activeTab.url !== location.pathname) {
      navigate(activeTab.url)
    }
  }, [activeTabId, tabs, navigate, location.pathname])

  // Handle tab click
  const handleTabClick = useCallback(
    (tab: Tab) => {
      setActiveTab(tab.id)
      navigate(tab.url)
    },
    [setActiveTab, navigate]
  )

  // Handle tab close
  const handleTabClose = useCallback(
    (tabId: string) => {
      removeTab(tabId)
    },
    [removeTab]
  )

  // Handle new tab
  const handleNewTab = useCallback(() => {
    // Default to dashboard for new tabs
    const tabId = openNewTab('/dashboard', 'New Tab', 'home')
    const newTab = tabs.find((t) => t.id === tabId)
    if (newTab) {
      navigate(newTab.url)
    }
  }, [openNewTab, tabs, navigate])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0
      const modifier = isMac ? e.metaKey : e.ctrlKey

      if (!modifier) return

      switch (e.key.toLowerCase()) {
        case 'w':
          e.preventDefault()
          closeActiveTab()
          break
        case 't':
          e.preventDefault()
          handleNewTab()
          break
        case '1':
          e.preventDefault()
          jumpToHomeTab()
          break
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [closeActiveTab, handleNewTab, jumpToHomeTab])

  // Scroll active tab into view
  useEffect(() => {
    if (tabListRef.current && activeTabId) {
      const activeTabElement = tabListRef.current.querySelector(
        `[data-tab-id="${activeTabId}"]`
      )
      if (activeTabElement) {
        activeTabElement.scrollIntoView({
          behavior: 'smooth',
          block: 'nearest',
          inline: 'nearest',
        })
      }
    }
  }, [activeTabId])

  const isDarkMode = resolvedTheme === 'dark'

  return (
    <div
      className={cn(
        'relative z-[999] flex items-center min-h-[44px]',
        'border-b',
        // Light mode gradient
        !isDarkMode && 'border-[#dddbda]',
        // Dark mode gradient
        isDarkMode && 'border-[#374151]'
      )}
      style={{
        background: isDarkMode
          ? 'linear-gradient(to bottom, #1f2937 0%, #111827 100%)'
          : 'linear-gradient(to bottom, #ffffff 0%, #f3f3f3 100%)',
      }}
    >
      {/* App Launcher */}
      <div className="flex-shrink-0 px-2">
        <AppLauncher />
      </div>

      {/* Console Label */}
      <ConsoleLabel />

      {/* Tab List */}
      <div
        ref={tabListRef}
        className={cn(
          'flex items-end flex-1 gap-[2px] px-2 overflow-x-auto',
          // Hide scrollbar
          'scrollbar-hide',
          '[&::-webkit-scrollbar]:hidden',
          '[-ms-overflow-style:none]',
          '[scrollbar-width:none]'
        )}
        style={{ paddingBottom: '1px' }}
      >
        {tabs.map((tab) => (
          <div key={tab.id} data-tab-id={tab.id}>
            <TabItem
              tab={tab}
              isActive={tab.id === activeTabId}
              onClose={() => handleTabClose(tab.id)}
              onClick={() => handleTabClick(tab)}
            />
          </div>
        ))}
      </div>

      {/* New Tab Button */}
      <div className="flex-shrink-0 px-2">
        <NewTabButton onClick={handleNewTab} />
      </div>
    </div>
  )
}

/**
 * Hook to open a new tab from anywhere in the app
 */
export function useOpenTab() {
  const navigate = useNavigate()
  const { openNewTab, setActiveTab, getTabByUrl } = useTabStore()

  return useCallback(
    (url: string, title: string, icon?: TabIconType) => {
      const tabIcon = icon || getIconFromUrl(url)
      const existingTab = getTabByUrl(url)

      if (existingTab) {
        setActiveTab(existingTab.id)
      } else {
        openNewTab(url, title, tabIcon)
      }
      navigate(url)
    },
    [navigate, openNewTab, setActiveTab, getTabByUrl]
  )
}

/**
 * Hook to update current tab title
 */
export function useUpdateTabTitle() {
  const { activeTabId, updateTab } = useTabStore()

  return useCallback(
    (title: string) => {
      if (activeTabId) {
        updateTab(activeTabId, { title })
      }
    },
    [activeTabId, updateTab]
  )
}

export default TabSystem
