/**
 * Store Index
 *
 * Export all Zustand stores from this file.
 */

export { useAuthStore } from './auth.store'
export { useUIStore } from './ui.store'
export { useTabStore, type Tab, type TabIconType } from './tabs.store'
export {
  useDashboardStore,
  selectEnabledWidgets,
  selectAllWidgets,
  selectWidgetConfig,
  type WidgetConfig,
  type DashboardLayout,
} from './dashboard.store'
export { usePreferencesStore, useSyncPreferences } from './preferences.store'
export {
  useNotificationsStore,
  useUnreadCount,
  useNotifications,
} from './notifications.store'
