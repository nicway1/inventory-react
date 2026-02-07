/**
 * Tab Store
 *
 * Manages Salesforce-style tab system state using Zustand with sessionStorage persistence.
 * Supports multiple tabs, navigation, keyboard shortcuts, and dark mode.
 */

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

/**
 * Tab icon types matching Flask TrueLog design
 */
export type TabIconType = 'home' | 'ticket' | 'asset' | 'accessory' | 'inventory' | 'report' | 'dev' | 'customer' | 'admin' | 'settings'

/**
 * Tab interface
 */
export interface Tab {
  id: string
  title: string
  url: string
  icon: TabIconType
  closable: boolean
}

/**
 * Tab state interface
 */
interface TabState {
  // State
  tabs: Tab[]
  activeTabId: string | null

  // Actions
  addTab: (tab: Omit<Tab, 'id'>) => string
  removeTab: (tabId: string) => void
  setActiveTab: (tabId: string) => void
  updateTab: (tabId: string, updates: Partial<Omit<Tab, 'id'>>) => void
  reorderTabs: (startIndex: number, endIndex: number) => void
  closeAllTabs: () => void
  closeOtherTabs: (tabId: string) => void
  closeTabsToRight: (tabId: string) => void

  // Getters
  getActiveTab: () => Tab | undefined
  getTabById: (tabId: string) => Tab | undefined
  getTabByUrl: (url: string) => Tab | undefined

  // Navigation helpers
  openNewTab: (url: string, title: string, icon: TabIconType) => string
  navigateToTab: (tabId: string) => void
  closeActiveTab: () => void
  jumpToHomeTab: () => void
}

/**
 * Generate a unique tab ID
 */
const generateTabId = (): string => {
  return `tab-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

/**
 * Default home tab
 */
const HOME_TAB: Tab = {
  id: 'home',
  title: 'Home',
  url: '/dashboard',
  icon: 'home',
  closable: false,
}

/**
 * Tab store with Zustand
 */
export const useTabStore = create<TabState>()(
  persist(
    (set, get) => ({
      // Initial state with home tab
      tabs: [HOME_TAB],
      activeTabId: 'home',

      // Add a new tab
      addTab: (tabData) => {
        const id = generateTabId()
        const newTab: Tab = { ...tabData, id }

        set((state) => ({
          tabs: [...state.tabs, newTab],
          activeTabId: id,
        }))

        return id
      },

      // Remove a tab
      removeTab: (tabId) => {
        const { tabs, activeTabId } = get()
        const tabToRemove = tabs.find((t) => t.id === tabId)

        // Don't remove non-closable tabs
        if (!tabToRemove?.closable) return

        const tabIndex = tabs.findIndex((t) => t.id === tabId)
        const newTabs = tabs.filter((t) => t.id !== tabId)

        // If removing active tab, activate adjacent tab
        let newActiveTabId = activeTabId
        if (activeTabId === tabId && newTabs.length > 0) {
          // Prefer tab to the left, otherwise tab to the right
          const newIndex = Math.max(0, tabIndex - 1)
          newActiveTabId = newTabs[newIndex].id
        }

        set({
          tabs: newTabs,
          activeTabId: newActiveTabId,
        })
      },

      // Set active tab
      setActiveTab: (tabId) => {
        const tab = get().tabs.find((t) => t.id === tabId)
        if (tab) {
          set({ activeTabId: tabId })
        }
      },

      // Update tab properties
      updateTab: (tabId, updates) => {
        set((state) => ({
          tabs: state.tabs.map((tab) =>
            tab.id === tabId ? { ...tab, ...updates } : tab
          ),
        }))
      },

      // Reorder tabs (for drag and drop)
      reorderTabs: (startIndex, endIndex) => {
        set((state) => {
          const newTabs = [...state.tabs]
          const [removed] = newTabs.splice(startIndex, 1)
          newTabs.splice(endIndex, 0, removed)
          return { tabs: newTabs }
        })
      },

      // Close all closable tabs
      closeAllTabs: () => {
        set((state) => ({
          tabs: state.tabs.filter((t) => !t.closable),
          activeTabId: 'home',
        }))
      },

      // Close all tabs except the specified one
      closeOtherTabs: (tabId) => {
        set((state) => ({
          tabs: state.tabs.filter((t) => t.id === tabId || !t.closable),
          activeTabId: tabId,
        }))
      },

      // Close all tabs to the right of the specified tab
      closeTabsToRight: (tabId) => {
        set((state) => {
          const tabIndex = state.tabs.findIndex((t) => t.id === tabId)
          if (tabIndex === -1) return state

          return {
            tabs: state.tabs.filter(
              (t, index) => index <= tabIndex || !t.closable
            ),
          }
        })
      },

      // Get active tab
      getActiveTab: () => {
        const { tabs, activeTabId } = get()
        return tabs.find((t) => t.id === activeTabId)
      },

      // Get tab by ID
      getTabById: (tabId) => {
        return get().tabs.find((t) => t.id === tabId)
      },

      // Get tab by URL
      getTabByUrl: (url) => {
        return get().tabs.find((t) => t.url === url)
      },

      // Open a new tab and navigate to it
      openNewTab: (url, title, icon) => {
        const { tabs, addTab, setActiveTab } = get()

        // Check if tab with same URL already exists
        const existingTab = tabs.find((t) => t.url === url)
        if (existingTab) {
          setActiveTab(existingTab.id)
          return existingTab.id
        }

        return addTab({
          title,
          url,
          icon,
          closable: true,
        })
      },

      // Navigate to a specific tab
      navigateToTab: (tabId) => {
        get().setActiveTab(tabId)
      },

      // Close the active tab
      closeActiveTab: () => {
        const { activeTabId, removeTab } = get()
        if (activeTabId) {
          removeTab(activeTabId)
        }
      },

      // Jump to home tab
      jumpToHomeTab: () => {
        set({ activeTabId: 'home' })
      },
    }),
    {
      name: 'sf-tabs',
      storage: createJSONStorage(() => sessionStorage),
      partialize: (state) => ({
        tabs: state.tabs,
        activeTabId: state.activeTabId,
      }),
    }
  )
)
