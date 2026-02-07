/**
 * Authentication Hook
 *
 * Provides authentication functionality for React components.
 */

import { useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuthStore } from '@/store/auth.store'
import { authService } from '@/services/auth.service'
import type { LoginRequest, User } from '@/types/auth'

/**
 * Query key for auth-related queries
 */
const AUTH_QUERY_KEY = ['auth', 'user']

/**
 * Custom hook for authentication
 */
export function useAuth() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // Get auth state from store
  const {
    user,
    token,
    isAuthenticated,
    isLoading: isAuthLoading,
    login: storeLogin,
    logout: storeLogout,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    isAdmin,
    isTechnician,
    isClient,
    setLoading,
  } = useAuthStore()

  /**
   * Login mutation
   */
  const loginMutation = useMutation({
    mutationFn: (credentials: LoginRequest) => authService.login(credentials),
    onSuccess: (response) => {
      if (response.success) {
        const { token, user, expires_at } = response.data
        storeLogin(user, token, expires_at)
        queryClient.setQueryData(AUTH_QUERY_KEY, user)
        navigate('/dashboard')
      }
    },
    onError: () => {
      // Error is handled by the component
    },
  })

  /**
   * Logout mutation
   */
  const logoutMutation = useMutation({
    mutationFn: () => authService.logout(),
    onSettled: () => {
      // Always clear auth state, even if API call fails
      storeLogout()
      queryClient.removeQueries({ queryKey: AUTH_QUERY_KEY })
      queryClient.clear()
      navigate('/login')
    },
  })

  /**
   * Fetch current user query (for session validation)
   */
  const currentUserQuery = useQuery({
    queryKey: AUTH_QUERY_KEY,
    queryFn: async () => {
      const response = await authService.getCurrentUser()
      if (response.success) {
        return response.data
      }
      throw new Error(response.message || 'Failed to fetch user')
    },
    enabled: isAuthenticated && !!token,
    staleTime: 1000 * 60 * 5, // 5 minutes
    retry: false,
    meta: {
      onError: () => {
        // If fetching current user fails, logout
        storeLogout()
      },
    },
  })

  /**
   * Login function
   */
  const login = useCallback(
    async (credentials: LoginRequest) => {
      return loginMutation.mutateAsync(credentials)
    },
    [loginMutation]
  )

  /**
   * Logout function
   */
  const logout = useCallback(async () => {
    return logoutMutation.mutateAsync()
  }, [logoutMutation])

  /**
   * Refresh token function
   */
  const refreshToken = useCallback(async () => {
    try {
      const response = await authService.refreshToken()
      if (response.success) {
        useAuthStore.getState().setToken(response.data.token, response.data.expires_at)
        return true
      }
      return false
    } catch {
      storeLogout()
      return false
    }
  }, [storeLogout])

  /**
   * Check if user can access a resource based on permissions
   */
  const canAccess = useCallback(
    (requiredPermissions?: string | string[], requireAll = false): boolean => {
      if (!requiredPermissions) return isAuthenticated

      const permissions = Array.isArray(requiredPermissions)
        ? requiredPermissions
        : [requiredPermissions]

      if (permissions.length === 0) return isAuthenticated

      return requireAll
        ? hasAllPermissions(permissions)
        : hasAnyPermission(permissions)
    },
    [isAuthenticated, hasAnyPermission, hasAllPermissions]
  )

  /**
   * Get user's full name
   */
  const fullName = useMemo(() => {
    if (!user) return ''
    return `${user.first_name} ${user.last_name}`.trim()
  }, [user])

  /**
   * Get user's initials
   */
  const initials = useMemo(() => {
    if (!user) return ''
    const first = user.first_name?.[0] || ''
    const last = user.last_name?.[0] || ''
    return `${first}${last}`.toUpperCase()
  }, [user])

  return {
    // State
    user,
    token,
    isAuthenticated,
    isLoading: isAuthLoading || loginMutation.isPending || currentUserQuery.isLoading,
    isLoggingIn: loginMutation.isPending,
    isLoggingOut: logoutMutation.isPending,
    loginError: loginMutation.error,

    // Actions
    login,
    logout,
    refreshToken,
    setLoading,

    // Permission helpers
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    canAccess,

    // Role helpers
    isAdmin,
    isTechnician,
    isClient,

    // User helpers
    fullName,
    initials,
  }
}

/**
 * Type for the auth hook return value
 */
export type UseAuthReturn = ReturnType<typeof useAuth>
