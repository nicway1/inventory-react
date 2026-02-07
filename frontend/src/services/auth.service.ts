/**
 * Authentication Service
 *
 * Handles all authentication-related API calls.
 */

import { apiClient } from './api'
import type {
  LoginRequest,
  LoginResponse,
  RefreshTokenResponse,
  CurrentUserResponse,
} from '@/types/auth'

const AUTH_BASE_URL = '/v2/auth'

/**
 * Authentication service for handling login, logout, and token management
 */
export const authService = {
  /**
   * Login with username and password
   */
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await apiClient.post<LoginResponse>(
      `${AUTH_BASE_URL}/login`,
      credentials
    )
    return response.data
  },

  /**
   * Logout the current user
   */
  async logout(): Promise<void> {
    await apiClient.post(`${AUTH_BASE_URL}/logout`)
  },

  /**
   * Refresh the authentication token
   */
  async refreshToken(): Promise<RefreshTokenResponse> {
    const response = await apiClient.post<RefreshTokenResponse>(
      `${AUTH_BASE_URL}/refresh`
    )
    return response.data
  },

  /**
   * Get the current authenticated user
   */
  async getCurrentUser(): Promise<CurrentUserResponse> {
    const response = await apiClient.get<CurrentUserResponse>(
      `${AUTH_BASE_URL}/me`
    )
    return response.data
  },
}

export default authService
