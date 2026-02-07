/**
 * DashboardCustomizer Component
 *
 * A modal component for customizing the dashboard layout.
 * Supports:
 * - Widget enable/disable toggles
 * - Widget ordering via up/down buttons
 * - Widget size selection
 * - Per-widget configuration
 *
 * Note: For drag-and-drop functionality, install @dnd-kit/core, @dnd-kit/sortable, @dnd-kit/utilities
 */

import React, { useState, useCallback, useEffect } from 'react'
import {
  Cog6ToothIcon,
  ArrowUpIcon,
  ArrowDownIcon,
  CheckIcon,
  ArrowPathIcon,
  EyeIcon,
  EyeSlashIcon,
  ChevronUpIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils/cn'
import { Modal } from './Modal'
import { Button } from '@/components/atoms/Button'
import {
  useDashboardStore,
  selectAllWidgets,
  type WidgetConfig,
} from '@/store/dashboard.store'
import { useWidgets } from '@/hooks/useDashboard'
import {
  saveDashboardPreferences,
  resetDashboardPreferences,
} from '@/services/dashboard.service'
import type { Widget, WidgetSize } from '@/types/dashboard'

/**
 * Size options for widgets
 */
const SIZE_OPTIONS: { value: WidgetSize; label: string; cols: string }[] = [
  { value: 'small', label: 'Small', cols: '1 column' },
  { value: 'medium', label: 'Medium', cols: '2 columns' },
  { value: 'large', label: 'Large', cols: '3 columns' },
  { value: 'full', label: 'Full Width', cols: '4 columns' },
]

/**
 * Get widget icon based on category
 */
function getWidgetIcon(category: string): React.ReactNode {
  switch (category) {
    case 'stats':
      return (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
      )
    case 'charts':
      return (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z" />
        </svg>
      )
    case 'lists':
      return (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
        </svg>
      )
    case 'actions':
      return (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      )
    case 'system':
      return (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      )
    default:
      return (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
        </svg>
      )
  }
}

/**
 * Props for WidgetItem
 */
interface WidgetItemProps {
  widgetConfig: WidgetConfig
  widgetDef: Widget | undefined
  index: number
  totalCount: number
  onToggle: (widgetId: string, enabled: boolean) => void
  onSizeChange: (widgetId: string, size: WidgetSize) => void
  onMoveUp: (index: number) => void
  onMoveDown: (index: number) => void
  onConfigChange: (widgetId: string, key: string, value: unknown) => void
}

/**
 * Widget item component
 */
function WidgetItem({
  widgetConfig,
  widgetDef,
  index,
  totalCount,
  onToggle,
  onSizeChange,
  onMoveUp,
  onMoveDown,
  onConfigChange,
}: WidgetItemProps) {
  const [showSettings, setShowSettings] = useState(false)

  const handleToggle = () => {
    onToggle(widgetConfig.widgetId, !widgetConfig.enabled)
  }

  return (
    <div
      className={cn(
        'bg-white dark:bg-gray-800 rounded-lg border transition-all duration-200',
        'border-[#DDDBDA] dark:border-gray-700',
        !widgetConfig.enabled && 'opacity-60'
      )}
    >
      {/* Main row */}
      <div className="flex items-center gap-3 p-4">
        {/* Move buttons */}
        <div className="flex flex-col gap-1">
          <button
            type="button"
            onClick={() => onMoveUp(index)}
            disabled={index === 0}
            className={cn(
              'p-1 rounded transition-colors',
              index === 0
                ? 'text-gray-300 cursor-not-allowed'
                : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700'
            )}
            title="Move up"
          >
            <ArrowUpIcon className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={() => onMoveDown(index)}
            disabled={index === totalCount - 1}
            className={cn(
              'p-1 rounded transition-colors',
              index === totalCount - 1
                ? 'text-gray-300 cursor-not-allowed'
                : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700'
            )}
            title="Move down"
          >
            <ArrowDownIcon className="w-4 h-4" />
          </button>
        </div>

        {/* Widget icon */}
        <div
          className={cn(
            'flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center',
            widgetConfig.enabled
              ? 'bg-[#0176d3]/10 text-[#0176d3]'
              : 'bg-gray-100 text-gray-400 dark:bg-gray-700'
          )}
        >
          {widgetDef ? getWidgetIcon(widgetDef.category) : null}
        </div>

        {/* Widget info */}
        <div className="flex-1 min-w-0">
          <h4 className="font-medium text-gray-900 dark:text-white truncate">
            {widgetDef?.name || widgetConfig.widgetId}
          </h4>
          <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
            {widgetDef?.description || 'Widget'}
          </p>
        </div>

        {/* Size selector */}
        <select
          value={widgetConfig.size}
          onChange={(e) => onSizeChange(widgetConfig.widgetId, e.target.value as WidgetSize)}
          className={cn(
            'px-3 py-1.5 text-sm rounded-md border border-[#DDDBDA] dark:border-gray-600',
            'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200',
            'focus:outline-none focus:ring-2 focus:ring-[#0176d3] focus:border-transparent'
          )}
          disabled={!widgetConfig.enabled}
        >
          {SIZE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>

        {/* Settings button */}
        {widgetDef?.configurable && (
          <button
            type="button"
            onClick={() => setShowSettings(!showSettings)}
            className={cn(
              'p-2 rounded-md transition-colors',
              showSettings
                ? 'bg-[#0176d3]/10 text-[#0176d3]'
                : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500'
            )}
            title="Widget settings"
            disabled={!widgetConfig.enabled}
          >
            {showSettings ? (
              <ChevronUpIcon className="w-5 h-5" />
            ) : (
              <Cog6ToothIcon className="w-5 h-5" />
            )}
          </button>
        )}

        {/* Toggle button */}
        <button
          type="button"
          onClick={handleToggle}
          className={cn(
            'p-2 rounded-md transition-colors',
            widgetConfig.enabled
              ? 'bg-green-100 text-green-600 hover:bg-green-200 dark:bg-green-900/30 dark:text-green-400'
              : 'bg-gray-100 text-gray-400 hover:bg-gray-200 dark:bg-gray-700'
          )}
          title={widgetConfig.enabled ? 'Hide widget' : 'Show widget'}
        >
          {widgetConfig.enabled ? (
            <EyeIcon className="w-5 h-5" />
          ) : (
            <EyeSlashIcon className="w-5 h-5" />
          )}
        </button>
      </div>

      {/* Settings panel */}
      {showSettings && widgetDef?.configurable && widgetConfig.enabled && (
        <div className="px-4 pb-4 pt-0">
          <div className="border-t border-[#DDDBDA] dark:border-gray-700 pt-4">
            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
              <h5 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                Widget Settings
              </h5>
              {widgetDef.config_options && widgetDef.config_options.length > 0 ? (
                <div className="space-y-3">
                  {widgetDef.config_options.map((option) => (
                    <div key={option.key} className="flex items-center justify-between">
                      <label className="text-sm text-gray-600 dark:text-gray-400">
                        {option.label}
                      </label>
                      {option.type === 'boolean' ? (
                        <input
                          type="checkbox"
                          checked={Boolean(widgetConfig.config[option.key] ?? option.default)}
                          onChange={(e) =>
                            onConfigChange(widgetConfig.widgetId, option.key, e.target.checked)
                          }
                          className="rounded border-gray-300 text-[#0176d3] focus:ring-[#0176d3]"
                        />
                      ) : option.type === 'select' && option.options ? (
                        <select
                          value={String(widgetConfig.config[option.key] ?? option.default)}
                          onChange={(e) =>
                            onConfigChange(widgetConfig.widgetId, option.key, e.target.value)
                          }
                          className="px-2 py-1 text-sm rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
                        >
                          {option.options.map((opt) => (
                            <option key={opt} value={opt}>
                              {opt}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <input
                          type={option.type === 'number' ? 'number' : 'text'}
                          value={String(widgetConfig.config[option.key] ?? option.default ?? '')}
                          onChange={(e) =>
                            onConfigChange(
                              widgetConfig.widgetId,
                              option.key,
                              option.type === 'number' ? Number(e.target.value) : e.target.value
                            )
                          }
                          min={option.min}
                          max={option.max}
                          className="px-2 py-1 text-sm rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 w-24"
                        />
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  No configurable options available.
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

/**
 * DashboardCustomizer props
 */
export interface DashboardCustomizerProps {
  isOpen: boolean
  onClose: () => void
}

/**
 * DashboardCustomizer component
 */
export function DashboardCustomizer({ isOpen, onClose }: DashboardCustomizerProps) {
  const {
    layout,
    pendingLayout,
    isSaving,
    setWidgetEnabled,
    setWidgetSize,
    setWidgetConfig,
    reorderWidgets,
    addWidget,
    resetToDefault,
    savePendingChanges,
    cancelEditing,
    setSaving,
    openCustomizer,
  } = useDashboardStore()

  const allWidgets = useDashboardStore(selectAllWidgets)
  const { data: availableWidgets, isLoading: isLoadingWidgets } = useWidgets({ includeAll: true })

  const [error, setError] = useState<string | null>(null)

  // Initialize pending layout when opening
  useEffect(() => {
    if (isOpen && !pendingLayout) {
      openCustomizer()
    }
  }, [isOpen, pendingLayout, openCustomizer])

  // Handle toggle widget
  const handleToggle = useCallback(
    (widgetId: string, enabled: boolean) => {
      setWidgetEnabled(widgetId, enabled)
    },
    [setWidgetEnabled]
  )

  // Handle size change
  const handleSizeChange = useCallback(
    (widgetId: string, size: WidgetSize) => {
      setWidgetSize(widgetId, size)
    },
    [setWidgetSize]
  )

  // Handle config change
  const handleConfigChange = useCallback(
    (widgetId: string, key: string, value: unknown) => {
      setWidgetConfig(widgetId, { [key]: value })
    },
    [setWidgetConfig]
  )

  // Handle move up
  const handleMoveUp = useCallback(
    (index: number) => {
      if (index > 0) {
        reorderWidgets(index, index - 1)
      }
    },
    [reorderWidgets]
  )

  // Handle move down
  const handleMoveDown = useCallback(
    (index: number) => {
      if (index < allWidgets.length - 1) {
        reorderWidgets(index, index + 1)
      }
    },
    [reorderWidgets, allWidgets.length]
  )

  // Handle save
  const handleSave = async () => {
    setError(null)
    setSaving(true)

    try {
      const layoutToSave = pendingLayout || layout
      await saveDashboardPreferences(layoutToSave)
      savePendingChanges()
      onClose()
    } catch (err) {
      console.error('Failed to save dashboard preferences:', err)
      setError('Failed to save preferences. Changes saved locally.')
      // Still save locally
      savePendingChanges()
    } finally {
      setSaving(false)
    }
  }

  // Handle cancel
  const handleCancel = () => {
    cancelEditing()
    onClose()
  }

  // Handle reset to default
  const handleReset = async () => {
    if (window.confirm('Reset dashboard to default layout? This cannot be undone.')) {
      setError(null)
      setSaving(true)

      try {
        await resetDashboardPreferences()
        resetToDefault()
      } catch (err) {
        console.error('Failed to reset preferences:', err)
        resetToDefault()
      } finally {
        setSaving(false)
      }
    }
  }

  // Get widget definition map
  const widgetDefMap = new Map<string, Widget>()
  availableWidgets?.forEach((w) => widgetDefMap.set(w.id, w))

  // Find widgets that are available but not in the current layout
  const missingWidgets = availableWidgets?.filter(
    (w) => !allWidgets.some((aw) => aw.widgetId === w.id) && w.has_access
  ) || []

  // Add missing widget
  const handleAddWidget = (widget: Widget) => {
    addWidget({
      widgetId: widget.id,
      enabled: true,
      position: allWidgets.length,
      size: (widget.default_size.w === 1
        ? 'small'
        : widget.default_size.w === 2
          ? 'medium'
          : widget.default_size.w === 3
            ? 'large'
            : 'full') as WidgetSize,
      config: {},
    })
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleCancel}
      title="Customize Dashboard"
      size="xl"
      footer={
        <>
          <Button
            variant="ghost"
            onClick={handleReset}
            disabled={isSaving}
            leftIcon={<ArrowPathIcon className="w-4 h-4" />}
          >
            Reset to Default
          </Button>
          <div className="flex-1" />
          <Button variant="secondary" onClick={handleCancel} disabled={isSaving}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleSave}
            isLoading={isSaving}
            leftIcon={<CheckIcon className="w-4 h-4" />}
          >
            Save Changes
          </Button>
        </>
      }
    >
      {error && (
        <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-800">
          {error}
        </div>
      )}

      <div className="mb-4">
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Reorder widgets using the arrow buttons, toggle visibility, and adjust sizes. Your preferences will be
          saved automatically.
        </p>
      </div>

      {/* Widget list */}
      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
          Dashboard Widgets
        </h3>

        {isLoadingWidgets ? (
          <div className="space-y-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <div
                key={i}
                className="h-20 bg-gray-100 dark:bg-gray-700 rounded-lg animate-pulse"
              />
            ))}
          </div>
        ) : (
          <div className="space-y-2">
            {allWidgets.map((widgetConfig, index) => (
              <WidgetItem
                key={widgetConfig.widgetId}
                widgetConfig={widgetConfig}
                widgetDef={widgetDefMap.get(widgetConfig.widgetId)}
                index={index}
                totalCount={allWidgets.length}
                onToggle={handleToggle}
                onSizeChange={handleSizeChange}
                onMoveUp={handleMoveUp}
                onMoveDown={handleMoveDown}
                onConfigChange={handleConfigChange}
              />
            ))}
          </div>
        )}
      </div>

      {/* Available widgets to add */}
      {missingWidgets.length > 0 && (
        <div className="mt-6 pt-6 border-t border-[#DDDBDA] dark:border-gray-700">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
            Available Widgets
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {missingWidgets.map((widget) => (
              <button
                type="button"
                key={widget.id}
                onClick={() => handleAddWidget(widget)}
                className={cn(
                  'flex items-center gap-3 p-3 rounded-lg border border-dashed',
                  'border-[#DDDBDA] dark:border-gray-600',
                  'hover:border-[#0176d3] hover:bg-[#0176d3]/5',
                  'transition-colors text-left'
                )}
              >
                <div className="w-8 h-8 rounded-lg bg-gray-100 dark:bg-gray-700 flex items-center justify-center text-gray-400">
                  {getWidgetIcon(widget.category)}
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate">
                    {widget.name}
                  </h4>
                  <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                    {widget.description}
                  </p>
                </div>
                <span className="text-[#0176d3] text-sm font-medium">+ Add</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Size legend */}
      <div className="mt-6 pt-4 border-t border-[#DDDBDA] dark:border-gray-700">
        <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">Size Legend</h4>
        <div className="flex flex-wrap gap-3">
          {SIZE_OPTIONS.map((option) => (
            <div key={option.value} className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400">
              <div
                className={cn(
                  'h-3 rounded bg-[#0176d3]/20',
                  option.value === 'small' && 'w-6',
                  option.value === 'medium' && 'w-12',
                  option.value === 'large' && 'w-18',
                  option.value === 'full' && 'w-24'
                )}
              />
              <span>{option.label}</span>
            </div>
          ))}
        </div>
      </div>
    </Modal>
  )
}

export default DashboardCustomizer
