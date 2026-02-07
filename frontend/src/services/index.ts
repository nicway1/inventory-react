/**
 * Services Index
 *
 * Export all API services from this file.
 * Each domain should have its own service file.
 */

export { apiClient } from './api'
export { authService } from './auth.service'
export { dashboardService } from './dashboard.service'
export * from './dashboard.service'
export { searchService } from './search.service'
export * from './search.service'

// Domain services
export { ticketsService } from './tickets.service'
export * from './tickets.service'
export { assetsService } from './assets.service'
export * from './assets.service'
export { customerService } from './customer.service'
export * from './customer.service'
export { accessoryService } from './accessory.service'
export * from './accessory.service'
export * from './inventory.service'
export { reportsService } from './reports.service'
export * from './reports.service'
export { preferencesService, profileService, securityService } from './preferences.service'
export { notificationsService } from './notifications.service'
export * from './notifications.service'
export { historyService } from './history.service'
export * from './history.service'
