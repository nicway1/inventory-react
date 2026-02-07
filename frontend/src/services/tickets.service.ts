/**
 * Tickets Service
 *
 * API methods for ticket management.
 */

import { apiClient } from './api'
import type {
  Ticket,
  CreateTicketPayload,
  UpdateTicketPayload,
  Queue,
  Customer,
  UserOption,
} from '@/types'

export interface TicketListParams {
  page?: number
  per_page?: number
  sort?: string
  order?: 'asc' | 'desc'
  search?: string
  status?: string
  queue_id?: number
  priority?: string
  assigned_to_id?: number
  customer_id?: number
  category?: string
  date_from?: string
  date_to?: string
}

export interface TicketListResponse {
  data: Ticket[]
  meta: {
    pagination: {
      page: number
      per_page: number
      total: number
      total_pages: number
    }
    counts: {
      total: number
      new: number
      in_progress: number
      resolved: number
      on_hold: number
    }
  }
}

export interface TicketResponse {
  success: boolean
  data: Ticket
  message?: string
}

/**
 * Get list of tickets with pagination and filtering
 */
export async function getTickets(
  params: TicketListParams = {}
): Promise<TicketListResponse> {
  const searchParams = new URLSearchParams()

  if (params.page) searchParams.append('page', String(params.page))
  if (params.per_page) searchParams.append('per_page', String(params.per_page))
  if (params.sort) searchParams.append('sort', params.sort)
  if (params.order) searchParams.append('order', params.order)
  if (params.search) searchParams.append('search', params.search)
  if (params.status) searchParams.append('status', params.status)
  if (params.queue_id) searchParams.append('queue_id', String(params.queue_id))
  if (params.priority) searchParams.append('priority', params.priority)
  if (params.assigned_to_id)
    searchParams.append('assigned_to_id', String(params.assigned_to_id))
  if (params.customer_id)
    searchParams.append('customer_id', String(params.customer_id))
  if (params.category) searchParams.append('category', params.category)
  if (params.date_from) searchParams.append('date_from', params.date_from)
  if (params.date_to) searchParams.append('date_to', params.date_to)

  const response = await apiClient.get<TicketListResponse>(
    `/v2/tickets?${searchParams.toString()}`
  )
  return response.data
}

/**
 * Get a single ticket by ID
 */
export async function getTicket(id: number): Promise<Ticket> {
  const response = await apiClient.get<TicketResponse>(`/v2/tickets/${id}`)
  return response.data.data
}

/**
 * Create a new ticket
 */
export async function createTicket(
  payload: CreateTicketPayload
): Promise<Ticket> {
  const response = await apiClient.post<TicketResponse>('/v2/tickets', payload)
  return response.data.data
}

/**
 * Update an existing ticket
 */
export async function updateTicket(
  id: number,
  payload: UpdateTicketPayload
): Promise<Ticket> {
  const response = await apiClient.put<TicketResponse>(
    `/v2/tickets/${id}`,
    payload
  )
  return response.data.data
}

/**
 * Delete a ticket
 */
export async function deleteTicket(id: number): Promise<void> {
  await apiClient.delete(`/v2/tickets/${id}`)
}

/**
 * Get list of queues for dropdown
 */
export async function getQueues(): Promise<Queue[]> {
  const response = await apiClient.get<{ data: Queue[] }>('/v2/queues')
  return response.data.data
}

/**
 * Get list of customers for dropdown
 */
export async function getCustomers(search?: string): Promise<Customer[]> {
  const params = search ? `?search=${encodeURIComponent(search)}&limit=50` : '?limit=50'
  const response = await apiClient.get<{ data: Customer[] }>(
    `/v2/customers${params}`
  )
  return response.data.data
}

/**
 * Get list of users for assignee dropdown
 */
export async function getUsers(): Promise<UserOption[]> {
  const response = await apiClient.get<{ data: UserOption[] }>('/v2/users?limit=100')
  return response.data.data
}

/**
 * Upload attachments to a ticket
 */
export async function uploadTicketAttachments(
  ticketId: number,
  files: File[]
): Promise<void> {
  const formData = new FormData()
  files.forEach((file) => {
    formData.append('files', file)
  })

  await apiClient.post(`/v2/tickets/${ticketId}/attachments`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
}

export const ticketsService = {
  getTickets,
  getTicket,
  createTicket,
  updateTicket,
  deleteTicket,
  getQueues,
  getCustomers,
  getUsers,
  uploadTicketAttachments,
}

export default ticketsService
