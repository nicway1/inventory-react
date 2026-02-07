/**
 * Admin Hooks
 *
 * React Query hooks for admin data fetching and mutations.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { adminService } from '@/services/admin.service'
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
  PaginationMeta,
} from '@/types/admin'

// Query keys
export const adminKeys = {
  all: ['admin'] as const,
  // Users
  users: () => [...adminKeys.all, 'users'] as const,
  userList: (params: UserListParams) => [...adminKeys.users(), 'list', params] as const,
  userDetail: (id: number) => [...adminKeys.users(), 'detail', id] as const,
  // Companies
  companies: () => [...adminKeys.all, 'companies'] as const,
  companyList: (params: CompanyListParams) =>
    [...adminKeys.companies(), 'list', params] as const,
  companyDetail: (id: number) => [...adminKeys.companies(), 'detail', id] as const,
  // Queues
  queues: () => [...adminKeys.all, 'queues'] as const,
  queueList: (params: AdminListParams) => [...adminKeys.queues(), 'list', params] as const,
  queueDetail: (id: number) => [...adminKeys.queues(), 'detail', id] as const,
  // Settings
  settings: () => [...adminKeys.all, 'settings'] as const,
  // Dashboard
  dashboard: () => [...adminKeys.all, 'dashboard'] as const,
  dashboardStats: () => [...adminKeys.dashboard(), 'stats'] as const,
  activities: () => [...adminKeys.all, 'activities'] as const,
}

// ============================================================================
// USER HOOKS
// ============================================================================

/**
 * Hook to fetch paginated users
 */
export function useUsers(
  params: UserListParams = {},
  options?: { enabled?: boolean }
) {
  return useQuery<{ users: AdminUser[]; meta: PaginationMeta }, Error>({
    queryKey: adminKeys.userList(params),
    queryFn: () => adminService.listUsers(params),
    staleTime: 1000 * 60 * 2, // 2 minutes
    enabled: options?.enabled ?? true,
  })
}

/**
 * Hook to fetch single user
 */
export function useUser(id: number, options?: { enabled?: boolean }) {
  return useQuery<AdminUser, Error>({
    queryKey: adminKeys.userDetail(id),
    queryFn: () => adminService.getUser(id),
    staleTime: 1000 * 60 * 2,
    enabled: (options?.enabled ?? true) && id > 0,
  })
}

/**
 * Hook to create a user
 */
export function useCreateUser() {
  const queryClient = useQueryClient()

  return useMutation<AdminUser, Error, CreateUserRequest>({
    mutationFn: adminService.createUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.users() })
      queryClient.invalidateQueries({ queryKey: adminKeys.dashboardStats() })
    },
  })
}

/**
 * Hook to update a user
 */
export function useUpdateUser() {
  const queryClient = useQueryClient()

  return useMutation<AdminUser, Error, { id: number; data: UpdateUserRequest }>({
    mutationFn: ({ id, data }) => adminService.updateUser(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: adminKeys.users() })
      queryClient.invalidateQueries({ queryKey: adminKeys.userDetail(id) })
    },
  })
}

/**
 * Hook to delete (deactivate) a user
 */
export function useDeleteUser() {
  const queryClient = useQueryClient()

  return useMutation<void, Error, { id: number; permanent?: boolean }>({
    mutationFn: ({ id, permanent }) => adminService.deleteUser(id, permanent),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.users() })
      queryClient.invalidateQueries({ queryKey: adminKeys.dashboardStats() })
    },
  })
}

/**
 * Hook to reset a user's password
 */
export function useResetUserPassword() {
  return useMutation<{ message: string }, Error, { id: number; password: string }>({
    mutationFn: ({ id, password }) => adminService.resetUserPassword(id, password),
  })
}

// ============================================================================
// COMPANY HOOKS
// ============================================================================

/**
 * Hook to fetch paginated companies
 */
export function useCompanies(
  params: CompanyListParams = {},
  options?: { enabled?: boolean }
) {
  return useQuery<{ companies: Company[]; meta: PaginationMeta }, Error>({
    queryKey: adminKeys.companyList(params),
    queryFn: () => adminService.listCompanies(params),
    staleTime: 1000 * 60 * 2,
    enabled: options?.enabled ?? true,
  })
}

/**
 * Hook to fetch single company
 */
export function useCompany(id: number, options?: { enabled?: boolean }) {
  return useQuery<Company, Error>({
    queryKey: adminKeys.companyDetail(id),
    queryFn: () => adminService.getCompany(id),
    staleTime: 1000 * 60 * 2,
    enabled: (options?.enabled ?? true) && id > 0,
  })
}

/**
 * Hook to create a company
 */
export function useCreateCompany() {
  const queryClient = useQueryClient()

  return useMutation<Company, Error, CreateCompanyRequest>({
    mutationFn: adminService.createCompany,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.companies() })
      queryClient.invalidateQueries({ queryKey: adminKeys.dashboardStats() })
    },
  })
}

/**
 * Hook to update a company
 */
export function useUpdateCompany() {
  const queryClient = useQueryClient()

  return useMutation<Company, Error, { id: number; data: UpdateCompanyRequest }>({
    mutationFn: ({ id, data }) => adminService.updateCompany(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: adminKeys.companies() })
      queryClient.invalidateQueries({ queryKey: adminKeys.companyDetail(id) })
    },
  })
}

/**
 * Hook to delete a company
 */
export function useDeleteCompany() {
  const queryClient = useQueryClient()

  return useMutation<void, Error, number>({
    mutationFn: adminService.deleteCompany,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.companies() })
      queryClient.invalidateQueries({ queryKey: adminKeys.dashboardStats() })
    },
  })
}

// ============================================================================
// QUEUE HOOKS
// ============================================================================

/**
 * Hook to fetch paginated queues
 */
export function useAdminQueues(
  params: AdminListParams = {},
  options?: { enabled?: boolean }
) {
  return useQuery<{ queues: AdminQueue[]; meta: PaginationMeta }, Error>({
    queryKey: adminKeys.queueList(params),
    queryFn: () => adminService.listQueues(params),
    staleTime: 1000 * 60 * 2,
    enabled: options?.enabled ?? true,
  })
}

/**
 * Hook to fetch single queue
 */
export function useAdminQueue(id: number, options?: { enabled?: boolean }) {
  return useQuery<AdminQueue, Error>({
    queryKey: adminKeys.queueDetail(id),
    queryFn: () => adminService.getQueue(id),
    staleTime: 1000 * 60 * 2,
    enabled: (options?.enabled ?? true) && id > 0,
  })
}

/**
 * Hook to create a queue
 */
export function useCreateQueue() {
  const queryClient = useQueryClient()

  return useMutation<AdminQueue, Error, CreateQueueRequest>({
    mutationFn: adminService.createQueue,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.queues() })
      queryClient.invalidateQueries({ queryKey: adminKeys.dashboardStats() })
    },
  })
}

/**
 * Hook to update a queue
 */
export function useUpdateQueue() {
  const queryClient = useQueryClient()

  return useMutation<AdminQueue, Error, { id: number; data: UpdateQueueRequest }>({
    mutationFn: ({ id, data }) => adminService.updateQueue(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: adminKeys.queues() })
      queryClient.invalidateQueries({ queryKey: adminKeys.queueDetail(id) })
    },
  })
}

/**
 * Hook to delete a queue
 */
export function useDeleteQueue() {
  const queryClient = useQueryClient()

  return useMutation<void, Error, number>({
    mutationFn: adminService.deleteQueue,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.queues() })
      queryClient.invalidateQueries({ queryKey: adminKeys.dashboardStats() })
    },
  })
}

// ============================================================================
// SETTINGS HOOKS
// ============================================================================

/**
 * Hook to fetch system settings
 */
export function useSystemSettings(options?: { enabled?: boolean }) {
  return useQuery<SystemSettings, Error>({
    queryKey: adminKeys.settings(),
    queryFn: adminService.getSystemSettings,
    staleTime: 1000 * 60 * 5, // 5 minutes
    enabled: options?.enabled ?? true,
  })
}

/**
 * Hook to update system settings
 */
export function useUpdateSystemSettings() {
  const queryClient = useQueryClient()

  return useMutation<SystemSettings, Error, UpdateSystemSettingsRequest>({
    mutationFn: adminService.updateSystemSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.settings() })
    },
  })
}

/**
 * Hook to create an issue type
 */
export function useCreateIssueType() {
  const queryClient = useQueryClient()

  return useMutation<IssueType, Error, CreateIssueTypeRequest>({
    mutationFn: adminService.createIssueType,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.settings() })
    },
  })
}

/**
 * Hook to update an issue type
 */
export function useUpdateIssueType() {
  const queryClient = useQueryClient()

  return useMutation<IssueType, Error, { id: number; data: Partial<CreateIssueTypeRequest> }>({
    mutationFn: ({ id, data }) => adminService.updateIssueType(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.settings() })
    },
  })
}

/**
 * Hook to delete an issue type
 */
export function useDeleteIssueType() {
  const queryClient = useQueryClient()

  return useMutation<void, Error, number>({
    mutationFn: adminService.deleteIssueType,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.settings() })
    },
  })
}

// ============================================================================
// DASHBOARD HOOKS
// ============================================================================

/**
 * Hook to fetch admin dashboard stats
 */
export function useAdminDashboardStats(options?: { enabled?: boolean }) {
  return useQuery<AdminDashboardStats, Error>({
    queryKey: adminKeys.dashboardStats(),
    queryFn: adminService.getDashboardStats,
    staleTime: 1000 * 60 * 1, // 1 minute
    enabled: options?.enabled ?? true,
  })
}

/**
 * Hook to fetch recent admin activities
 */
export function useAdminActivities(limit = 10, options?: { enabled?: boolean }) {
  return useQuery<AdminActivity[], Error>({
    queryKey: [...adminKeys.activities(), limit],
    queryFn: () => adminService.getRecentActivities(limit),
    staleTime: 1000 * 60 * 1,
    enabled: options?.enabled ?? true,
  })
}

/**
 * Hook to refresh all admin data
 */
export function useAdminRefresh() {
  const queryClient = useQueryClient()

  const refreshAll = () => {
    queryClient.invalidateQueries({ queryKey: adminKeys.all })
  }

  const refreshUsers = () => {
    queryClient.invalidateQueries({ queryKey: adminKeys.users() })
  }

  const refreshCompanies = () => {
    queryClient.invalidateQueries({ queryKey: adminKeys.companies() })
  }

  const refreshQueues = () => {
    queryClient.invalidateQueries({ queryKey: adminKeys.queues() })
  }

  const refreshSettings = () => {
    queryClient.invalidateQueries({ queryKey: adminKeys.settings() })
  }

  return {
    refreshAll,
    refreshUsers,
    refreshCompanies,
    refreshQueues,
    refreshSettings,
  }
}
