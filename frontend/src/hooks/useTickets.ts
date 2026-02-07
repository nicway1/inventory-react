/**
 * Ticket Hooks
 *
 * React Query hooks for ticket data fetching and mutations.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getTickets,
  getTicket,
  createTicket,
  updateTicket,
  getQueues,
  getUsers,
  deleteTicket,
  type TicketListParams,
  type TicketListResponse,
} from '@/services/tickets.service'
import { apiClient } from '@/services/api'
import type { Ticket, Queue, Assignee, CreateTicketRequest, UpdateTicketRequest } from '@/types/ticket'

// Query keys
export const ticketKeys = {
  all: ['tickets'] as const,
  lists: () => [...ticketKeys.all, 'list'] as const,
  list: (params: TicketListParams) => [...ticketKeys.lists(), params] as const,
  details: () => [...ticketKeys.all, 'detail'] as const,
  detail: (id: number) => [...ticketKeys.details(), id] as const,
  queues: () => [...ticketKeys.all, 'queues'] as const,
  assignees: () => [...ticketKeys.all, 'assignees'] as const,
}

/**
 * Hook to fetch paginated tickets
 */
export function useTickets(
  params: TicketListParams,
  options?: { enabled?: boolean }
) {
  return useQuery<TicketListResponse, Error>({
    queryKey: ticketKeys.list(params),
    queryFn: () => getTickets(params),
    staleTime: 1000 * 60 * 1, // 1 minute
    enabled: options?.enabled ?? true,
  })
}

/**
 * Hook to fetch single ticket
 */
export function useTicket(id: number, options?: { enabled?: boolean }) {
  return useQuery<Ticket, Error>({
    queryKey: ticketKeys.detail(id),
    queryFn: () => getTicket(id),
    staleTime: 1000 * 60 * 2, // 2 minutes
    enabled: (options?.enabled ?? true) && id > 0,
  })
}

/**
 * Hook to fetch queues
 */
export function useQueues(options?: { enabled?: boolean }) {
  return useQuery<Queue[], Error>({
    queryKey: ticketKeys.queues(),
    queryFn: getQueues,
    staleTime: 1000 * 60 * 5, // 5 minutes
    enabled: options?.enabled ?? true,
  })
}

/**
 * Hook to fetch assignees (users who can be assigned tickets)
 */
export function useAssignees(options?: { enabled?: boolean }) {
  return useQuery<Assignee[], Error>({
    queryKey: ticketKeys.assignees(),
    queryFn: async () => {
      const users = await getUsers()
      // Transform UserOption to Assignee format
      return users.map((user) => ({
        id: user.id,
        username: user.username || '',
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        full_name: user.full_name || `${user.first_name} ${user.last_name}`.trim() || user.username || '',
      }))
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
    enabled: options?.enabled ?? true,
  })
}

/**
 * Helper function to delete multiple tickets
 */
async function deleteTickets(ids: number[]): Promise<{ success: boolean; message: string }> {
  // Delete tickets one by one (or implement bulk endpoint if available)
  await Promise.all(ids.map((id) => deleteTicket(id)))
  return { success: true, message: `Deleted ${ids.length} ticket(s)` }
}

/**
 * Helper function to assign multiple tickets
 */
async function assignTickets(
  ticketIds: number[],
  assigneeId: number
): Promise<{ success: boolean; message: string }> {
  const response = await apiClient.post<{ success: boolean; message: string }>(
    '/v2/tickets/bulk/assign',
    { ticket_ids: ticketIds, assigned_to_id: assigneeId }
  )
  return response.data
}

/**
 * Helper function to update status of multiple tickets
 */
async function updateTicketsStatus(
  ticketIds: number[],
  status: string
): Promise<{ success: boolean; message: string }> {
  const response = await apiClient.post<{ success: boolean; message: string }>(
    '/v2/tickets/bulk/status',
    { ticket_ids: ticketIds, status }
  )
  return response.data
}

/**
 * Helper function to move tickets to a queue
 */
async function moveTicketsToQueue(
  ticketIds: number[],
  queueId: number
): Promise<{ success: boolean; message: string }> {
  const response = await apiClient.post<{ success: boolean; message: string }>(
    '/v2/tickets/bulk/queue',
    { ticket_ids: ticketIds, queue_id: queueId }
  )
  return response.data
}

/**
 * Hook for bulk delete tickets
 */
export function useDeleteTickets() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (ids: number[]) => deleteTickets(ids),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ticketKeys.lists() })
    },
  })
}

/**
 * Hook for bulk assign tickets
 */
export function useAssignTickets() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ ticketIds, assigneeId }: { ticketIds: number[]; assigneeId: number }) =>
      assignTickets(ticketIds, assigneeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ticketKeys.lists() })
    },
  })
}

/**
 * Hook for bulk status update
 */
export function useUpdateTicketsStatus() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ ticketIds, status }: { ticketIds: number[]; status: string }) =>
      updateTicketsStatus(ticketIds, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ticketKeys.lists() })
    },
  })
}

/**
 * Hook for moving tickets to queue
 */
export function useMoveTicketsToQueue() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ ticketIds, queueId }: { ticketIds: number[]; queueId: number }) =>
      moveTicketsToQueue(ticketIds, queueId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ticketKeys.lists() })
    },
  })
}

/**
 * Hook to create a ticket
 */
export function useCreateTicket() {
  const queryClient = useQueryClient()

  return useMutation<Ticket, Error, CreateTicketRequest>({
    mutationFn: createTicket,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ticketKeys.lists() })
    },
  })
}

/**
 * Hook to update a ticket
 */
export function useUpdateTicket() {
  const queryClient = useQueryClient()

  return useMutation<Ticket, Error, { id: number; data: UpdateTicketRequest }>({
    mutationFn: ({ id, data }) => updateTicket(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ticketKeys.lists() })
      queryClient.invalidateQueries({ queryKey: ticketKeys.detail(id) })
    },
  })
}

/**
 * Hook to refresh tickets list
 */
export function useTicketsRefresh() {
  const queryClient = useQueryClient()

  const refreshList = () => {
    queryClient.invalidateQueries({ queryKey: ticketKeys.lists() })
  }

  const refreshAll = () => {
    queryClient.invalidateQueries({ queryKey: ticketKeys.all })
  }

  return {
    refreshList,
    refreshAll,
  }
}
