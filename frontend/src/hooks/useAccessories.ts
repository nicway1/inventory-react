/**
 * Accessory Hooks
 *
 * React Query hooks for accessory data fetching and mutations.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getAccessories,
  getAccessory,
  createAccessory,
  updateAccessory,
  deleteAccessory,
  checkinAccessory,
  returnAccessory,
  type AccessoryListParams,
  type AccessoryListResponse,
  type AccessoryResponse,
  type CreateAccessoryRequest,
  type UpdateAccessoryRequest,
  type AccessoryCheckinRequest,
  type AccessoryReturnRequest,
  type AccessoryCheckinResponse,
} from '@/services/accessory.service'
import type { Accessory } from '@/types/inventory'

// Query keys
export const accessoryKeys = {
  all: ['accessories'] as const,
  lists: () => [...accessoryKeys.all, 'list'] as const,
  list: (params: AccessoryListParams) => [...accessoryKeys.lists(), params] as const,
  details: () => [...accessoryKeys.all, 'detail'] as const,
  detail: (id: number) => [...accessoryKeys.details(), id] as const,
}

/**
 * Hook to fetch paginated accessories
 */
export function useAccessories(
  params: AccessoryListParams = {},
  options?: { enabled?: boolean }
) {
  return useQuery<AccessoryListResponse, Error>({
    queryKey: accessoryKeys.list(params),
    queryFn: () => getAccessories(params),
    staleTime: 1000 * 60 * 2, // 2 minutes
    enabled: options?.enabled ?? true,
  })
}

/**
 * Hook to fetch a single accessory
 */
export function useAccessory(id: number, options?: { enabled?: boolean }) {
  return useQuery<AccessoryResponse, Error>({
    queryKey: accessoryKeys.detail(id),
    queryFn: () => getAccessory(id),
    staleTime: 1000 * 60 * 2, // 2 minutes
    enabled: (options?.enabled ?? true) && id > 0,
  })
}

/**
 * Hook to create an accessory
 */
export function useCreateAccessory() {
  const queryClient = useQueryClient()

  return useMutation<AccessoryResponse, Error, CreateAccessoryRequest>({
    mutationFn: createAccessory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: accessoryKeys.lists() })
    },
  })
}

/**
 * Hook to update an accessory
 */
export function useUpdateAccessory() {
  const queryClient = useQueryClient()

  return useMutation<
    AccessoryResponse,
    Error,
    { id: number; data: UpdateAccessoryRequest }
  >({
    mutationFn: ({ id, data }) => updateAccessory(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: accessoryKeys.lists() })
      queryClient.invalidateQueries({ queryKey: accessoryKeys.detail(id) })
    },
  })
}

/**
 * Hook to delete an accessory
 */
export function useDeleteAccessory() {
  const queryClient = useQueryClient()

  return useMutation<void, Error, number>({
    mutationFn: deleteAccessory,
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: accessoryKeys.lists() })
      queryClient.removeQueries({ queryKey: accessoryKeys.detail(id) })
    },
  })
}

/**
 * Hook to check in (return) an accessory from a customer
 */
export function useCheckinAccessory() {
  const queryClient = useQueryClient()

  return useMutation<
    AccessoryCheckinResponse,
    Error,
    { id: number; data: AccessoryCheckinRequest }
  >({
    mutationFn: ({ id, data }) => checkinAccessory(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: accessoryKeys.lists() })
      queryClient.invalidateQueries({ queryKey: accessoryKeys.detail(id) })
    },
  })
}

/**
 * Hook to return an accessory to inventory
 */
export function useReturnAccessory() {
  const queryClient = useQueryClient()

  return useMutation<
    AccessoryResponse,
    Error,
    { id: number; data: AccessoryReturnRequest }
  >({
    mutationFn: ({ id, data }) => returnAccessory(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: accessoryKeys.lists() })
      queryClient.invalidateQueries({ queryKey: accessoryKeys.detail(id) })
    },
  })
}

/**
 * Hook to refresh accessory data
 */
export function useAccessoryRefresh() {
  const queryClient = useQueryClient()

  const refreshAll = () => {
    queryClient.invalidateQueries({ queryKey: accessoryKeys.all })
  }

  const refreshList = () => {
    queryClient.invalidateQueries({ queryKey: accessoryKeys.lists() })
  }

  const refreshDetail = (id: number) => {
    queryClient.invalidateQueries({ queryKey: accessoryKeys.detail(id) })
  }

  return {
    refreshAll,
    refreshList,
    refreshDetail,
  }
}
