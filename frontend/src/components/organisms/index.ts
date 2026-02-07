/**
 * Organism Components
 *
 * Complex UI sections: navigation, forms, tables, modals, etc.
 * These are larger, self-contained sections of the interface.
 */

// Layout components
export { Sidebar } from './Sidebar'
export { Header } from './Header'

// DataTable - Feature-rich data table component
export { DataTable } from './DataTable'
export type { DataTableProps, ColumnDef } from './DataTable'

// Modal - Accessible modal dialog
export { Modal } from './Modal'
export type { ModalProps } from './Modal'

// Toast - Toast notifications and hook
export { ToastContainer, useToast } from './Toast'
export type { ToastType, ToastPosition, ToastData, ToastContainerProps } from './Toast'

// ConfirmDialog - Confirmation dialogs
export { ConfirmDialog, useConfirmDialog } from './ConfirmDialog'
export type { ConfirmDialogProps, ConfirmDialogVariant } from './ConfirmDialog'

// EmptyState - Empty state displays
export {
  EmptyState,
  NoSearchResults,
  NoFilterResults,
  NoDataAvailable,
  ErrorState,
} from './EmptyState'
export type { EmptyStateProps, EmptyStatePreset } from './EmptyState'

// Dashboard Widgets
export * from './widgets'
