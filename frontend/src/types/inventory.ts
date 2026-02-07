/**
 * Inventory Types
 *
 * Types for assets, accessories, and inventory management.
 */

import { BaseEntity } from './common'

// Asset status enum matching Flask backend
export type AssetStatus =
  | 'IN_STOCK'
  | 'DEPLOYED'
  | 'READY_TO_DEPLOY'
  | 'REPAIR'
  | 'ARCHIVED'
  | 'DISPOSED'

// Legacy alias
export type AssetStatusValue = AssetStatus

// Asset status for display
export interface AssetStatusLabel {
  name: string
  status_meta: 'deployable' | 'deployed' | 'pending' | 'archived'
}

// Asset condition
export type AssetCondition = 'NEW' | 'GOOD' | 'FAIR' | 'POOR'

// Asset interface matching Flask model
export interface Asset extends BaseEntity {
  asset_tag: string
  name: string
  model: string
  serial_num: string
  manufacturer: string
  asset_type: string
  status: AssetStatus
  condition: AssetCondition
  customer_id?: number
  customer_name?: string
  image_url?: string
  // specs
  cpu_type?: string
  cpu_cores?: string
  memory?: string
  harddrive?: string
  notes?: string
  // Extended fields
  product?: string
  status_label?: AssetStatusLabel
  category?: {
    id: number
    name: string
  }
  manufacturer_obj?: {
    id: number
    name: string
  }
  customer?: {
    id: number
    name: string
  }
  location?: {
    id: number
    name: string
  }
  country?: string
  gpu_cores?: string
  tech_notes?: string
  erased?: string
  legal_hold?: boolean
  purchase_date?: string
  warranty_date?: string
}

// Accessory status
export type AccessoryStatus = 'Available' | 'Out of Stock' | 'Low Stock'

// Accessory interface matching Flask model
export interface Accessory extends BaseEntity {
  name: string
  category?: string
  manufacturer?: string
  model_no?: string
  country?: string
  company?: {
    id: number
    name: string
  }
  total_quantity: number
  available_quantity: number
  checked_out_quantity?: number
  min_quantity?: number
  status: AccessoryStatus
  image_url?: string
  notes?: string
}

// Filter options for inventory list
export interface InventoryFilters {
  search?: string
  status?: AssetStatusValue | ''
  type?: string
  manufacturer?: string
  customer?: string
  condition?: AssetCondition | ''
}

// Filter options for accessories list
export interface AccessoryFilters {
  search?: string
  category?: string
  manufacturer?: string
  country?: string
  company?: string
  status?: AccessoryStatus | ''
}

// Checkout cart item
export interface CheckoutCartItem {
  id: number
  name: string
  type: 'asset' | 'accessory'
  asset_tag?: string
  category?: string
  quantity: number
  image_url?: string
}

// Checkout request
export interface CheckoutRequest {
  customer_id: number
  items: {
    id: number
    type: 'asset' | 'accessory'
    quantity: number
  }[]
  notes?: string
}

// API response types
export interface AssetsListResponse {
  items: Asset[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

export interface AccessoriesListResponse {
  items: Accessory[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

// Customer for checkout
export interface Customer {
  id: number
  name: string
  email?: string
  company?: string
}

// Filter dropdown options
export interface FilterOption {
  value: string
  label: string
  count?: number
}

// Bulk action types
export type BulkActionType =
  | 'checkout'
  | 'status_change'
  | 'export_csv'
  | 'delete'

// Status change request
export interface BulkStatusChangeRequest {
  asset_ids: number[]
  status: AssetStatusValue
  notes?: string
}

// Create asset request
export interface CreateAssetRequest {
  asset_tag?: string
  serial_number?: string
  name?: string
  model?: string
  manufacturer?: string
  asset_type?: string
  category?: string
  status?: AssetStatus
  condition?: AssetCondition
  country?: string
  customer?: string
  customer_id?: number
  location_id?: number
  company_id?: number
  cost_price?: number
  hardware_type?: string
  cpu_type?: string
  cpu_cores?: string
  gpu_cores?: string
  memory?: string
  harddrive?: string
  keyboard?: string
  charger?: string
  erased?: string
  diag?: string
  po?: string
  notes?: string
  tech_notes?: string
  image_url?: string
  legal_hold?: boolean
  receiving_date?: string
  specifications?: Record<string, unknown>
}

// Update asset request
export interface UpdateAssetRequest extends Partial<CreateAssetRequest> {}

// Transfer asset request
export interface TransferAssetRequest {
  customer_id: number
  reason?: string
  notes?: string
  effective_date?: string
}

// Asset list query parameters
export interface AssetListParams {
  page?: number
  per_page?: number
  sort?: string
  order?: 'asc' | 'desc'
  search?: string
  status?: AssetStatus
  condition?: AssetCondition
  asset_type?: string
  manufacturer?: string
  customer_id?: number
  company_id?: number
  country?: string
}

// Asset API response
export interface AssetResponse {
  success: boolean
  data: Asset
  message?: string
}

// Asset list API response
export interface AssetListResponse {
  success: boolean
  data: Asset[]
  meta: {
    pagination: {
      page: number
      per_page: number
      total_items: number
      total_pages: number
      has_next: boolean
      has_prev: boolean
    }
  }
}

// Create accessory request
export interface CreateAccessoryRequest {
  name: string
  category: string
  manufacturer?: string
  model_no?: string
  total_quantity?: number
  country?: string
  notes?: string
  image_url?: string
  company_id?: number
  aliases?: string[]
}

// Update accessory request
export interface UpdateAccessoryRequest extends Partial<CreateAccessoryRequest> {}

// Accessory checkin request
export interface AccessoryCheckinRequest {
  customer_id: number
  quantity?: number
  condition?: string
  notes?: string
  ticket_id?: number
}

// Accessory return request
export interface AccessoryReturnRequest {
  quantity?: number
  customer_id?: number
  notes?: string
}

// Accessory list query parameters
export interface AccessoryListParams {
  page?: number
  per_page?: number
  search?: string
  category?: string
  manufacturer?: string
  country?: string
  company_id?: number
  sort?: string
  order?: 'asc' | 'desc'
}

// Accessory API response
export interface AccessoryResponse {
  success: boolean
  data: Accessory
  message?: string
}

// Accessory list API response
export interface AccessoryListResponse {
  success: boolean
  data: Accessory[]
  meta: {
    pagination: {
      page: number
      per_page: number
      total_items: number
      total_pages: number
      has_next: boolean
      has_prev: boolean
    }
  }
}
