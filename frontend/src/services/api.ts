/**
 * API Client Configuration
 *
 * Centralized Axios instance with interceptors for authentication,
 * error handling, and request/response transformation.
 */

import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

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
    // Add any request transformations here
    // e.g., add auth token from store
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
      // Redirect to login on unauthorized
      window.location.href = '/login'
    }

    if (error.response?.status === 403) {
      // Handle forbidden access
      console.error('Access forbidden')
    }

    if (error.response?.status >= 500) {
      // Log server errors
      console.error('Server error:', error.response?.data)
    }

    return Promise.reject(error)
  }
)

export default apiClient
