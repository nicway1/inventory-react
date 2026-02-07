/**
 * Admin Types
 *
 * Type definitions for admin-related entities.
 */

/**
 * User type enum for admin management
 */
export type AdminUserType =
  | 'SUPER_ADMIN'
  | 'DEVELOPER'
  | 'COUNTRY_ADMIN'
  | 'SUPERVISOR'
  | 'CLIENT'

/**
 * Admin user interface for management
 */
export interface AdminUser {
  id: number
  username: string
  email: string
  user_type: AdminUserType
  company_id: number | null
  company_name?: string
  assigned_country?: string
  first_name?: string
  last_name?: string
  full_name?: string
  is_deleted: boolean
  deleted_at?: string | null
  created_at: string
  updated_at?: string
}

/**
 * Create user request
 */
export interface CreateUserRequest {
  username: string
  email: string
  password: string
  user_type: AdminUserType
  company_id?: number | null
  assigned_country?: string
}

/**
 * Update user request
 */
export interface UpdateUserRequest {
  username?: string
  email?: string
  password?: string
  user_type?: AdminUserType
  company_id?: number | null
  assigned_country?: string
}

/**
 * Company interface
 */
export interface Company {
  id: number
  name: string
  display_name?: string
  description?: string
  address?: string
  contact_name?: string
  contact_email?: string
  parent_company_id?: number | null
  is_parent_company: boolean
  created_at: string
  updated_at?: string
}

/**
 * Create company request
 */
export interface CreateCompanyRequest {
  name: string
  description?: string
  address?: string
  contact_name?: string
  contact_email?: string
  parent_company_id?: number | null
  display_name?: string
  is_parent_company?: boolean
}

/**
 * Update company request
 */
export interface UpdateCompanyRequest {
  name?: string
  description?: string
  address?: string
  contact_name?: string
  contact_email?: string
  parent_company_id?: number | null
  display_name?: string
  is_parent_company?: boolean
}

/**
 * Queue interface
 */
export interface AdminQueue {
  id: number
  name: string
  description?: string
  folder_id?: number | null
  display_order: number
  created_at: string
  updated_at?: string
}

/**
 * Create queue request
 */
export interface CreateQueueRequest {
  name: string
  description?: string
  folder_id?: number | null
  display_order?: number
}

/**
 * Update queue request
 */
export interface UpdateQueueRequest {
  name?: string
  description?: string
  folder_id?: number | null
  display_order?: number
}

/**
 * System settings interface
 */
export interface SystemSettings {
  general: {
    default_homepage: 'classic' | 'dashboard' | 'tickets' | 'inventory' | 'sf'
    default_ticket_view: 'classic' | 'sf'
    default_inventory_view: 'classic' | 'sf'
    system_timezone: string
  }
  email: {
    smtp_enabled: boolean
    from_email: string | null
    ms365_oauth_configured: boolean
  }
  features: {
    chatbot_enabled: boolean
    sla_enabled: boolean
    audit_enabled: boolean
  }
  issue_types: IssueType[]
}

/**
 * Issue type interface
 */
export interface IssueType {
  id: number | null
  name: string
  is_active: boolean
  usage_count?: number
  created_at?: string | null
}

/**
 * Update system settings request
 */
export interface UpdateSystemSettingsRequest {
  general?: {
    default_homepage?: string
    default_ticket_view?: string
    default_inventory_view?: string
    system_timezone?: string
  }
  features?: {
    chatbot_enabled?: boolean
    sla_enabled?: boolean
    audit_enabled?: boolean
  }
}

/**
 * Create issue type request
 */
export interface CreateIssueTypeRequest {
  name: string
  is_active?: boolean
}

/**
 * Admin activity/audit log interface
 */
export interface AdminActivity {
  id: number
  user_id: number
  username?: string
  type: string
  content: string
  reference_id?: number | null
  created_at: string
}

/**
 * Admin dashboard stats
 */
export interface AdminDashboardStats {
  total_users: number
  active_users: number
  total_companies: number
  total_queues: number
  total_tickets: number
  open_tickets: number
  total_assets: number
}

/**
 * Pagination meta from API
 */
export interface PaginationMeta {
  page: number
  per_page: number
  total: number
  total_pages: number
  has_next: boolean
  has_previous: boolean
}

/**
 * Paginated response wrapper
 */
export interface PaginatedResponse<T> {
  success: boolean
  data: T[]
  message?: string
  meta: PaginationMeta
}

/**
 * Single item response wrapper
 */
export interface SingleResponse<T> {
  success: boolean
  data: T
  message?: string
}

/**
 * List params for pagination
 */
export interface AdminListParams {
  page?: number
  per_page?: number
  sort?: string
  order?: 'asc' | 'desc'
  search?: string
}

/**
 * User list params
 */
export interface UserListParams extends AdminListParams {
  user_type?: AdminUserType
  company_id?: number
  include_deleted?: boolean
}

/**
 * Company list params
 */
export interface CompanyListParams extends AdminListParams {
  parent_only?: boolean
}
