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
  useDashboardPreferences,
  useSaveDashboardPreferences,
  useResetDashboardPreferences,
  dashboardKeys,
} from './useDashboard'
export {
  useGlobalSearch,
  useSearchSuggestions,
  searchKeys,
} from './useGlobalSearch'
export {
  useTickets,
  useTicket,
  useQueues,
  useAssignees,
  useCreateTicket,
  useUpdateTicket,
  useDeleteTickets,
  useAssignTickets,
  useUpdateTicketsStatus,
  useMoveTicketsToQueue,
  useTicketsRefresh,
  ticketKeys,
} from './useTickets'
export {
  useAssets,
  useAsset,
  useCreateAsset,
  useUpdateAsset,
  useDeleteAsset,
  useUploadAssetImage,
  useTransferAsset,
  useAssetRefresh,
  assetKeys,
} from './useAssets'
export {
  useCustomers,
  useCustomer,
  useCustomerTransactions,
  useCompanies,
  useCustomerCountries,
  useCreateCustomer,
  useUpdateCustomer,
  useDeleteCustomer,
  useCustomerRefresh,
  customerKeys,
} from './useCustomers'
export {
  useAccessories,
  useAccessory,
  useCreateAccessory,
  useUpdateAccessory,
  useDeleteAccessory,
  useCheckinAccessory,
  useReturnAccessory,
  useAccessoryRefresh,
  accessoryKeys,
} from './useAccessories'

export {
  useNotifications,
  useNotificationToasts,
  useNotificationNavigation,
  useNotificationStyles,
} from './useNotifications'

// Re-export organism hooks for convenience
export { useToast } from '@/components/organisms/Toast'
export { useConfirmDialog } from '@/components/organisms/ConfirmDialog'
