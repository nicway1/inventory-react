/**
 * Asset Types
 *
 * Type definitions for asset/inventory management.
 */

import type { BaseEntity, SelectOption } from './common'

// Asset Status enum values
export type AssetStatus =
  | 'IN_STOCK'
  | 'DEPLOYED'
  | 'IN_REPAIR'
  | 'PENDING_RETURN'
  | 'RETURNED'
  | 'DISPOSED'
  | 'ARCHIVED'
  | 'ON_HOLD'
  | 'IN_TRANSIT'

// Asset Condition values
export type AssetCondition =
  | 'New'
  | 'Excellent'
  | 'Good'
  | 'Fair'
  | 'Poor'
  | 'For Disposal'

// Asset Type values
export type AssetType =
  | 'Laptop'
  | 'Desktop'
  | 'Monitor'
  | 'Phone'
  | 'Tablet'
  | 'Printer'
  | 'Server'
  | 'Networking'
  | 'Other'

// Asset interface
export interface Asset extends BaseEntity {
  asset_tag?: string
  serial_number?: string
  name?: string
  model?: string
  manufacturer?: string
  category?: string
  asset_type?: AssetType | string
  status: AssetStatus
  condition?: AssetCondition | string
  country?: string
  customer?: string
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

// Create Asset request payload
export interface CreateAssetPayload {
  asset_tag?: string
  serial_number?: string
  name?: string
  model?: string
  manufacturer?: string
  category?: string
  asset_type?: string
  status?: string
  condition?: string
  country?: string
  customer?: string
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

// Update Asset request payload
export interface UpdateAssetPayload extends Partial<CreateAssetPayload> {}

// Asset form values (for React Hook Form)
export interface AssetFormValues {
  asset_tag: string
  serial_number: string
  name: string
  model: string
  manufacturer: string
  asset_type: string
  status: string
  condition: string
  cpu_type: string
  memory: string
  harddrive: string
  customer: string
  notes: string
  auto_generate_tag: boolean
}

// Status options
export const STATUS_OPTIONS: SelectOption[] = [
  { value: 'IN_STOCK', label: 'In Stock' },
  { value: 'DEPLOYED', label: 'Deployed' },
  { value: 'IN_REPAIR', label: 'In Repair' },
  { value: 'PENDING_RETURN', label: 'Pending Return' },
  { value: 'RETURNED', label: 'Returned' },
  { value: 'DISPOSED', label: 'Disposed' },
  { value: 'ARCHIVED', label: 'Archived' },
  { value: 'ON_HOLD', label: 'On Hold' },
  { value: 'IN_TRANSIT', label: 'In Transit' },
]

// Condition options
export const CONDITION_OPTIONS: SelectOption[] = [
  { value: 'New', label: 'New' },
  { value: 'Excellent', label: 'Excellent' },
  { value: 'Good', label: 'Good' },
  { value: 'Fair', label: 'Fair' },
  { value: 'Poor', label: 'Poor' },
  { value: 'For Disposal', label: 'For Disposal' },
]

// Asset Type options
export const ASSET_TYPE_OPTIONS: SelectOption[] = [
  { value: 'Laptop', label: 'Laptop' },
  { value: 'Desktop', label: 'Desktop' },
  { value: 'Monitor', label: 'Monitor' },
  { value: 'Phone', label: 'Phone' },
  { value: 'Tablet', label: 'Tablet' },
  { value: 'Printer', label: 'Printer' },
  { value: 'Server', label: 'Server' },
  { value: 'Networking', label: 'Networking' },
  { value: 'Other', label: 'Other' },
]

// Common Manufacturer options
export const MANUFACTURER_OPTIONS: SelectOption[] = [
  { value: 'Apple', label: 'Apple' },
  { value: 'Dell', label: 'Dell' },
  { value: 'HP', label: 'HP' },
  { value: 'Lenovo', label: 'Lenovo' },
  { value: 'Microsoft', label: 'Microsoft' },
  { value: 'Samsung', label: 'Samsung' },
  { value: 'Asus', label: 'Asus' },
  { value: 'Acer', label: 'Acer' },
  { value: 'Other', label: 'Other' },
]

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
  condition?: string
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

// Asset image upload response
export interface AssetImageResponse {
  success: boolean
  data: {
    image_url: string
  }
  message?: string
}
