/**
 * UI Store
 *
 * Manages UI state like sidebar, modals, and notifications.
 */

import { create } from 'zustand'
import type { Toast } from '@/types'

interface UIState {
  // Sidebar
  sidebarOpen: boolean
  sidebarCollapsed: boolean
  isMobileMenuOpen: boolean

  // Modals
  activeModal: string | null
  modalData: Record<string, unknown> | null

  // Toasts
  toasts: Toast[]

  // Actions
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
  setSidebarCollapsed: (collapsed: boolean) => void
  toggleMobileMenu: () => void
  setMobileMenuOpen: (open: boolean) => void

  openModal: (modalId: string, data?: Record<string, unknown>) => void
  closeModal: () => void

  addToast: (toast: Omit<Toast, 'id'>) => void
  removeToast: (id: string) => void
  clearToasts: () => void
}

export const useUIStore = create<UIState>((set) => ({
  // Initial state
  sidebarOpen: true,
  sidebarCollapsed: false,
  isMobileMenuOpen: false,
  activeModal: null,
  modalData: null,
  toasts: [],

  // Sidebar actions
  toggleSidebar: () =>
    set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

  setSidebarOpen: (open) =>
    set({ sidebarOpen: open }),

  setSidebarCollapsed: (collapsed) =>
    set({ sidebarCollapsed: collapsed }),

  toggleMobileMenu: () =>
    set((state) => ({ isMobileMenuOpen: !state.isMobileMenuOpen })),

  setMobileMenuOpen: (open) =>
    set({ isMobileMenuOpen: open }),

  // Modal actions
  openModal: (modalId, data = null) =>
    set({ activeModal: modalId, modalData: data }),

  closeModal: () =>
    set({ activeModal: null, modalData: null }),

  // Toast actions
  addToast: (toast) =>
    set((state) => ({
      toasts: [
        ...state.toasts,
        { ...toast, id: `toast-${Date.now()}-${Math.random()}` },
      ],
    })),

  removeToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    })),

  clearToasts: () =>
    set({ toasts: [] }),
}))
