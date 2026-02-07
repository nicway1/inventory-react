/**
 * User Preferences Service
 *
 * Handles all user preferences and profile-related API calls.
 */

import { apiClient } from './api'
import type {
  UserPreferences,
  PreferenceOptions,
  PreferencesResponse,
  PreferenceOptionsResponse,
  UpdateProfileRequest,
  ChangePasswordRequest,
  ProfilePictureResponse,
  SessionsResponse,
} from '@/types/preferences'
import type { User, CurrentUserResponse } from '@/types/auth'

const PREFERENCES_BASE_URL = '/v2/user/preferences'
const USER_BASE_URL = '/v2/user'
const AUTH_BASE_URL = '/v2/auth'

/**
 * User preferences service for managing user settings
 */
export const preferencesService = {
  /**
   * Get current user's preferences
   */
  async getPreferences(): Promise<PreferencesResponse> {
    const response = await apiClient.get<PreferencesResponse>(PREFERENCES_BASE_URL)
    return response.data
  },

  /**
   * Update user preferences (partial update supported)
   */
  async updatePreferences(
    preferences: Partial<UserPreferences>
  ): Promise<PreferencesResponse> {
    const response = await apiClient.put<PreferencesResponse>(
      PREFERENCES_BASE_URL,
      preferences
    )
    return response.data
  },

  /**
   * Get available preference options
   */
  async getPreferenceOptions(): Promise<PreferenceOptionsResponse> {
    const response = await apiClient.get<PreferenceOptionsResponse>(
      `${PREFERENCES_BASE_URL}/options`
    )
    return response.data
  },

  /**
   * Update theme preferences
   */
  async updateThemePreferences(
    theme: Partial<UserPreferences['theme']>
  ): Promise<PreferencesResponse> {
    return this.updatePreferences({ theme })
  },

  /**
   * Update layout preferences
   */
  async updateLayoutPreferences(
    layout: Partial<UserPreferences['layout']>
  ): Promise<PreferencesResponse> {
    return this.updatePreferences({ layout })
  },

  /**
   * Update notification preferences
   */
  async updateNotificationPreferences(
    notifications: Partial<UserPreferences['notifications']>
  ): Promise<PreferencesResponse> {
    return this.updatePreferences({ notifications })
  },
}

/**
 * User profile service for managing user profile
 */
export const profileService = {
  /**
   * Get current user's profile
   */
  async getProfile(): Promise<CurrentUserResponse> {
    const response = await apiClient.get<CurrentUserResponse>(`${AUTH_BASE_URL}/me`)
    return response.data
  },

  /**
   * Update user profile
   */
  async updateProfile(
    data: UpdateProfileRequest
  ): Promise<{ success: boolean; data: User; message?: string }> {
    const response = await apiClient.put<{ success: boolean; data: User; message?: string }>(
      `${USER_BASE_URL}/profile`,
      data
    )
    return response.data
  },

  /**
   * Change password
   */
  async changePassword(
    data: ChangePasswordRequest
  ): Promise<{ success: boolean; message?: string }> {
    const response = await apiClient.post<{ success: boolean; message?: string }>(
      `${USER_BASE_URL}/change-password`,
      data
    )
    return response.data
  },

  /**
   * Upload profile picture
   */
  async uploadProfilePicture(file: File): Promise<ProfilePictureResponse> {
    const formData = new FormData()
    formData.append('avatar', file)

    const response = await apiClient.post<ProfilePictureResponse>(
      `${USER_BASE_URL}/avatar`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    )
    return response.data
  },

  /**
   * Delete profile picture
   */
  async deleteProfilePicture(): Promise<{ success: boolean; message?: string }> {
    const response = await apiClient.delete<{ success: boolean; message?: string }>(
      `${USER_BASE_URL}/avatar`
    )
    return response.data
  },
}

/**
 * Security service for managing security settings
 */
export const securityService = {
  /**
   * Get active sessions
   */
  async getActiveSessions(): Promise<SessionsResponse> {
    const response = await apiClient.get<SessionsResponse>(`${USER_BASE_URL}/sessions`)
    return response.data
  },

  /**
   * Revoke a session
   */
  async revokeSession(sessionId: string): Promise<{ success: boolean; message?: string }> {
    const response = await apiClient.delete<{ success: boolean; message?: string }>(
      `${USER_BASE_URL}/sessions/${sessionId}`
    )
    return response.data
  },

  /**
   * Revoke all sessions except current
   */
  async revokeAllSessions(): Promise<{ success: boolean; message?: string }> {
    const response = await apiClient.post<{ success: boolean; message?: string }>(
      `${USER_BASE_URL}/sessions/revoke-all`
    )
    return response.data
  },

  /**
   * Enable two-factor authentication
   */
  async enableTwoFactor(): Promise<{
    success: boolean
    data: { qr_code: string; secret: string }
    message?: string
  }> {
    const response = await apiClient.post<{
      success: boolean
      data: { qr_code: string; secret: string }
      message?: string
    }>(`${USER_BASE_URL}/2fa/enable`)
    return response.data
  },

  /**
   * Verify two-factor authentication
   */
  async verifyTwoFactor(
    code: string
  ): Promise<{ success: boolean; message?: string }> {
    const response = await apiClient.post<{ success: boolean; message?: string }>(
      `${USER_BASE_URL}/2fa/verify`,
      { code }
    )
    return response.data
  },

  /**
   * Disable two-factor authentication
   */
  async disableTwoFactor(
    password: string
  ): Promise<{ success: boolean; message?: string }> {
    const response = await apiClient.post<{ success: boolean; message?: string }>(
      `${USER_BASE_URL}/2fa/disable`,
      { password }
    )
    return response.data
  },
}

export default {
  ...preferencesService,
  ...profileService,
  ...securityService,
}
