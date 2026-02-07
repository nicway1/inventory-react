/**
 * Asset Hooks
 *
 * React Query hooks for asset data fetching and mutations.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getAssets,
  getAsset,
  createAsset,
  updateAsset,
  deleteAsset,
  uploadAssetImage,
  transferAsset,
  type AssetListParams,
  type AssetListResponse,
  type AssetResponse,
} from '@/services/assets.service'
import type { Asset, CreateAssetPayload, UpdateAssetPayload } from '@/types/assets'

// Query keys
export const assetKeys = {
  all: ['assets'] as const,
  lists: () => [...assetKeys.all, 'list'] as const,
  list: (params: AssetListParams) => [...assetKeys.lists(), params] as const,
  details: () => [...assetKeys.all, 'detail'] as const,
  detail: (id: number) => [...assetKeys.details(), id] as const,
}

/**
 * Hook to fetch paginated assets
 */
export function useAssets(
  params: AssetListParams = {},
  options?: { enabled?: boolean }
) {
  return useQuery<AssetListResponse, Error>({
    queryKey: assetKeys.list(params),
    queryFn: () => getAssets(params),
    staleTime: 1000 * 60 * 2, // 2 minutes
    enabled: options?.enabled ?? true,
  })
}

/**
 * Hook to fetch a single asset
 */
export function useAsset(id: number, options?: { enabled?: boolean }) {
  return useQuery<Asset, Error>({
    queryKey: assetKeys.detail(id),
    queryFn: () => getAsset(id),
    staleTime: 1000 * 60 * 2, // 2 minutes
    enabled: (options?.enabled ?? true) && id > 0,
  })
}

/**
 * Hook to create an asset
 */
export function useCreateAsset() {
  const queryClient = useQueryClient()

  return useMutation<Asset, Error, CreateAssetPayload>({
    mutationFn: createAsset,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: assetKeys.lists() })
    },
  })
}

/**
 * Hook to update an asset
 */
export function useUpdateAsset() {
  const queryClient = useQueryClient()

  return useMutation<Asset, Error, { id: number; data: UpdateAssetPayload }>({
    mutationFn: ({ id, data }) => updateAsset(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: assetKeys.lists() })
      queryClient.invalidateQueries({ queryKey: assetKeys.detail(id) })
    },
  })
}

/**
 * Hook to delete/archive an asset
 */
export function useDeleteAsset() {
  const queryClient = useQueryClient()

  return useMutation<void, Error, { id: number; mode?: 'archive' | 'delete' }>({
    mutationFn: ({ id, mode }) => deleteAsset(id, mode),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: assetKeys.lists() })
      queryClient.removeQueries({ queryKey: assetKeys.detail(id) })
    },
  })
}

/**
 * Hook to upload asset image
 */
export function useUploadAssetImage() {
  const queryClient = useQueryClient()

  return useMutation<{ image_url: string }, Error, { id: number; file: File }>({
    mutationFn: ({ id, file }) => uploadAssetImage(id, file),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: assetKeys.detail(id) })
    },
  })
}

/**
 * Hook to transfer asset to different customer
 */
export function useTransferAsset() {
  const queryClient = useQueryClient()

  return useMutation<
    Asset,
    Error,
    { id: number; customerId: number; reason?: string; notes?: string }
  >({
    mutationFn: ({ id, customerId, reason, notes }) =>
      transferAsset(id, customerId, reason, notes),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: assetKeys.lists() })
      queryClient.invalidateQueries({ queryKey: assetKeys.detail(id) })
    },
  })
}

/**
 * Hook to refresh asset data
 */
export function useAssetRefresh() {
  const queryClient = useQueryClient()

  const refreshAll = () => {
    queryClient.invalidateQueries({ queryKey: assetKeys.all })
  }

  const refreshList = () => {
    queryClient.invalidateQueries({ queryKey: assetKeys.lists() })
  }

  const refreshDetail = (id: number) => {
    queryClient.invalidateQueries({ queryKey: assetKeys.detail(id) })
  }

  return {
    refreshAll,
    refreshList,
    refreshDetail,
  }
}
