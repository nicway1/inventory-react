/**
 * Settings Page
 *
 * User settings management page with:
 * - Theme preference (light/dark/system)
 * - Notification preferences
 * - Email notification settings
 * - Default dashboard layout
 * - Language/locale settings
 * - Security settings (2FA, sessions)
 */

import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  SunIcon,
  MoonIcon,
  ComputerDesktopIcon,
  BellIcon,
  BellSlashIcon,
  EnvelopeIcon,
  SpeakerWaveIcon,
  HomeIcon,
  ViewColumnsIcon,
  LanguageIcon,
  ShieldCheckIcon,
  DevicePhoneMobileIcon,
  ArrowRightOnRectangleIcon,
  TrashIcon,
  CheckIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils/cn'
import { useTheme, type Theme } from '@/providers/ThemeProvider'
import { usePreferencesStore } from '@/store/preferences.store'
import { useAuthStore } from '@/store/auth.store'
import { useUIStore } from '@/store/ui.store'
import { preferencesService, securityService } from '@/services/preferences.service'
import { PageLayout } from '@/components/templates/PageLayout'
import { Card, CardHeader, CardBody } from '@/components/molecules/Card'
import { Button } from '@/components/atoms/Button'
import { Select } from '@/components/atoms/Select'
import type { ActiveSession } from '@/types/preferences'

/**
 * Toggle Switch component
 */
function Toggle({
  checked,
  onChange,
  disabled = false,
  label,
}: {
  checked: boolean
  onChange: (checked: boolean) => void
  disabled?: boolean
  label?: string
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        'relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full',
        'border-2 border-transparent transition-colors duration-200 ease-in-out',
        'focus:outline-none focus:ring-2 focus:ring-[#0176D3] focus:ring-offset-2',
        'disabled:cursor-not-allowed disabled:opacity-50',
        checked ? 'bg-[#0176D3]' : 'bg-gray-200 dark:bg-gray-600'
      )}
    >
      <span
        className={cn(
          'pointer-events-none inline-block h-5 w-5 transform rounded-full',
          'bg-white shadow ring-0 transition duration-200 ease-in-out',
          checked ? 'translate-x-5' : 'translate-x-0'
        )}
      />
    </button>
  )
}

/**
 * Setting Row component
 */
function SettingRow({
  icon: Icon,
  iconColor,
  title,
  description,
  children,
}: {
  icon: React.ElementType
  iconColor: string
  title: string
  description: string
  children: React.ReactNode
}) {
  return (
    <div className="flex items-center justify-between py-4 border-b border-gray-100 dark:border-gray-800 last:border-0">
      <div className="flex items-start gap-4">
        <div className={cn('p-2 rounded-lg', iconColor)}>
          <Icon className="w-5 h-5" />
        </div>
        <div>
          <h4 className="text-sm font-medium text-gray-900 dark:text-white">{title}</h4>
          <p className="text-sm text-gray-500 dark:text-gray-400">{description}</p>
        </div>
      </div>
      <div className="flex-shrink-0 ml-4">{children}</div>
    </div>
  )
}

/**
 * Theme Option Card component
 */
function ThemeOption({
  value,
  icon: Icon,
  label,
  description,
  selected,
  onClick,
}: {
  value: Theme
  icon: React.ElementType
  label: string
  description: string
  selected: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'relative flex flex-col items-center p-4 rounded-lg border-2 transition-all',
        'hover:border-[#0176D3]/50 hover:bg-gray-50 dark:hover:bg-gray-800/50',
        'focus:outline-none focus:ring-2 focus:ring-[#0176D3] focus:ring-offset-2',
        selected
          ? 'border-[#0176D3] bg-blue-50 dark:bg-blue-900/20'
          : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800'
      )}
    >
      {selected && (
        <div className="absolute top-2 right-2">
          <CheckIcon className="w-5 h-5 text-[#0176D3]" />
        </div>
      )}
      <Icon
        className={cn(
          'w-8 h-8 mb-2',
          selected ? 'text-[#0176D3]' : 'text-gray-400 dark:text-gray-500'
        )}
      />
      <span
        className={cn(
          'text-sm font-medium',
          selected ? 'text-[#0176D3]' : 'text-gray-700 dark:text-gray-300'
        )}
      >
        {label}
      </span>
      <span className="text-xs text-gray-500 dark:text-gray-400 mt-1">{description}</span>
    </button>
  )
}

/**
 * Session Card component
 */
function SessionCard({
  session,
  onRevoke,
  isRevoking,
}: {
  session: ActiveSession
  onRevoke: (sessionId: string) => void
  isRevoking: boolean
}) {
  return (
    <div
      className={cn(
        'flex items-center justify-between p-4 rounded-lg border',
        session.is_current
          ? 'border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20'
          : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800'
      )}
    >
      <div className="flex items-start gap-3">
        <div
          className={cn(
            'p-2 rounded-lg',
            session.is_current
              ? 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400'
              : 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
          )}
        >
          <DevicePhoneMobileIcon className="w-5 h-5" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-900 dark:text-white">
              {session.browser} on {session.device}
            </span>
            {session.is_current && (
              <span className="px-2 py-0.5 text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-full">
                Current
              </span>
            )}
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {session.ip_address}
            {session.location && ` - ${session.location}`}
          </p>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
            Last active: {new Date(session.last_active).toLocaleString()}
          </p>
        </div>
      </div>
      {!session.is_current && (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onRevoke(session.id)}
          isLoading={isRevoking}
          leftIcon={<ArrowRightOnRectangleIcon className="w-4 h-4" />}
          className="text-red-600 hover:text-red-700 hover:bg-red-50 dark:text-red-400 dark:hover:text-red-300 dark:hover:bg-red-900/20"
        >
          Revoke
        </Button>
      )}
    </div>
  )
}

/**
 * Settings Page component
 */
export function SettingsPage() {
  const navigate = useNavigate()
  const { theme, setTheme } = useTheme()
  const { addToast } = useUIStore()
  const { user } = useAuthStore()
  const {
    notifications,
    layout,
    setNotifications,
    setLayout,
  } = usePreferencesStore()

  // State
  const [isSaving, setIsSaving] = useState(false)
  const [sessions, setSessions] = useState<ActiveSession[]>([])
  const [isLoadingSessions, setIsLoadingSessions] = useState(false)
  const [revokingSessionId, setRevokingSessionId] = useState<string | null>(null)
  const [isRevokingAll, setIsRevokingAll] = useState(false)

  // Load sessions on mount
  useEffect(() => {
    loadSessions()
  }, [])

  /**
   * Load active sessions
   */
  const loadSessions = async () => {
    setIsLoadingSessions(true)
    try {
      const response = await securityService.getActiveSessions()
      if (response.success) {
        setSessions(response.data)
      }
    } catch (error) {
      // Sessions API might not be available yet
      console.warn('Failed to load sessions:', error)
    } finally {
      setIsLoadingSessions(false)
    }
  }

  /**
   * Save preferences to API
   */
  const savePreferences = useCallback(
    async (
      type: 'theme' | 'notifications' | 'layout',
      data: Record<string, unknown>
    ) => {
      setIsSaving(true)
      try {
        const response = await preferencesService.updatePreferences({ [type]: data })
        if (response.success) {
          addToast({
            type: 'success',
            message: 'Preferences saved successfully.',
          })
        }
      } catch (error) {
        addToast({
          type: 'error',
          message: 'Failed to save preferences.',
        })
      } finally {
        setIsSaving(false)
      }
    },
    [addToast]
  )

  /**
   * Handle theme change
   */
  const handleThemeChange = (newTheme: Theme) => {
    setTheme(newTheme)
    // Map 'system' to 'auto' for API
    const apiTheme = newTheme === 'system' ? 'auto' : newTheme
    savePreferences('theme', { mode: apiTheme })
  }

  /**
   * Handle notification toggle
   */
  const handleNotificationToggle = (key: keyof typeof notifications, value: boolean) => {
    setNotifications({ [key]: value })
    savePreferences('notifications', { [key]: value })
  }

  /**
   * Handle layout change
   */
  const handleLayoutChange = (key: keyof typeof layout, value: string | boolean) => {
    setLayout({ [key]: value })
    savePreferences('layout', { [key]: value })
  }

  /**
   * Revoke a session
   */
  const handleRevokeSession = async (sessionId: string) => {
    setRevokingSessionId(sessionId)
    try {
      const response = await securityService.revokeSession(sessionId)
      if (response.success) {
        setSessions((prev) => prev.filter((s) => s.id !== sessionId))
        addToast({
          type: 'success',
          message: 'Session revoked successfully.',
        })
      }
    } catch (error) {
      addToast({
        type: 'error',
        message: 'Failed to revoke session.',
      })
    } finally {
      setRevokingSessionId(null)
    }
  }

  /**
   * Revoke all other sessions
   */
  const handleRevokeAllSessions = async () => {
    setIsRevokingAll(true)
    try {
      const response = await securityService.revokeAllSessions()
      if (response.success) {
        setSessions((prev) => prev.filter((s) => s.is_current))
        addToast({
          type: 'success',
          message: 'All other sessions revoked successfully.',
        })
      }
    } catch (error) {
      addToast({
        type: 'error',
        message: 'Failed to revoke sessions.',
      })
    } finally {
      setIsRevokingAll(false)
    }
  }

  return (
    <PageLayout
      title="Settings"
      subtitle="Manage your preferences and security settings"
      breadcrumbs={[{ label: 'Settings' }]}
    >
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Theme Settings */}
        <Card>
          <CardHeader>Appearance</CardHeader>
          <CardBody>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              Choose how TrueLog looks to you. Select a single theme, or sync with your system.
            </p>
            <div className="grid grid-cols-3 gap-4">
              <ThemeOption
                value="light"
                icon={SunIcon}
                label="Light"
                description="Always use light theme"
                selected={theme === 'light'}
                onClick={() => handleThemeChange('light')}
              />
              <ThemeOption
                value="dark"
                icon={MoonIcon}
                label="Dark"
                description="Always use dark theme"
                selected={theme === 'dark'}
                onClick={() => handleThemeChange('dark')}
              />
              <ThemeOption
                value="system"
                icon={ComputerDesktopIcon}
                label="System"
                description="Sync with OS setting"
                selected={theme === 'system'}
                onClick={() => handleThemeChange('system')}
              />
            </div>
          </CardBody>
        </Card>

        {/* Notification Settings */}
        <Card>
          <CardHeader>Notifications</CardHeader>
          <CardBody className="py-0">
            <SettingRow
              icon={BellIcon}
              iconColor="bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
              title="In-App Notifications"
              description="Receive notifications within the application"
            >
              <Toggle
                checked={notifications.in_app_enabled}
                onChange={(checked) => handleNotificationToggle('in_app_enabled', checked)}
                label="Toggle in-app notifications"
              />
            </SettingRow>
            <SettingRow
              icon={EnvelopeIcon}
              iconColor="bg-green-50 dark:bg-green-900/30 text-green-600 dark:text-green-400"
              title="Email Notifications"
              description="Receive important updates via email"
            >
              <Toggle
                checked={notifications.email_enabled}
                onChange={(checked) => handleNotificationToggle('email_enabled', checked)}
                label="Toggle email notifications"
              />
            </SettingRow>
            <SettingRow
              icon={SpeakerWaveIcon}
              iconColor="bg-purple-50 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400"
              title="Sound Notifications"
              description="Play sounds for new notifications"
            >
              <Toggle
                checked={notifications.sound_enabled}
                onChange={(checked) => handleNotificationToggle('sound_enabled', checked)}
                label="Toggle sound notifications"
              />
            </SettingRow>
          </CardBody>
        </Card>

        {/* Layout Settings */}
        <Card>
          <CardHeader>Layout Preferences</CardHeader>
          <CardBody className="py-0">
            <SettingRow
              icon={HomeIcon}
              iconColor="bg-orange-50 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400"
              title="Default Homepage"
              description="Choose your default landing page"
            >
              <Select
                options={[
                  { value: 'dashboard', label: 'Dashboard' },
                  { value: 'tickets', label: 'Tickets' },
                  { value: 'inventory', label: 'Inventory' },
                ]}
                value={layout.default_homepage}
                onChange={(e) => handleLayoutChange('default_homepage', e.target.value)}
                className="w-40"
              />
            </SettingRow>
            <SettingRow
              icon={ViewColumnsIcon}
              iconColor="bg-cyan-50 dark:bg-cyan-900/30 text-cyan-600 dark:text-cyan-400"
              title="Default Ticket View"
              description="Choose your preferred ticket list style"
            >
              <Select
                options={[
                  { value: 'sf', label: 'Salesforce Style' },
                  { value: 'classic', label: 'Classic Table' },
                ]}
                value={layout.default_ticket_view}
                onChange={(e) => handleLayoutChange('default_ticket_view', e.target.value)}
                className="w-40"
              />
            </SettingRow>
            <SettingRow
              icon={ViewColumnsIcon}
              iconColor="bg-teal-50 dark:bg-teal-900/30 text-teal-600 dark:text-teal-400"
              title="Default Inventory View"
              description="Choose your preferred inventory list style"
            >
              <Select
                options={[
                  { value: 'sf', label: 'Salesforce Style' },
                  { value: 'classic', label: 'Classic Table' },
                ]}
                value={layout.default_inventory_view}
                onChange={(e) => handleLayoutChange('default_inventory_view', e.target.value)}
                className="w-40"
              />
            </SettingRow>
            <SettingRow
              icon={ViewColumnsIcon}
              iconColor="bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400"
              title="Compact Mode"
              description="Use condensed spacing throughout the app"
            >
              <Toggle
                checked={layout.compact_mode}
                onChange={(checked) => handleLayoutChange('compact_mode', checked)}
                label="Toggle compact mode"
              />
            </SettingRow>
          </CardBody>
        </Card>

        {/* Language Settings */}
        <Card>
          <CardHeader>Language & Region</CardHeader>
          <CardBody className="py-0">
            <SettingRow
              icon={LanguageIcon}
              iconColor="bg-pink-50 dark:bg-pink-900/30 text-pink-600 dark:text-pink-400"
              title="Language"
              description="Choose your preferred language"
            >
              <Select
                options={[
                  { value: 'en', label: 'English' },
                  { value: 'es', label: 'Spanish' },
                  { value: 'fr', label: 'French' },
                  { value: 'de', label: 'German' },
                ]}
                value="en"
                onChange={() => {
                  addToast({
                    type: 'info',
                    message: 'Language selection will be available in a future update.',
                  })
                }}
                className="w-40"
              />
            </SettingRow>
          </CardBody>
        </Card>

        {/* Security Settings */}
        <Card>
          <CardHeader
            action={
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/profile')}
                leftIcon={<ShieldCheckIcon className="w-4 h-4" />}
              >
                Manage Password
              </Button>
            }
          >
            Security
          </CardHeader>
          <CardBody>
            {/* Two-Factor Authentication Info */}
            <div className="mb-6 p-4 rounded-lg bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800">
              <div className="flex items-start gap-3">
                <ExclamationTriangleIcon className="w-5 h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                    Two-Factor Authentication
                  </h4>
                  <p className="text-sm text-yellow-700 dark:text-yellow-300 mt-1">
                    Two-factor authentication is not currently enabled. Enable 2FA to add an extra
                    layer of security to your account.
                  </p>
                  <Button variant="secondary" size="sm" className="mt-3" disabled>
                    Enable 2FA (Coming Soon)
                  </Button>
                </div>
              </div>
            </div>

            {/* Active Sessions */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h4 className="text-sm font-medium text-gray-900 dark:text-white">
                  Active Sessions
                </h4>
                {sessions.length > 1 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleRevokeAllSessions}
                    isLoading={isRevokingAll}
                    leftIcon={<TrashIcon className="w-4 h-4" />}
                    className="text-red-600 hover:text-red-700 hover:bg-red-50 dark:text-red-400 dark:hover:text-red-300"
                  >
                    Revoke All Others
                  </Button>
                )}
              </div>

              {isLoadingSessions ? (
                <div className="flex items-center justify-center py-8">
                  <div className="w-8 h-8 border-2 border-[#0176D3] border-t-transparent rounded-full animate-spin" />
                </div>
              ) : sessions.length > 0 ? (
                <div className="space-y-3">
                  {sessions.map((session) => (
                    <SessionCard
                      key={session.id}
                      session={session}
                      onRevoke={handleRevokeSession}
                      isRevoking={revokingSessionId === session.id}
                    />
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <DevicePhoneMobileIcon className="w-12 h-12 text-gray-400 dark:text-gray-500 mx-auto mb-4" />
                  <p className="text-gray-500 dark:text-gray-400">
                    Session management will be available in a future update.
                  </p>
                </div>
              )}
            </div>
          </CardBody>
        </Card>

        {/* Danger Zone */}
        <Card>
          <CardHeader>
            <span className="text-red-600 dark:text-red-400">Danger Zone</span>
          </CardHeader>
          <CardBody>
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-medium text-gray-900 dark:text-white">
                  Delete Account
                </h4>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Permanently delete your account and all associated data. This action cannot be
                  undone.
                </p>
              </div>
              <Button
                variant="danger"
                onClick={() => {
                  addToast({
                    type: 'info',
                    title: 'Contact Support',
                    message: 'Please contact support to delete your account.',
                  })
                }}
              >
                Delete Account
              </Button>
            </div>
          </CardBody>
        </Card>
      </div>
    </PageLayout>
  )
}

export default SettingsPage
