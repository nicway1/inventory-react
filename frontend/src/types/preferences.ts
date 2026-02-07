/**
 * User Preferences Types
 *
 * Type definitions for user preferences and profile settings.
 */

/**
 * Theme preferences
 */
export interface ThemePreferences {
  mode: 'light' | 'dark' | 'auto'
  primary_color: string
  sidebar_style: 'expanded' | 'compact' | 'hidden'
}

/**
 * Layout preferences
 */
export interface LayoutPreferences {
  default_homepage: 'dashboard' | 'tickets' | 'inventory'
  default_ticket_view: 'classic' | 'sf'
  default_inventory_view: 'classic' | 'sf'
  sidebar_collapsed: boolean
  compact_mode: boolean
}

/**
 * Notification preferences
 */
export interface NotificationPreferences {
  email_enabled: boolean
  in_app_enabled: boolean
  sound_enabled: boolean
}

/**
 * Full user preferences object
 */
export interface UserPreferences {
  theme: ThemePreferences
  layout: LayoutPreferences
  notifications: NotificationPreferences
}

/**
 * Preference options available from the API
 */
export interface PreferenceOptions {
  theme_modes: string[]
  primary_colors: Array<{ name: string; value: string }>
  sidebar_styles: string[]
  homepage_options: string[]
  view_options: string[]
}

/**
 * User profile update request
 */
export interface UpdateProfileRequest {
  full_name?: string
  email?: string
  username?: string
}

/**
 * Password change request
 */
export interface ChangePasswordRequest {
  current_password: string
  new_password: string
  confirm_password: string
}

/**
 * Profile picture upload response
 */
export interface ProfilePictureResponse {
  success: boolean
  data: {
    avatar_url: string
  }
  message?: string
}

/**
 * API response wrapper for preferences
 */
export interface PreferencesResponse {
  success: boolean
  data: UserPreferences
  message?: string
}

/**
 * API response wrapper for preference options
 */
export interface PreferenceOptionsResponse {
  success: boolean
  data: PreferenceOptions
  message?: string
}

/**
 * Active session information
 */
export interface ActiveSession {
  id: string
  device: string
  browser: string
  ip_address: string
  last_active: string
  is_current: boolean
  location?: string
}

/**
 * Sessions response
 */
export interface SessionsResponse {
  success: boolean
  data: ActiveSession[]
  message?: string
}
