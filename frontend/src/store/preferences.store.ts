/**
 * User Preferences Store
 *
 * Manages user preferences state using Zustand with persistence.
 */

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import type {
  UserPreferences,
  ThemePreferences,
  LayoutPreferences,
  NotificationPreferences,
  PreferenceOptions,
} from '@/types/preferences'

/**
 * Default preferences
 */
const DEFAULT_THEME: ThemePreferences = {
  mode: 'light',
  primary_color: '#1976D2',
  sidebar_style: 'expanded',
}

const DEFAULT_LAYOUT: LayoutPreferences = {
  default_homepage: 'dashboard',
  default_ticket_view: 'sf',
  default_inventory_view: 'sf',
  sidebar_collapsed: false,
  compact_mode: false,
}

const DEFAULT_NOTIFICATIONS: NotificationPreferences = {
  email_enabled: true,
  in_app_enabled: true,
  sound_enabled: false,
}

/**
 * Preferences state interface
 */
interface PreferencesState {
  // State
  theme: ThemePreferences
  layout: LayoutPreferences
  notifications: NotificationPreferences
  options: PreferenceOptions | null
  isLoading: boolean
  isSynced: boolean

  // Actions
  setTheme: (theme: Partial<ThemePreferences>) => void
  setLayout: (layout: Partial<LayoutPreferences>) => void
  setNotifications: (notifications: Partial<NotificationPreferences>) => void
  setPreferences: (preferences: Partial<UserPreferences>) => void
  setOptions: (options: PreferenceOptions) => void
  setLoading: (loading: boolean) => void
  setSynced: (synced: boolean) => void
  resetToDefaults: () => void

  // Getters
  getThemeMode: () => 'light' | 'dark' | 'auto'
  getPrimaryColor: () => string
  getSidebarStyle: () => 'expanded' | 'compact' | 'hidden'
  getDefaultHomepage: () => 'dashboard' | 'tickets' | 'inventory'
  isEmailNotificationsEnabled: () => boolean
  isInAppNotificationsEnabled: () => boolean
  isSoundEnabled: () => boolean
}

/**
 * Preferences store with Zustand
 */
export const usePreferencesStore = create<PreferencesState>()(
  persist(
    (set, get) => ({
      // Initial state
      theme: DEFAULT_THEME,
      layout: DEFAULT_LAYOUT,
      notifications: DEFAULT_NOTIFICATIONS,
      options: null,
      isLoading: false,
      isSynced: false,

      // Set theme preferences
      setTheme: (theme) =>
        set((state) => ({
          theme: { ...state.theme, ...theme },
          isSynced: false,
        })),

      // Set layout preferences
      setLayout: (layout) =>
        set((state) => ({
          layout: { ...state.layout, ...layout },
          isSynced: false,
        })),

      // Set notification preferences
      setNotifications: (notifications) =>
        set((state) => ({
          notifications: { ...state.notifications, ...notifications },
          isSynced: false,
        })),

      // Set all preferences at once
      setPreferences: (preferences) =>
        set((state) => ({
          theme: preferences.theme ? { ...state.theme, ...preferences.theme } : state.theme,
          layout: preferences.layout ? { ...state.layout, ...preferences.layout } : state.layout,
          notifications: preferences.notifications
            ? { ...state.notifications, ...preferences.notifications }
            : state.notifications,
          isSynced: true,
        })),

      // Set preference options
      setOptions: (options) =>
        set({ options }),

      // Set loading state
      setLoading: (loading) =>
        set({ isLoading: loading }),

      // Set synced state
      setSynced: (synced) =>
        set({ isSynced: synced }),

      // Reset to defaults
      resetToDefaults: () =>
        set({
          theme: DEFAULT_THEME,
          layout: DEFAULT_LAYOUT,
          notifications: DEFAULT_NOTIFICATIONS,
          isSynced: false,
        }),

      // Getters
      getThemeMode: () => get().theme.mode,
      getPrimaryColor: () => get().theme.primary_color,
      getSidebarStyle: () => get().theme.sidebar_style,
      getDefaultHomepage: () => get().layout.default_homepage,
      isEmailNotificationsEnabled: () => get().notifications.email_enabled,
      isInAppNotificationsEnabled: () => get().notifications.in_app_enabled,
      isSoundEnabled: () => get().notifications.sound_enabled,
    }),
    {
      name: 'truelog-preferences',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        theme: state.theme,
        layout: state.layout,
        notifications: state.notifications,
      }),
    }
  )
)

/**
 * Hook to sync preferences with API
 */
export function useSyncPreferences() {
  const { setPreferences, setOptions, setLoading, setSynced } = usePreferencesStore()

  const syncFromApi = async (
    getPreferences: () => Promise<{ success: boolean; data: UserPreferences }>,
    getOptions?: () => Promise<{ success: boolean; data: PreferenceOptions }>
  ) => {
    setLoading(true)
    try {
      const [prefsResponse, optionsResponse] = await Promise.all([
        getPreferences(),
        getOptions?.(),
      ])

      if (prefsResponse.success) {
        setPreferences(prefsResponse.data)
      }

      if (optionsResponse?.success) {
        setOptions(optionsResponse.data)
      }

      setSynced(true)
    } catch (error) {
      console.error('Failed to sync preferences:', error)
    } finally {
      setLoading(false)
    }
  }

  return { syncFromApi }
}
