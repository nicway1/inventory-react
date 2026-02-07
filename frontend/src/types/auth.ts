/**
 * Authentication Types
 *
 * Type definitions for authentication-related entities.
 */

/**
 * User type enum representing different user roles in the system
 */
export type UserType = 'SUPER_ADMIN' | 'DEVELOPER' | 'SUPERVISOR' | 'COUNTRY_ADMIN' | 'TECHNICIAN' | 'CLIENT'

/**
 * Authenticated user interface
 */
export interface User {
  id: number
  email: string
  username: string
  full_name: string
  user_type: UserType
  permissions: string[]
  company_id: number
  company_name?: string
  is_admin?: boolean
  is_supervisor?: boolean
  theme_preference?: string
}

/**
 * Login request payload
 */
export interface LoginRequest {
  username: string
  password: string
  remember_me?: boolean
}

/**
 * Login response from the API
 */
export interface LoginResponse {
  success: boolean
  data: {
    token: string
    user: User
    expires_at: string
  }
  message?: string
}

/**
 * Auth error response
 */
export interface AuthErrorResponse {
  success: false
  message: string
  errors?: Record<string, string[]>
}

/**
 * Token refresh response
 */
export interface RefreshTokenResponse {
  success: boolean
  data: {
    token: string
    expires_at: string
  }
  message?: string
}

/**
 * Current user response
 */
export interface CurrentUserResponse {
  success: boolean
  data: User
  message?: string
}
