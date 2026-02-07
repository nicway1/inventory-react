/**
 * Assets Service
 *
 * API methods for asset/inventory management.
 */

import { apiClient } from './api'
import type { Asset, CreateAssetPayload, UpdateAssetPayload } from '@/types'

export interface AssetListParams {
  page?: number
  per_page?: number
  sort?: string
  order?: 'asc' | 'desc'
  search?: string
  status?: string
  asset_type?: string
  manufacturer?: string
  country?: string
  customer?: string
}

export interface AssetListResponse {
  data: Asset[]
  meta: {
    pagination: {
      page: number
      per_page: number
      total: number
      total_pages: number
    }
  }
}

export interface AssetResponse {
  success: boolean
  data: Asset
  message?: string
}

/**
 * Get list of assets with pagination and filtering
 */
export async function getAssets(
  params: AssetListParams = {}
): Promise<AssetListResponse> {
  const searchParams = new URLSearchParams()

  if (params.page) searchParams.append('page', String(params.page))
  if (params.per_page) searchParams.append('per_page', String(params.per_page))
  if (params.sort) searchParams.append('sort', params.sort)
  if (params.order) searchParams.append('order', params.order)
  if (params.search) searchParams.append('search', params.search)
  if (params.status) searchParams.append('status', params.status)
  if (params.asset_type) searchParams.append('asset_type', params.asset_type)
  if (params.manufacturer)
    searchParams.append('manufacturer', params.manufacturer)
  if (params.country) searchParams.append('country', params.country)
  if (params.customer) searchParams.append('customer', params.customer)

  const response = await apiClient.get<AssetListResponse>(
    `/v2/assets?${searchParams.toString()}`
  )
  return response.data
}

/**
 * Get a single asset by ID
 */
export async function getAsset(id: number): Promise<Asset> {
  const response = await apiClient.get<AssetResponse>(`/v2/assets/${id}`)
  return response.data.data
}

/**
 * Create a new asset
 */
export async function createAsset(payload: CreateAssetPayload): Promise<Asset> {
  const response = await apiClient.post<AssetResponse>('/v2/assets', payload)
  return response.data.data
}

/**
 * Update an existing asset
 */
export async function updateAsset(
  id: number,
  payload: UpdateAssetPayload
): Promise<Asset> {
  const response = await apiClient.put<AssetResponse>(
    `/v2/assets/${id}`,
    payload
  )
  return response.data.data
}

/**
 * Delete/archive an asset
 */
export async function deleteAsset(
  id: number,
  mode: 'archive' | 'delete' = 'archive'
): Promise<void> {
  await apiClient.delete(`/v2/assets/${id}?mode=${mode}`)
}

/**
 * Upload asset image
 */
export async function uploadAssetImage(
  assetId: number,
  file: File
): Promise<{ image_url: string }> {
  const formData = new FormData()
  formData.append('image', file)

  const response = await apiClient.post<{
    success: boolean
    data: { image_url: string }
  }>(`/v2/assets/${assetId}/image`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data.data
}

/**
 * Generate a new asset tag
 */
export async function generateAssetTag(): Promise<string> {
  const response = await apiClient.get<{ data: { asset_tag: string } }>(
    '/v2/assets/generate-tag'
  )
  return response.data.data.asset_tag
}

/**
 * Transfer asset to different customer
 */
export async function transferAsset(
  assetId: number,
  customerId: number,
  reason?: string,
  notes?: string
): Promise<Asset> {
  const response = await apiClient.post<AssetResponse>(
    `/v2/assets/${assetId}/transfer`,
    {
      customer_id: customerId,
      reason,
      notes,
    }
  )
  return response.data.data
}

export const assetsService = {
  getAssets,
  getAsset,
  createAsset,
  updateAsset,
  deleteAsset,
  uploadAssetImage,
  generateAssetTag,
  transferAsset,
}

export default assetsService
