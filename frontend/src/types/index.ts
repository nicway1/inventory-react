/**
 * TrueLog Inventory - Type Definitions
 *
 * This file exports all shared TypeScript types used across the application.
 * Individual type files should be created for each domain (tickets, inventory, etc.)
 */

// Re-export all types from domain-specific files
export * from './common'
export * from './auth'
export * from './dashboard'
// Ticket types - using tickets.ts as the primary source
export * from './tickets'
// Explicitly export non-conflicting types from ticket.ts
export type {
  TicketResponse,
  TicketListResponse,
  CreateTicketRequest,
  UpdateTicketRequest,
  AssignTicketRequest,
  ChangeTicketStatusRequest,
  BulkActionRequest,
  STATUS_CONFIG,
  PRIORITY_CONFIG,
} from './ticket'
// Assets types - using assets.ts as the primary source
export * from './assets'
// Inventory types - explicitly avoid conflicts
export type {
  AssetStatusLabel,
  AccessoryFilters,
  InventoryFilters,
  CheckoutCartItem,
  CheckoutRequest,
  AssetsListResponse,
  AccessoriesListResponse,
  FilterOption,
  BulkActionType,
  BulkStatusChangeRequest,
  Accessory,
  AccessoryStatus,
  AccessoryListParams,
  AccessoryResponse,
  AccessoryListResponse,
  CreateAccessoryRequest,
  UpdateAccessoryRequest,
  AccessoryCheckinRequest,
  AccessoryReturnRequest,
} from './inventory'
export { type Customer as InventoryCustomer } from './inventory'
export * from './customer'
export * from './reports'
export * from './preferences'
export * from './history'
