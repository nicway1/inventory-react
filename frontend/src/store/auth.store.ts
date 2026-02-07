/**
 * Authentication Store
 *
 * Manages user authentication state using Zustand with persistence.
 */

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import type { User } from '@/types/auth'

/**
 * Token storage key
 */
const TOKEN_KEY = 'truelog-auth-token'

/**
 * Auth state interface
 */
interface AuthState {
  // State
  user: User | null
  token: string | null
  expiresAt: string | null
  isAuthenticated: boolean
  isLoading: boolean

  // Actions
  setUser: (user: User | null) => void
  setToken: (token: string | null, expiresAt?: string | null) => void
  login: (user: User, token: string, expiresAt: string) => void
  logout: () => void
  setLoading: (loading: boolean) => void

  // Permission helpers
  hasPermission: (permission: string) => boolean
  hasAnyPermission: (permissions: string[]) => boolean
  hasAllPermissions: (permissions: string[]) => boolean
  isAdmin: () => boolean
  isTechnician: () => boolean
  isClient: () => boolean
}

/**
 * Get token from localStorage
 */
export const getStoredToken = (): string | null => {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

/**
 * Set token in localStorage
 */
export const setStoredToken = (token: string | null): void => {
  try {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token)
    } else {
      localStorage.removeItem(TOKEN_KEY)
    }
  } catch {
    // Silently fail if localStorage is not available
  }
}

/**
 * Auth store with Zustand
 */
export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      token: null,
      expiresAt: null,
      isAuthenticated: false,
      isLoading: true,

      // Set user
      setUser: (user) =>
        set({
          user,
          isAuthenticated: !!user,
        }),

      // Set token
      setToken: (token, expiresAt = null) => {
        setStoredToken(token)
        set({
          token,
          expiresAt,
        })
      },

      // Login action - sets user, token, and authenticated state
      login: (user, token, expiresAt) => {
        setStoredToken(token)
        set({
          user,
          token,
          expiresAt,
          isAuthenticated: true,
          isLoading: false,
        })
      },

      // Logout action - clears all auth state
      logout: () => {
        setStoredToken(null)
        set({
          user: null,
          token: null,
          expiresAt: null,
          isAuthenticated: false,
          isLoading: false,
        })
      },

      // Set loading state
      setLoading: (loading) =>
        set({
          isLoading: loading,
        }),

      // Check if user has a specific permission
      hasPermission: (permission) => {
        const { user } = get()
        if (!user) return false
        return user.permissions.includes(permission)
      },

      // Check if user has any of the specified permissions
      hasAnyPermission: (permissions) => {
        const { user } = get()
        if (!user) return false
        return permissions.some((p) => user.permissions.includes(p))
      },

      // Check if user has all of the specified permissions
      hasAllPermissions: (permissions) => {
        const { user } = get()
        if (!user) return false
        return permissions.every((p) => user.permissions.includes(p))
      },

      // Check if user is admin
      isAdmin: () => {
        const { user } = get()
        return user?.user_type === 'ADMIN'
      },

      // Check if user is technician
      isTechnician: () => {
        const { user } = get()
        return user?.user_type === 'TECHNICIAN'
      },

      // Check if user is client
      isClient: () => {
        const { user } = get()
        return user?.user_type === 'CLIENT'
      },
    }),
    {
      name: 'truelog-auth',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        expiresAt: state.expiresAt,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        // After rehydration, set loading to false
        if (state) {
          state.setLoading(false)
        }
      },
    }
  )
)
