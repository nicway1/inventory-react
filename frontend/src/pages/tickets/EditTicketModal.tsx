/**
 * EditTicketModal Component
 *
 * Modal for editing an existing ticket with form validation.
 */

import { useState, useEffect } from 'react'
import { useForm, FormProvider, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Modal } from '@/components/organisms/Modal'
import { Button, Input, Select, TextArea } from '@/components/atoms'
import { FormLabel } from '@/components/molecules/FormGroup'
import { useToast } from '@/hooks'
import {
  getTicket,
  updateTicket,
  getQueues,
  getCustomers,
  getUsers,
} from '@/services/tickets.service'
import type { Ticket, Queue, Customer, UserOption } from '@/types'
import { PRIORITY_OPTIONS, CATEGORY_OPTIONS } from '@/types/tickets'

// Status options
const STATUS_OPTIONS = [
  { value: 'New', label: 'New' },
  { value: 'In Progress', label: 'In Progress' },
  { value: 'On Hold', label: 'On Hold' },
  { value: 'Processing', label: 'Processing' },
  { value: 'Resolved', label: 'Resolved' },
  { value: 'Resolved - Delivered', label: 'Resolved - Delivered' },
  { value: 'Closed', label: 'Closed' },
]

// Form validation schema
const editTicketSchema = z.object({
  subject: z
    .string()
    .min(1, 'Subject is required')
    .max(200, 'Subject must be less than 200 characters'),
  description: z.string().optional(),
  status: z.string().min(1, 'Status is required'),
  category: z.string().optional(),
  priority: z.string().min(1, 'Priority is required'),
  queue_id: z.string().min(1, 'Queue is required'),
  customer_id: z.string().optional(),
  assigned_to_id: z.string().optional(),
  notes: z.string().optional(),
})

type EditTicketFormValues = z.infer<typeof editTicketSchema>

interface EditTicketModalProps {
  ticketId: number | null
  isOpen: boolean
  onClose: () => void
  onSuccess?: (ticket: Ticket) => void
}

export function EditTicketModal({
  ticketId,
  isOpen,
  onClose,
  onSuccess,
}: EditTicketModalProps) {
  const { success, error: showError } = useToast()

  // Data states
  const [queues, setQueues] = useState<Queue[]>([])
  const [customers, setCustomers] = useState<Customer[]>([])
  const [users, setUsers] = useState<UserOption[]>([])
  const [isLoadingData, setIsLoadingData] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [ticket, setTicket] = useState<Ticket | null>(null)

  // Initialize form
  const methods = useForm<EditTicketFormValues>({
    resolver: zodResolver(editTicketSchema),
    defaultValues: {
      subject: '',
      description: '',
      status: '',
      category: '',
      priority: 'Medium',
      queue_id: '',
      customer_id: '',
      assigned_to_id: '',
      notes: '',
    },
  })

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors },
  } = methods

  // Load data when modal opens
  useEffect(() => {
    async function loadData() {
      if (!isOpen || !ticketId) return

      setIsLoadingData(true)
      try {
        const [ticketData, queuesData, customersData, usersData] =
          await Promise.all([
            getTicket(ticketId),
            getQueues(),
            getCustomers(),
            getUsers(),
          ])

        setTicket(ticketData)
        setQueues(queuesData)
        setCustomers(customersData)
        setUsers(usersData)

        // Reset form with ticket data
        reset({
          subject: ticketData.subject || '',
          description: ticketData.description || '',
          status: ticketData.status || '',
          category: ticketData.category || '',
          priority: ticketData.priority || 'Medium',
          queue_id: ticketData.queue_id ? String(ticketData.queue_id) : '',
          customer_id: ticketData.customer_id
            ? String(ticketData.customer_id)
            : '',
          assigned_to_id: ticketData.assigned_to_id
            ? String(ticketData.assigned_to_id)
            : '',
          notes: ticketData.notes || '',
        })
      } catch (err) {
        showError('Failed to load ticket data')
        console.error('Error loading ticket data:', err)
        onClose()
      } finally {
        setIsLoadingData(false)
      }
    }

    loadData()
  }, [isOpen, ticketId, reset, showError, onClose])

  // Handle form submission
  const onSubmit = async (data: EditTicketFormValues) => {
    if (!ticketId) return

    setIsSubmitting(true)
    try {
      const payload = {
        subject: data.subject,
        description: data.description || undefined,
        status: data.status,
        category: data.category || undefined,
        priority: data.priority,
        queue_id: parseInt(data.queue_id, 10),
        customer_id: data.customer_id
          ? parseInt(data.customer_id, 10)
          : undefined,
        assigned_to_id: data.assigned_to_id
          ? parseInt(data.assigned_to_id, 10)
          : undefined,
        notes: data.notes || undefined,
      }

      const updatedTicket = await updateTicket(ticketId, payload)

      success(
        `Ticket ${updatedTicket.display_id || updatedTicket.id} updated successfully`
      )
      onSuccess?.(updatedTicket)
      onClose()
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to update ticket'
      showError(errorMessage)
      console.error('Error updating ticket:', err)
    } finally {
      setIsSubmitting(false)
    }
  }

  // Queue options for select
  const queueOptions = queues.map((q) => ({
    value: String(q.id),
    label: q.name,
  }))

  // Customer options for select
  const customerOptions = [
    { value: '', label: 'Select customer...' },
    ...customers.map((c) => ({
      value: String(c.id),
      label: c.company ? `${c.name} (${c.company})` : c.name,
    })),
  ]

  // User options for assignee select
  const userOptions = [
    { value: '', label: 'Select assignee...' },
    ...users.map((u) => ({
      value: String(u.id),
      label: u.first_name
        ? `${u.first_name} ${u.last_name || ''} (${u.username})`
        : u.username,
    })),
  ]

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Edit Ticket ${ticket?.display_id || `#${ticketId}`}`}
      size="lg"
      footer={
        <>
          <Button
            type="button"
            variant="secondary"
            onClick={onClose}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            isLoading={isSubmitting}
            onClick={handleSubmit(onSubmit)}
          >
            Save Changes
          </Button>
        </>
      }
    >
      {isLoadingData ? (
        <div className="flex items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
        </div>
      ) : (
        <FormProvider {...methods}>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* Subject */}
            <div>
              <FormLabel required>Subject</FormLabel>
              <Input
                {...register('subject')}
                placeholder="Enter ticket subject..."
                error={errors.subject?.message}
              />
            </div>

            {/* Status & Priority Row */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <FormLabel required>Status</FormLabel>
                <Controller
                  name="status"
                  control={control}
                  render={({ field }) => (
                    <Select
                      {...field}
                      options={STATUS_OPTIONS}
                      error={errors.status?.message}
                    />
                  )}
                />
              </div>
              <div>
                <FormLabel required>Priority</FormLabel>
                <Controller
                  name="priority"
                  control={control}
                  render={({ field }) => (
                    <Select
                      {...field}
                      options={PRIORITY_OPTIONS.map((p) => ({
                        value: String(p.value),
                        label: p.label,
                      }))}
                      error={errors.priority?.message}
                    />
                  )}
                />
              </div>
            </div>

            {/* Category & Queue Row */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <FormLabel>Category</FormLabel>
                <Controller
                  name="category"
                  control={control}
                  render={({ field }) => (
                    <Select
                      {...field}
                      placeholder="Select category..."
                      options={[
                        { value: '', label: 'Select category...' },
                        ...CATEGORY_OPTIONS.map((c) => ({
                          value: String(c.value),
                          label: c.label,
                        })),
                      ]}
                      error={errors.category?.message}
                    />
                  )}
                />
              </div>
              <div>
                <FormLabel required>Queue</FormLabel>
                <Controller
                  name="queue_id"
                  control={control}
                  render={({ field }) => (
                    <Select
                      {...field}
                      placeholder="Select queue..."
                      options={queueOptions}
                      error={errors.queue_id?.message}
                    />
                  )}
                />
              </div>
            </div>

            {/* Customer & Assignee Row */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <FormLabel>Customer</FormLabel>
                <Controller
                  name="customer_id"
                  control={control}
                  render={({ field }) => (
                    <Select
                      {...field}
                      options={customerOptions}
                      error={errors.customer_id?.message}
                    />
                  )}
                />
              </div>
              <div>
                <FormLabel>Assignee</FormLabel>
                <Controller
                  name="assigned_to_id"
                  control={control}
                  render={({ field }) => (
                    <Select
                      {...field}
                      options={userOptions}
                      error={errors.assigned_to_id?.message}
                    />
                  )}
                />
              </div>
            </div>

            {/* Description */}
            <div>
              <FormLabel>Description</FormLabel>
              <TextArea
                {...register('description')}
                placeholder="Describe the issue or request..."
                rows={4}
                error={errors.description?.message}
              />
            </div>

            {/* Notes */}
            <div>
              <FormLabel>Internal Notes</FormLabel>
              <TextArea
                {...register('notes')}
                placeholder="Add any internal notes..."
                rows={3}
                error={errors.notes?.message}
              />
            </div>
          </form>
        </FormProvider>
      )}
    </Modal>
  )
}

export default EditTicketModal
