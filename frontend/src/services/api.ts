/**
 * API Client Configuration
 *
 * Centralized Axios instance with interceptors for authentication,
 * error handling, and request/response transformation.
 */

import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

/**
 * Get auth token from localStorage
 */
const getAuthToken = (): string | null => {
  try {
    // Try to get from persisted store first
    const authStore = localStorage.getItem('truelog-auth')
    if (authStore) {
      const parsed = JSON.parse(authStore)
      return parsed?.state?.token || null
    }
    // Fallback to direct token storage
    return localStorage.getItem('truelog-auth-token')
  } catch {
    return null
  }
}

// Create axios instance
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Include cookies for session auth
})

// Request interceptor
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Add auth token if available
    const token = getAuthToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error: AxiosError) => {
    return Promise.reject(error)
  }
)

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    // Transform response data if needed
    return response
  },
  (error: AxiosError) => {
    // Handle common errors
    if (error.response?.status === 401) {
      // Clear auth state on unauthorized
      try {
        localStorage.removeItem('truelog-auth')
        localStorage.removeItem('truelog-auth-token')
      } catch {
        // Ignore storage errors
      }
      // Only redirect if not already on login page
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login'
      }
    }

    if (error.response?.status === 403) {
      // Handle forbidden access
      console.error('Access forbidden')
    }

    if (error.response?.status && error.response.status >= 500) {
      // Log server errors
      console.error('Server error:', error.response?.data)
    }

    return Promise.reject(error)
  }
)

export default apiClient
