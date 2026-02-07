/**
 * Custom Hooks Index
 *
 * Export all custom React hooks from this file.
 */

export { useDebounce } from './useDebounce'
export { useLocalStorage } from './useLocalStorage'
export { useAuth } from './useAuth'
export {
  useTicketStats,
  useInventoryStats,
  useRecentTickets,
  useWidgets,
  useWidgetData,
  useDashboardRefresh,
  dashboardKeys,
} from './useDashboard'

// Re-export organism hooks for convenience
export { useToast } from '@/components/organisms/Toast'
export { useConfirmDialog } from '@/components/organisms/ConfirmDialog'
