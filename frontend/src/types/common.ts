/**
 * Common types shared across the application
 */

// API Response wrapper
export interface ApiResponse<T> {
  data: T
  message?: string
  success: boolean
}

// Pagination
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

export interface PaginationParams {
  page?: number
  per_page?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

// User types
export interface User {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
  role: UserRole
  is_active: boolean
  created_at: string
  updated_at: string
}

export type UserRole = 'admin' | 'technician' | 'viewer'

// Common entity fields
export interface BaseEntity {
  id: number
  created_at: string
  updated_at: string
}

// Form state
export type FormMode = 'create' | 'edit' | 'view'

// Table column definition
export interface TableColumn<T> {
  key: keyof T | string
  header: string
  sortable?: boolean
  width?: string
  render?: (item: T) => React.ReactNode
}

// Select option
export interface SelectOption {
  value: string | number
  label: string
  disabled?: boolean
}

// Toast notification
export interface Toast {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  message: string
  duration?: number
}
