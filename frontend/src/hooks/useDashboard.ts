/**
 * Dashboard Hooks
 *
 * React Query hooks for dashboard data fetching.
 */

import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getTicketStats,
  getInventoryStats,
  getRecentTickets,
  getWidgets,
  getWidgetData,
} from '@/services/dashboard.service'
import type {
  TicketStatsData,
  InventoryStatsData,
  Widget,
} from '@/types/dashboard'
import type { TicketListItem } from '@/services/dashboard.service'

// Query keys
export const dashboardKeys = {
  all: ['dashboard'] as const,
  widgets: () => [...dashboardKeys.all, 'widgets'] as const,
  widgetData: (widgetId: string) =>
    [...dashboardKeys.all, 'widget', widgetId] as const,
  ticketStats: () => [...dashboardKeys.all, 'ticketStats'] as const,
  inventoryStats: () => [...dashboardKeys.all, 'inventoryStats'] as const,
  recentTickets: () => [...dashboardKeys.all, 'recentTickets'] as const,
}

/**
 * Hook to fetch ticket statistics
 */
export function useTicketStats(options?: {
  show_resolved?: boolean
  time_period?: '7d' | '30d' | '90d'
  enabled?: boolean
}) {
  return useQuery<TicketStatsData, Error>({
    queryKey: dashboardKeys.ticketStats(),
    queryFn: () =>
      getTicketStats({
        show_resolved: options?.show_resolved,
        time_period: options?.time_period,
      }),
    staleTime: 1000 * 60 * 2, // 2 minutes
    enabled: options?.enabled ?? true,
  })
}

/**
 * Hook to fetch inventory statistics
 */
export function useInventoryStats(options?: { enabled?: boolean }) {
  return useQuery<InventoryStatsData, Error>({
    queryKey: dashboardKeys.inventoryStats(),
    queryFn: getInventoryStats,
    staleTime: 1000 * 60 * 2, // 2 minutes
    enabled: options?.enabled ?? true,
  })
}

/**
 * Hook to fetch recent tickets
 */
export function useRecentTickets(options?: {
  per_page?: number
  enabled?: boolean
}) {
  return useQuery<TicketListItem[], Error>({
    queryKey: dashboardKeys.recentTickets(),
    queryFn: () =>
      getRecentTickets({
        per_page: options?.per_page || 5,
        sort: 'created_at',
        order: 'desc',
      }),
    staleTime: 1000 * 60 * 1, // 1 minute
    enabled: options?.enabled ?? true,
  })
}

/**
 * Hook to fetch available widgets
 */
export function useWidgets(options?: {
  category?: string
  includeAll?: boolean
  enabled?: boolean
}) {
  return useQuery<Widget[], Error>({
    queryKey: dashboardKeys.widgets(),
    queryFn: () =>
      getWidgets({
        category: options?.category,
        includeAll: options?.includeAll,
      }),
    staleTime: 1000 * 60 * 5, // 5 minutes
    enabled: options?.enabled ?? true,
  })
}

/**
 * Hook to fetch data for a specific widget
 */
export function useWidgetData<T = unknown>(
  widgetId: string,
  config?: Record<string, unknown>,
  options?: { enabled?: boolean }
) {
  return useQuery<T, Error>({
    queryKey: dashboardKeys.widgetData(widgetId),
    queryFn: () => getWidgetData<T>(widgetId, config),
    staleTime: 1000 * 60 * 2, // 2 minutes
    enabled: options?.enabled ?? true,
  })
}

/**
 * Hook to refresh all dashboard data
 */
export function useDashboardRefresh() {
  const queryClient = useQueryClient()

  const refreshAll = () => {
    queryClient.invalidateQueries({ queryKey: dashboardKeys.all })
  }

  const refreshTicketStats = () => {
    queryClient.invalidateQueries({ queryKey: dashboardKeys.ticketStats() })
  }

  const refreshInventoryStats = () => {
    queryClient.invalidateQueries({ queryKey: dashboardKeys.inventoryStats() })
  }

  const refreshRecentTickets = () => {
    queryClient.invalidateQueries({ queryKey: dashboardKeys.recentTickets() })
  }

  return {
    refreshAll,
    refreshTicketStats,
    refreshInventoryStats,
    refreshRecentTickets,
  }
}
