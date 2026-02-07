/**
 * Admin Service
 *
 * Handles all admin-related API calls for user, company, queue, and settings management.
 */

import { apiClient } from './api'
import type {
  AdminUser,
  Company,
  AdminQueue,
  SystemSettings,
  IssueType,
  AdminActivity,
  AdminDashboardStats,
  CreateUserRequest,
  UpdateUserRequest,
  CreateCompanyRequest,
  UpdateCompanyRequest,
  CreateQueueRequest,
  UpdateQueueRequest,
  UpdateSystemSettingsRequest,
  CreateIssueTypeRequest,
  UserListParams,
  CompanyListParams,
  AdminListParams,
  PaginatedResponse,
  SingleResponse,
  PaginationMeta,
} from '@/types/admin'

const ADMIN_BASE_URL = '/v2/admin'

/**
 * Admin service for user, company, queue, and settings management
 */
export const adminService = {
  // ============================================================================
  // USER MANAGEMENT
  // ============================================================================

  /**
   * List users with pagination and filtering
   */
  async listUsers(
    params: UserListParams = {}
  ): Promise<{ users: AdminUser[]; meta: PaginationMeta }> {
    const response = await apiClient.get<PaginatedResponse<AdminUser>>(
      `${ADMIN_BASE_URL}/users`,
      { params }
    )
    return { users: response.data.data, meta: response.data.meta }
  },

  /**
   * Get a single user by ID
   */
  async getUser(id: number): Promise<AdminUser> {
    const response = await apiClient.get<SingleResponse<AdminUser>>(
      `${ADMIN_BASE_URL}/users/${id}`
    )
    return response.data.data
  },

  /**
   * Create a new user
   */
  async createUser(data: CreateUserRequest): Promise<AdminUser> {
    const response = await apiClient.post<SingleResponse<AdminUser>>(
      `${ADMIN_BASE_URL}/users`,
      data
    )
    return response.data.data
  },

  /**
   * Update an existing user
   */
  async updateUser(id: number, data: UpdateUserRequest): Promise<AdminUser> {
    const response = await apiClient.put<SingleResponse<AdminUser>>(
      `${ADMIN_BASE_URL}/users/${id}`,
      data
    )
    return response.data.data
  },

  /**
   * Delete (deactivate) a user
   */
  async deleteUser(id: number, permanent = false): Promise<void> {
    await apiClient.delete(`${ADMIN_BASE_URL}/users/${id}`, {
      params: { permanent },
    })
  },

  /**
   * Reactivate a deactivated user
   */
  async reactivateUser(id: number): Promise<AdminUser> {
    const response = await apiClient.put<SingleResponse<AdminUser>>(
      `${ADMIN_BASE_URL}/users/${id}/reactivate`
    )
    return response.data.data
  },

  /**
   * Reset a user's password
   */
  async resetUserPassword(
    id: number,
    newPassword: string
  ): Promise<{ message: string }> {
    const response = await apiClient.post<{ success: boolean; message: string }>(
      `${ADMIN_BASE_URL}/users/${id}/reset-password`,
      { password: newPassword }
    )
    return { message: response.data.message || 'Password reset successfully' }
  },

  // ============================================================================
  // COMPANY MANAGEMENT
  // ============================================================================

  /**
   * List companies with pagination
   */
  async listCompanies(
    params: CompanyListParams = {}
  ): Promise<{ companies: Company[]; meta: PaginationMeta }> {
    const response = await apiClient.get<PaginatedResponse<Company>>(
      `${ADMIN_BASE_URL}/companies`,
      { params }
    )
    return { companies: response.data.data, meta: response.data.meta }
  },

  /**
   * Get a single company by ID
   */
  async getCompany(id: number): Promise<Company> {
    const response = await apiClient.get<SingleResponse<Company>>(
      `${ADMIN_BASE_URL}/companies/${id}`
    )
    return response.data.data
  },

  /**
   * Create a new company
   */
  async createCompany(data: CreateCompanyRequest): Promise<Company> {
    const response = await apiClient.post<SingleResponse<Company>>(
      `${ADMIN_BASE_URL}/companies`,
      data
    )
    return response.data.data
  },

  /**
   * Update an existing company
   */
  async updateCompany(id: number, data: UpdateCompanyRequest): Promise<Company> {
    const response = await apiClient.put<SingleResponse<Company>>(
      `${ADMIN_BASE_URL}/companies/${id}`,
      data
    )
    return response.data.data
  },

  /**
   * Delete a company
   */
  async deleteCompany(id: number): Promise<void> {
    await apiClient.delete(`${ADMIN_BASE_URL}/companies/${id}`)
  },

  // ============================================================================
  // QUEUE MANAGEMENT
  // ============================================================================

  /**
   * List queues with pagination
   */
  async listQueues(
    params: AdminListParams = {}
  ): Promise<{ queues: AdminQueue[]; meta: PaginationMeta }> {
    const response = await apiClient.get<PaginatedResponse<AdminQueue>>(
      `${ADMIN_BASE_URL}/queues`,
      { params }
    )
    return { queues: response.data.data, meta: response.data.meta }
  },

  /**
   * Get a single queue by ID
   */
  async getQueue(id: number): Promise<AdminQueue> {
    const response = await apiClient.get<SingleResponse<AdminQueue>>(
      `${ADMIN_BASE_URL}/queues/${id}`
    )
    return response.data.data
  },

  /**
   * Create a new queue
   */
  async createQueue(data: CreateQueueRequest): Promise<AdminQueue> {
    const response = await apiClient.post<SingleResponse<AdminQueue>>(
      `${ADMIN_BASE_URL}/queues`,
      data
    )
    return response.data.data
  },

  /**
   * Update an existing queue
   */
  async updateQueue(id: number, data: UpdateQueueRequest): Promise<AdminQueue> {
    const response = await apiClient.put<SingleResponse<AdminQueue>>(
      `${ADMIN_BASE_URL}/queues/${id}`,
      data
    )
    return response.data.data
  },

  /**
   * Delete a queue
   */
  async deleteQueue(id: number): Promise<void> {
    await apiClient.delete(`${ADMIN_BASE_URL}/queues/${id}`)
  },

  // ============================================================================
  // SYSTEM SETTINGS
  // ============================================================================

  /**
   * Get system settings
   */
  async getSystemSettings(): Promise<SystemSettings> {
    const response = await apiClient.get<SingleResponse<SystemSettings>>(
      `${ADMIN_BASE_URL}/system-settings`
    )
    return response.data.data
  },

  /**
   * Update system settings
   */
  async updateSystemSettings(
    data: UpdateSystemSettingsRequest
  ): Promise<SystemSettings> {
    const response = await apiClient.put<SingleResponse<SystemSettings>>(
      `${ADMIN_BASE_URL}/system-settings`,
      data
    )
    return response.data.data
  },

  /**
   * Create a new issue type
   */
  async createIssueType(data: CreateIssueTypeRequest): Promise<IssueType> {
    const response = await apiClient.post<SingleResponse<IssueType>>(
      `${ADMIN_BASE_URL}/system-settings/issue-types`,
      data
    )
    return response.data.data
  },

  /**
   * Update an issue type
   */
  async updateIssueType(
    id: number,
    data: Partial<CreateIssueTypeRequest>
  ): Promise<IssueType> {
    const response = await apiClient.put<SingleResponse<IssueType>>(
      `${ADMIN_BASE_URL}/system-settings/issue-types/${id}`,
      data
    )
    return response.data.data
  },

  /**
   * Delete an issue type
   */
  async deleteIssueType(id: number): Promise<void> {
    await apiClient.delete(`${ADMIN_BASE_URL}/system-settings/issue-types/${id}`)
  },

  // ============================================================================
  // DASHBOARD & ACTIVITIES
  // ============================================================================

  /**
   * Get admin dashboard stats
   */
  async getDashboardStats(): Promise<AdminDashboardStats> {
    const response = await apiClient.get<SingleResponse<AdminDashboardStats>>(
      `${ADMIN_BASE_URL}/dashboard/stats`
    )
    return response.data.data
  },

  /**
   * Get recent admin activities
   */
  async getRecentActivities(
    limit = 10
  ): Promise<AdminActivity[]> {
    const response = await apiClient.get<PaginatedResponse<AdminActivity>>(
      `${ADMIN_BASE_URL}/activities`,
      { params: { per_page: limit } }
    )
    return response.data.data
  },
}

export default adminService
