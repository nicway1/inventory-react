/**
 * Dashboard Store
 *
 * Manages dashboard widget configuration state using Zustand with persistence.
 * Supports widget enable/disable, ordering, sizing, and per-widget configuration.
 */

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import type { WidgetSize } from '@/types/dashboard'

/**
 * Widget configuration for a single widget
 */
export interface WidgetConfig {
  widgetId: string
  enabled: boolean
  position: number
  size: WidgetSize
  config: Record<string, unknown>
}

/**
 * Dashboard layout state
 */
export interface DashboardLayout {
  widgets: WidgetConfig[]
  lastUpdated: string | null
}

/**
 * Dashboard state interface
 */
interface DashboardState {
  // State
  layout: DashboardLayout
  isCustomizing: boolean
  isSaving: boolean
  hasUnsavedChanges: boolean
  pendingLayout: DashboardLayout | null

  // Actions
  setLayout: (layout: DashboardLayout) => void
  setWidgetEnabled: (widgetId: string, enabled: boolean) => void
  setWidgetSize: (widgetId: string, size: WidgetSize) => void
  setWidgetPosition: (widgetId: string, position: number) => void
  setWidgetConfig: (widgetId: string, config: Record<string, unknown>) => void
  reorderWidgets: (startIndex: number, endIndex: number) => void
  addWidget: (widget: WidgetConfig) => void
  removeWidget: (widgetId: string) => void
  resetToDefault: () => void

  // Customization mode
  openCustomizer: () => void
  closeCustomizer: () => void
  startEditing: () => void
  cancelEditing: () => void
  savePendingChanges: () => void

  // Persistence
  setSaving: (isSaving: boolean) => void
  markAsSaved: () => void
}

/**
 * Default dashboard layout
 */
const DEFAULT_LAYOUT: DashboardLayout = {
  widgets: [
    { widgetId: 'inventory_stats', enabled: true, position: 0, size: 'small', config: {} },
    { widgetId: 'ticket_stats', enabled: true, position: 1, size: 'small', config: {} },
    { widgetId: 'customer_stats', enabled: true, position: 2, size: 'small', config: {} },
    { widgetId: 'quick_actions', enabled: true, position: 3, size: 'small', config: {} },
    { widgetId: 'queue_stats', enabled: true, position: 4, size: 'medium', config: {} },
    { widgetId: 'weekly_tickets_chart', enabled: true, position: 5, size: 'medium', config: {} },
    { widgetId: 'asset_status_chart', enabled: true, position: 6, size: 'medium', config: {} },
    { widgetId: 'recent_activities', enabled: true, position: 7, size: 'medium', config: {} },
    { widgetId: 'recent_tickets', enabled: true, position: 8, size: 'full', config: {} },
  ],
  lastUpdated: null,
}

/**
 * Storage key for localStorage
 */
const STORAGE_KEY = 'truelog-dashboard-layout'

/**
 * Dashboard store with Zustand
 */
export const useDashboardStore = create<DashboardState>()(
  persist(
    (set, get) => ({
      // Initial state
      layout: DEFAULT_LAYOUT,
      isCustomizing: false,
      isSaving: false,
      hasUnsavedChanges: false,
      pendingLayout: null,

      // Set entire layout
      setLayout: (layout) =>
        set({
          layout: {
            ...layout,
            lastUpdated: new Date().toISOString(),
          },
          hasUnsavedChanges: false,
        }),

      // Toggle widget enabled state
      setWidgetEnabled: (widgetId, enabled) =>
        set((state) => {
          const targetLayout = state.pendingLayout || state.layout
          const widgets = targetLayout.widgets.map((w) =>
            w.widgetId === widgetId ? { ...w, enabled } : w
          )
          const newLayout = { ...targetLayout, widgets }

          if (state.pendingLayout) {
            return { pendingLayout: newLayout, hasUnsavedChanges: true }
          }
          return {
            layout: { ...newLayout, lastUpdated: new Date().toISOString() },
            hasUnsavedChanges: true,
          }
        }),

      // Set widget size
      setWidgetSize: (widgetId, size) =>
        set((state) => {
          const targetLayout = state.pendingLayout || state.layout
          const widgets = targetLayout.widgets.map((w) =>
            w.widgetId === widgetId ? { ...w, size } : w
          )
          const newLayout = { ...targetLayout, widgets }

          if (state.pendingLayout) {
            return { pendingLayout: newLayout, hasUnsavedChanges: true }
          }
          return {
            layout: { ...newLayout, lastUpdated: new Date().toISOString() },
            hasUnsavedChanges: true,
          }
        }),

      // Set widget position
      setWidgetPosition: (widgetId, position) =>
        set((state) => {
          const targetLayout = state.pendingLayout || state.layout
          const widgets = targetLayout.widgets.map((w) =>
            w.widgetId === widgetId ? { ...w, position } : w
          )
          const newLayout = { ...targetLayout, widgets }

          if (state.pendingLayout) {
            return { pendingLayout: newLayout, hasUnsavedChanges: true }
          }
          return {
            layout: { ...newLayout, lastUpdated: new Date().toISOString() },
            hasUnsavedChanges: true,
          }
        }),

      // Set widget-specific configuration
      setWidgetConfig: (widgetId, config) =>
        set((state) => {
          const targetLayout = state.pendingLayout || state.layout
          const widgets = targetLayout.widgets.map((w) =>
            w.widgetId === widgetId ? { ...w, config: { ...w.config, ...config } } : w
          )
          const newLayout = { ...targetLayout, widgets }

          if (state.pendingLayout) {
            return { pendingLayout: newLayout, hasUnsavedChanges: true }
          }
          return {
            layout: { ...newLayout, lastUpdated: new Date().toISOString() },
            hasUnsavedChanges: true,
          }
        }),

      // Reorder widgets (drag-and-drop)
      reorderWidgets: (startIndex, endIndex) =>
        set((state) => {
          const targetLayout = state.pendingLayout || state.layout
          const widgets = [...targetLayout.widgets]
          const [removed] = widgets.splice(startIndex, 1)
          widgets.splice(endIndex, 0, removed)

          // Update positions
          const reorderedWidgets = widgets.map((w, index) => ({
            ...w,
            position: index,
          }))

          const newLayout = { ...targetLayout, widgets: reorderedWidgets }

          if (state.pendingLayout) {
            return { pendingLayout: newLayout, hasUnsavedChanges: true }
          }
          return {
            layout: { ...newLayout, lastUpdated: new Date().toISOString() },
            hasUnsavedChanges: true,
          }
        }),

      // Add a new widget
      addWidget: (widget) =>
        set((state) => {
          const targetLayout = state.pendingLayout || state.layout
          const maxPosition = Math.max(...targetLayout.widgets.map((w) => w.position), -1)
          const newWidget = { ...widget, position: maxPosition + 1 }
          const widgets = [...targetLayout.widgets, newWidget]
          const newLayout = { ...targetLayout, widgets }

          if (state.pendingLayout) {
            return { pendingLayout: newLayout, hasUnsavedChanges: true }
          }
          return {
            layout: { ...newLayout, lastUpdated: new Date().toISOString() },
            hasUnsavedChanges: true,
          }
        }),

      // Remove a widget
      removeWidget: (widgetId) =>
        set((state) => {
          const targetLayout = state.pendingLayout || state.layout
          const widgets = targetLayout.widgets
            .filter((w) => w.widgetId !== widgetId)
            .map((w, index) => ({ ...w, position: index }))
          const newLayout = { ...targetLayout, widgets }

          if (state.pendingLayout) {
            return { pendingLayout: newLayout, hasUnsavedChanges: true }
          }
          return {
            layout: { ...newLayout, lastUpdated: new Date().toISOString() },
            hasUnsavedChanges: true,
          }
        }),

      // Reset to default layout
      resetToDefault: () =>
        set((state) => {
          if (state.pendingLayout) {
            return { pendingLayout: DEFAULT_LAYOUT, hasUnsavedChanges: true }
          }
          return {
            layout: { ...DEFAULT_LAYOUT, lastUpdated: new Date().toISOString() },
            hasUnsavedChanges: true,
          }
        }),

      // Open customizer modal
      openCustomizer: () =>
        set((state) => ({
          isCustomizing: true,
          pendingLayout: { ...state.layout },
        })),

      // Close customizer modal
      closeCustomizer: () =>
        set({
          isCustomizing: false,
          pendingLayout: null,
          hasUnsavedChanges: false,
        }),

      // Start editing (create pending state)
      startEditing: () =>
        set((state) => ({
          pendingLayout: { ...state.layout },
        })),

      // Cancel editing (discard pending changes)
      cancelEditing: () =>
        set({
          pendingLayout: null,
          hasUnsavedChanges: false,
          isCustomizing: false,
        }),

      // Save pending changes to main layout
      savePendingChanges: () =>
        set((state) => {
          if (state.pendingLayout) {
            return {
              layout: {
                ...state.pendingLayout,
                lastUpdated: new Date().toISOString(),
              },
              pendingLayout: null,
              hasUnsavedChanges: false,
              isCustomizing: false,
            }
          }
          return { isCustomizing: false }
        }),

      // Set saving state
      setSaving: (isSaving) => set({ isSaving }),

      // Mark layout as saved (after API sync)
      markAsSaved: () =>
        set((state) => ({
          layout: {
            ...state.layout,
            lastUpdated: new Date().toISOString(),
          },
          hasUnsavedChanges: false,
        })),
    }),
    {
      name: STORAGE_KEY,
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        layout: state.layout,
      }),
    }
  )
)

/**
 * Selector for enabled widgets sorted by position
 */
export const selectEnabledWidgets = (state: DashboardState): WidgetConfig[] => {
  const layout = state.pendingLayout || state.layout
  return layout.widgets
    .filter((w) => w.enabled)
    .sort((a, b) => a.position - b.position)
}

/**
 * Selector for all widgets sorted by position
 */
export const selectAllWidgets = (state: DashboardState): WidgetConfig[] => {
  const layout = state.pendingLayout || state.layout
  return [...layout.widgets].sort((a, b) => a.position - b.position)
}

/**
 * Selector for a specific widget config
 */
export const selectWidgetConfig = (
  state: DashboardState,
  widgetId: string
): WidgetConfig | undefined => {
  const layout = state.pendingLayout || state.layout
  return layout.widgets.find((w) => w.widgetId === widgetId)
}

export default useDashboardStore
