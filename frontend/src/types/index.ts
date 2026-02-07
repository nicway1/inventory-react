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
export * from './ticket'
export * from './tickets'
export * from './assets'
export * from './inventory'
export * from './customer'
