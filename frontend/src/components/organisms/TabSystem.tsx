/**
 * TabSystem Component - Salesforce Lightning Style
 *
 * A clean, performant tab system with:
 * - App launcher (waffle icon)
 * - Console label
 * - Horizontal tab list
 * - Active tab indicator
 * - Tab close buttons
 * - New tab button
 * - Keyboard shortcuts (Ctrl+W, Ctrl+T)
 */

import { Fragment, useEffect, useRef, useCallback, memo } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Menu, Transition } from '@headlessui/react'
import {
  HomeIcon,
  TicketIcon,
  CubeIcon,
  ChartBarIcon,
  XMarkIcon,
  PlusIcon,
  Squares2X2Icon,
  UsersIcon,
  Cog6ToothIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils/cn'
import { useTabStore, type Tab, type TabIconType } from '@/store/tabs.store'

// Icon mapping
const TAB_ICONS: Record<TabIconType, React.ComponentType<{ className?: string }>> = {
  home: HomeIcon,
  ticket: TicketIcon,
  asset: CubeIcon,
  accessory: CubeIcon,
  inventory: CubeIcon,
  report: ChartBarIcon,
  dev: Cog6ToothIcon,
  customer: UsersIcon,
  admin: Cog6ToothIcon,
  settings: Cog6ToothIcon,
}

// App launcher items
const APP_ITEMS = [
  { name: 'Dashboard', url: '/dashboard', icon: HomeIcon, color: 'bg-blue-500' },
  { name: 'Tickets', url: '/tickets', icon: TicketIcon, color: 'bg-green-500' },
  { name: 'Inventory', url: '/inventory', icon: CubeIcon, color: 'bg-purple-500' },
  { name: 'Customers', url: '/customers', icon: UsersIcon, color: 'bg-pink-500' },
  { name: 'Reports', url: '/reports', icon: ChartBarIcon, color: 'bg-teal-500' },
]

// URL to icon mapping
function getIconForUrl(url: string): TabIconType {
  if (url.startsWith('/tickets')) return 'ticket'
  if (url.startsWith('/inventory')) return 'inventory'
  if (url.startsWith('/customers')) return 'customer'
  if (url.startsWith('/reports')) return 'report'
  if (url.startsWith('/admin')) return 'admin'
  if (url.startsWith('/settings')) return 'settings'
  return 'home'
}

// Get title from URL
function getTitleForUrl(url: string): string {
  if (url.startsWith('/tickets/')) return 'Ticket'
  if (url.startsWith('/tickets')) return 'Tickets'
  if (url.startsWith('/inventory/')) return 'Asset'
  if (url.startsWith('/inventory')) return 'Inventory'
  if (url.startsWith('/customers/')) return 'Customer'
  if (url.startsWith('/customers')) return 'Customers'
  if (url.startsWith('/reports')) return 'Reports'
  if (url.startsWith('/admin')) return 'Admin'
  if (url.startsWith('/settings')) return 'Settings'
  return 'Dashboard'
}

/**
 * App Launcher Button
 */
const AppLauncher = memo(function AppLauncher() {
  const navigate = useNavigate()
  const openTab = useOpenTab()

  return (
    <Menu as="div" className="relative">
      <Menu.Button
        className="flex items-center justify-center w-9 h-9 rounded text-[#0176d3] hover:bg-[#0176d3]/10 dark:text-blue-400 dark:hover:bg-blue-400/10 transition-colors"
        aria-label="App Launcher"
      >
        <Squares2X2Icon className="h-6 w-6" />
      </Menu.Button>

      <Transition
        as={Fragment}
        enter="transition ease-out duration-100"
        enterFrom="opacity-0 scale-95"
        enterTo="opacity-100 scale-100"
        leave="transition ease-in duration-75"
        leaveFrom="opacity-100 scale-100"
        leaveTo="opacity-0 scale-95"
      >
        <Menu.Items className="absolute left-0 z-50 mt-2 w-64 origin-top-left rounded-lg bg-white dark:bg-gray-800 shadow-lg ring-1 ring-black/5 dark:ring-white/10 focus:outline-none">
          <div className="px-4 py-2 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">App Launcher</h3>
          </div>
          <div className="grid grid-cols-3 gap-2 p-3">
            {APP_ITEMS.map((item) => (
              <Menu.Item key={item.name}>
                {({ active }) => (
                  <button
                    onClick={() => openTab(item.url, item.name)}
                    className={cn(
                      'flex flex-col items-center gap-2 p-3 rounded-lg transition-colors',
                      active && 'bg-gray-100 dark:bg-gray-700'
                    )}
                  >
                    <div className={cn('p-2 rounded-lg', item.color)}>
                      <item.icon className="h-5 w-5 text-white" />
                    </div>
                    <span className="text-xs text-gray-700 dark:text-gray-300">{item.name}</span>
                  </button>
                )}
              </Menu.Item>
            ))}
          </div>
        </Menu.Items>
      </Transition>
    </Menu>
  )
})

/**
 * Single Tab Item
 */
const TabItem = memo(function TabItem({
  tab,
  isActive,
  onActivate,
  onClose,
}: {
  tab: Tab
  isActive: boolean
  onActivate: () => void
  onClose: () => void
}) {
  const Icon = TAB_ICONS[tab.icon] || HomeIcon

  return (
    <div
      onClick={onActivate}
      className={cn(
        'group relative flex items-center gap-2 px-3 h-9 cursor-pointer select-none',
        'min-w-[120px] max-w-[200px]',
        'rounded-t-md border border-b-0',
        isActive
          ? 'bg-white dark:bg-gray-900 border-gray-300 dark:border-gray-600'
          : 'bg-gray-100 dark:bg-gray-800 border-transparent hover:bg-gray-200 dark:hover:bg-gray-700'
      )}
    >
      {/* Active indicator */}
      {isActive && (
        <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#0176d3] dark:bg-blue-400" />
      )}

      {/* Icon */}
      <Icon
        className={cn(
          'flex-shrink-0 h-4 w-4',
          isActive ? 'text-[#0176d3] dark:text-blue-400' : 'text-gray-500 dark:text-gray-400'
        )}
      />

      {/* Title */}
      <span
        className={cn(
          'flex-1 text-sm truncate',
          isActive ? 'text-gray-900 dark:text-white font-medium' : 'text-gray-600 dark:text-gray-300'
        )}
      >
        {tab.title}
      </span>

      {/* Close button */}
      {tab.closable && (
        <button
          onClick={(e) => {
            e.stopPropagation()
            onClose()
          }}
          className="flex-shrink-0 p-0.5 rounded opacity-0 group-hover:opacity-100 hover:bg-gray-300 dark:hover:bg-gray-600 transition-opacity"
          aria-label="Close tab"
        >
          <XMarkIcon className="h-3.5 w-3.5 text-gray-500 hover:text-red-500 dark:text-gray-400" />
        </button>
      )}
    </div>
  )
})

/**
 * Main TabSystem Component
 */
export function TabSystem() {
  const navigate = useNavigate()
  const location = useLocation()
  const isNavigatingRef = useRef(false)
  const lastUrlRef = useRef(location.pathname)

  const { tabs, activeTabId, setActiveTab, removeTab, openNewTab, closeActiveTab, updateTab } = useTabStore()

  // Handle URL changes (browser back/forward, direct URL entry)
  useEffect(() => {
    // Skip if we triggered this navigation
    if (isNavigatingRef.current) {
      isNavigatingRef.current = false
      return
    }

    const currentPath = location.pathname

    // Skip if URL hasn't changed
    if (currentPath === lastUrlRef.current) return
    lastUrlRef.current = currentPath

    // Find matching tab
    const matchingTab = tabs.find((t) => {
      const tabPath = t.url.split('?')[0]
      return tabPath === currentPath || currentPath.startsWith(tabPath + '/')
    })

    if (matchingTab) {
      // Activate existing tab and update its URL
      if (matchingTab.id !== activeTabId) {
        setActiveTab(matchingTab.id)
      }
      if (matchingTab.url !== currentPath) {
        updateTab(matchingTab.id, { url: currentPath })
      }
    } else {
      // Create new tab for this URL
      const title = getTitleForUrl(currentPath)
      const icon = getIconForUrl(currentPath)
      openNewTab(currentPath, title, icon)
    }
  }, [location.pathname, tabs, activeTabId, setActiveTab, updateTab, openNewTab])

  // Handle tab click - navigate to tab URL
  const handleTabClick = useCallback(
    (tab: Tab) => {
      if (tab.id === activeTabId) return // Already active

      setActiveTab(tab.id)

      // Navigate to tab URL
      const currentPath = location.pathname
      const tabPath = tab.url.split('?')[0]

      if (currentPath !== tabPath) {
        isNavigatingRef.current = true
        lastUrlRef.current = tabPath
        navigate(tab.url)
      }
    },
    [activeTabId, setActiveTab, navigate, location.pathname]
  )

  // Handle tab close
  const handleTabClose = useCallback(
    (tabId: string) => {
      const tabIndex = tabs.findIndex((t) => t.id === tabId)
      const isActiveTab = tabId === activeTabId

      removeTab(tabId)

      // If closing active tab, navigate to new active tab
      if (isActiveTab && tabs.length > 1) {
        const newIndex = Math.max(0, tabIndex - 1)
        const newActiveTab = tabs.filter((t) => t.id !== tabId)[newIndex]
        if (newActiveTab) {
          isNavigatingRef.current = true
          lastUrlRef.current = newActiveTab.url.split('?')[0]
          navigate(newActiveTab.url)
        }
      }
    },
    [tabs, activeTabId, removeTab, navigate]
  )

  // Handle new tab button
  const handleNewTab = useCallback(() => {
    isNavigatingRef.current = true
    lastUrlRef.current = '/dashboard'
    openNewTab('/dashboard', 'Dashboard', 'home')
    navigate('/dashboard')
  }, [openNewTab, navigate])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const modifier = e.metaKey || e.ctrlKey

      if (modifier && e.key === 'w') {
        e.preventDefault()
        closeActiveTab()
      } else if (modifier && e.key === 't') {
        e.preventDefault()
        handleNewTab()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [closeActiveTab, handleNewTab])

  return (
    <div className="flex items-center h-11 bg-gradient-to-b from-white to-gray-100 dark:from-gray-800 dark:to-gray-900 border-b border-gray-300 dark:border-gray-700">
      {/* App Launcher */}
      <div className="flex-shrink-0 px-2">
        <AppLauncher />
      </div>

      {/* Console Label */}
      <div className="flex-shrink-0 px-4 h-full flex items-center border-r border-gray-300 dark:border-gray-600">
        <span className="text-sm font-bold text-[#0176d3] dark:text-blue-400">Service Console</span>
      </div>

      {/* Tab List */}
      <div className="flex-1 flex items-end gap-0.5 px-2 overflow-x-auto scrollbar-hide pb-px">
        {tabs.map((tab) => (
          <TabItem
            key={tab.id}
            tab={tab}
            isActive={tab.id === activeTabId}
            onActivate={() => handleTabClick(tab)}
            onClose={() => handleTabClose(tab.id)}
          />
        ))}
      </div>

      {/* New Tab Button */}
      <div className="flex-shrink-0 px-2">
        <button
          onClick={handleNewTab}
          className="flex items-center justify-center w-8 h-8 rounded text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
          aria-label="New tab"
          title="New tab (Ctrl+T)"
        >
          <PlusIcon className="h-5 w-5" />
        </button>
      </div>
    </div>
  )
}

/**
 * Hook to open a tab from anywhere
 */
export function useOpenTab() {
  const navigate = useNavigate()
  const { openNewTab, setActiveTab, getTabByUrl } = useTabStore()

  return useCallback(
    (url: string, title?: string) => {
      const existingTab = getTabByUrl(url)

      if (existingTab) {
        setActiveTab(existingTab.id)
      } else {
        const tabTitle = title || getTitleForUrl(url)
        const tabIcon = getIconForUrl(url)
        openNewTab(url, tabTitle, tabIcon)
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
