/**
 * Customer Hooks
 *
 * React Query hooks for customer data fetching and mutations.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getCustomers,
  getCustomer,
  createCustomer,
  updateCustomer,
  deleteCustomer,
  getCustomerTransactions,
  getCompanies,
  getCustomerCountries,
} from '@/services/customer.service'
import type {
  CustomerListParams,
  CustomerListResponse,
  CustomerDetail,
  CustomerFormData,
  Customer,
  CustomerTransaction,
} from '@/types/customer'
import type { CompanyReference } from '@/types/customer'

// Query keys
export const customerKeys = {
  all: ['customers'] as const,
  lists: () => [...customerKeys.all, 'list'] as const,
  list: (params: CustomerListParams) =>
    [...customerKeys.lists(), params] as const,
  details: () => [...customerKeys.all, 'detail'] as const,
  detail: (id: number) => [...customerKeys.details(), id] as const,
  transactions: (id: number) =>
    [...customerKeys.all, 'transactions', id] as const,
  companies: () => ['companies'] as const,
  countries: () => [...customerKeys.all, 'countries'] as const,
}

/**
 * Hook to fetch paginated customers
 */
export function useCustomers(
  params: CustomerListParams = {},
  options?: { enabled?: boolean }
) {
  return useQuery<CustomerListResponse, Error>({
    queryKey: customerKeys.list(params),
    queryFn: () => getCustomers(params),
    staleTime: 1000 * 60 * 2, // 2 minutes
    enabled: options?.enabled ?? true,
  })
}

/**
 * Hook to fetch a single customer
 */
export function useCustomer(
  id: number,
  options?: { enabled?: boolean }
) {
  return useQuery<CustomerDetail, Error>({
    queryKey: customerKeys.detail(id),
    queryFn: () => getCustomer(id),
    staleTime: 1000 * 60 * 2, // 2 minutes
    enabled: (options?.enabled ?? true) && id > 0,
  })
}

/**
 * Hook to fetch customer transactions
 */
export function useCustomerTransactions(
  id: number,
  options?: { enabled?: boolean }
) {
  return useQuery<CustomerTransaction[], Error>({
    queryKey: customerKeys.transactions(id),
    queryFn: () => getCustomerTransactions(id),
    staleTime: 1000 * 60 * 2, // 2 minutes
    enabled: (options?.enabled ?? true) && id > 0,
  })
}

/**
 * Hook to fetch companies for dropdown
 */
export function useCompanies(options?: { enabled?: boolean }) {
  return useQuery<CompanyReference[], Error>({
    queryKey: customerKeys.companies(),
    queryFn: getCompanies,
    staleTime: 1000 * 60 * 5, // 5 minutes
    enabled: options?.enabled ?? true,
  })
}

/**
 * Hook to fetch customer countries for filter
 */
export function useCustomerCountries(options?: { enabled?: boolean }) {
  return useQuery<string[], Error>({
    queryKey: customerKeys.countries(),
    queryFn: getCustomerCountries,
    staleTime: 1000 * 60 * 5, // 5 minutes
    enabled: options?.enabled ?? true,
  })
}

/**
 * Hook to create a customer
 */
export function useCreateCustomer() {
  const queryClient = useQueryClient()

  return useMutation<Customer, Error, CustomerFormData>({
    mutationFn: createCustomer,
    onSuccess: () => {
      // Invalidate customer lists
      queryClient.invalidateQueries({ queryKey: customerKeys.lists() })
    },
  })
}

/**
 * Hook to update a customer
 */
export function useUpdateCustomer() {
  const queryClient = useQueryClient()

  return useMutation<
    Customer,
    Error,
    { id: number; data: CustomerFormData }
  >({
    mutationFn: ({ id, data }) => updateCustomer(id, data),
    onSuccess: (_, { id }) => {
      // Invalidate customer lists and detail
      queryClient.invalidateQueries({ queryKey: customerKeys.lists() })
      queryClient.invalidateQueries({ queryKey: customerKeys.detail(id) })
    },
  })
}

/**
 * Hook to delete a customer
 */
export function useDeleteCustomer() {
  const queryClient = useQueryClient()

  return useMutation<void, Error, number>({
    mutationFn: deleteCustomer,
    onSuccess: (_, id) => {
      // Invalidate customer lists and remove detail from cache
      queryClient.invalidateQueries({ queryKey: customerKeys.lists() })
      queryClient.removeQueries({ queryKey: customerKeys.detail(id) })
    },
  })
}

/**
 * Hook to refresh customer data
 */
export function useCustomerRefresh() {
  const queryClient = useQueryClient()

  const refreshAll = () => {
    queryClient.invalidateQueries({ queryKey: customerKeys.all })
  }

  const refreshList = () => {
    queryClient.invalidateQueries({ queryKey: customerKeys.lists() })
  }

  const refreshDetail = (id: number) => {
    queryClient.invalidateQueries({ queryKey: customerKeys.detail(id) })
  }

  return {
    refreshAll,
    refreshList,
    refreshDetail,
  }
}
