/**
 * Inventory Service
 *
 * API calls for assets and accessories management.
 */

import { apiClient } from './api'
import type {
  Asset,
  Accessory,
  AssetListResponse,
  AccessoryListResponse,
  AssetListParams,
  AccessoryListParams,
  CheckoutRequest,
  BulkStatusChangeRequest,
  Customer,
  FilterOption,
  CreateAssetRequest,
  UpdateAssetRequest,
  CreateAccessoryRequest,
  UpdateAccessoryRequest,
} from '@/types/inventory'

// Transform API response to standardized format
function transformAssetListResponse(response: AssetListResponse) {
  return {
    items: response.data,
    total: response.meta.pagination.total_items,
    page: response.meta.pagination.page,
    per_page: response.meta.pagination.per_page,
    total_pages: response.meta.pagination.total_pages,
  }
}

function transformAccessoryListResponse(response: AccessoryListResponse) {
  return {
    items: response.data,
    total: response.meta.pagination.total_items,
    page: response.meta.pagination.page,
    per_page: response.meta.pagination.per_page,
    total_pages: response.meta.pagination.total_pages,
  }
}

// Assets API

export async function fetchAssets(params: AssetListParams) {
  const response = await apiClient.get<AssetListResponse>('/v2/assets', { params })
  return transformAssetListResponse(response.data)
}

export async function fetchAsset(id: number): Promise<Asset> {
  const response = await apiClient.get(`/v2/assets/${id}`)
  return response.data.data || response.data
}

export async function createAsset(data: CreateAssetRequest): Promise<Asset> {
  const response = await apiClient.post('/v2/assets', data)
  return response.data.data || response.data
}

export async function updateAsset(id: number, data: UpdateAssetRequest): Promise<Asset> {
  const response = await apiClient.put(`/v2/assets/${id}`, data)
  return response.data.data || response.data
}

export async function deleteAsset(id: number): Promise<void> {
  await apiClient.delete(`/v2/assets/${id}`)
}

// Accessories API

export async function fetchAccessories(params: AccessoryListParams) {
  const response = await apiClient.get<AccessoryListResponse>('/v2/accessories', { params })
  return transformAccessoryListResponse(response.data)
}

export async function fetchAccessory(id: number): Promise<Accessory> {
  const response = await apiClient.get(`/v2/accessories/${id}`)
  return response.data.data || response.data
}

export async function createAccessory(data: CreateAccessoryRequest): Promise<Accessory> {
  const response = await apiClient.post('/v2/accessories', data)
  return response.data.data || response.data
}

export async function updateAccessory(id: number, data: UpdateAccessoryRequest): Promise<Accessory> {
  const response = await apiClient.put(`/v2/accessories/${id}`, data)
  return response.data.data || response.data
}

export async function deleteAccessory(id: number): Promise<void> {
  await apiClient.delete(`/v2/accessories/${id}`)
}

// Checkout API

export async function processCheckout(data: CheckoutRequest): Promise<{ success: boolean; message: string }> {
  const response = await apiClient.post('/v2/inventory/checkout', data)
  return response.data
}

export async function fetchCheckoutItems(
  assetIds: number[],
  accessoryIds: number[]
): Promise<{ assets: Asset[]; accessories: Accessory[] }> {
  const response = await apiClient.post('/inventory/get-checkout-items', {
    asset_ids: assetIds,
    accessory_ids: accessoryIds,
  })
  return response.data
}

// Bulk actions

export async function bulkUpdateAssetStatus(
  data: BulkStatusChangeRequest
): Promise<{ success: boolean; message: string; updated_count: number }> {
  const response = await apiClient.post('/v2/assets/bulk-status-update', data)
  return response.data
}

export async function exportAssetsToCSV(assetIds?: number[]): Promise<Blob> {
  const response = await apiClient.post(
    '/inventory/export',
    { item_type: 'assets', selected_ids: assetIds },
    { responseType: 'blob' }
  )
  return response.data
}

export async function exportAccessoriesToCSV(accessoryIds?: number[]): Promise<Blob> {
  const response = await apiClient.post(
    '/inventory/export',
    { item_type: 'accessories', selected_ids: accessoryIds },
    { responseType: 'blob' }
  )
  return response.data
}

// Filter options

export async function fetchAssetFilterOptions(): Promise<{
  statuses: FilterOption[]
  types: FilterOption[]
  manufacturers: FilterOption[]
  customers: FilterOption[]
  conditions: FilterOption[]
}> {
  const response = await apiClient.get('/v2/assets/filter-options')
  return response.data
}

export async function fetchAccessoryFilterOptions(): Promise<{
  categories: FilterOption[]
  manufacturers: FilterOption[]
  countries: FilterOption[]
  companies: FilterOption[]
}> {
  const response = await apiClient.get('/v2/accessories/filter-options')
  return response.data
}

// Customers for checkout

export async function fetchCustomers(): Promise<Customer[]> {
  const response = await apiClient.get('/v2/customers')
  return response.data.items || response.data.data || response.data
}

// Import

export async function importAssets(file: File): Promise<{ success: boolean; imported: number; errors: string[] }> {
  const formData = new FormData()
  formData.append('file', file)
  const response = await apiClient.post('/v2/assets/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}

export async function importAccessories(file: File): Promise<{ success: boolean; imported: number; errors: string[] }> {
  const formData = new FormData()
  formData.append('file', file)
  const response = await apiClient.post('/v2/accessories/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}

export default {
  fetchAssets,
  fetchAsset,
  createAsset,
  updateAsset,
  deleteAsset,
  fetchAccessories,
  fetchAccessory,
  createAccessory,
  updateAccessory,
  deleteAccessory,
  processCheckout,
  fetchCheckoutItems,
  bulkUpdateAssetStatus,
  exportAssetsToCSV,
  exportAccessoriesToCSV,
  fetchAssetFilterOptions,
  fetchAccessoryFilterOptions,
  fetchCustomers,
  importAssets,
  importAccessories,
}
