/**
 * CreateTicketPage Component
 *
 * Create new service ticket page with form validation using React Hook Form + Zod.
 */

import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm, FormProvider, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { PageLayout } from '@/components/templates/PageLayout'
import { Button, Input, Select, TextArea } from '@/components/atoms'
import { FormGroup, FormSection, FormActions, FormLabel, FormError } from '@/components/molecules/FormGroup'
import { Card } from '@/components/molecules/Card'
import { useToast } from '@/hooks'
import { cn } from '@/utils/cn'
import {
  createTicket,
  getQueues,
  getCustomers,
  getUsers,
  uploadTicketAttachments,
} from '@/services/tickets.service'
import type { Queue, Customer, UserOption } from '@/types'
import { PRIORITY_OPTIONS, CATEGORY_OPTIONS } from '@/types/tickets'

// Form validation schema
const ticketFormSchema = z.object({
  subject: z
    .string()
    .min(1, 'Subject is required')
    .max(200, 'Subject must be less than 200 characters'),
  description: z.string().optional(),
  category: z.string().optional(),
  priority: z.string().min(1, 'Priority is required'),
  queue_id: z.string().min(1, 'Queue is required'),
  customer_id: z.string().optional(),
  assigned_to_id: z.string().optional(),
  notes: z.string().optional(),
})

type TicketFormValues = z.infer<typeof ticketFormSchema>

export function CreateTicketPage() {
  const navigate = useNavigate()
  const { success, error: showError } = useToast()

  // Data states
  const [queues, setQueues] = useState<Queue[]>([])
  const [customers, setCustomers] = useState<Customer[]>([])
  const [users, setUsers] = useState<UserOption[]>([])
  const [isLoadingData, setIsLoadingData] = useState(true)

  // File upload state
  const [attachments, setAttachments] = useState<File[]>([])

  // Form state
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Initialize form
  const methods = useForm<TicketFormValues>({
    resolver: zodResolver(ticketFormSchema),
    defaultValues: {
      subject: '',
      description: '',
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
    formState: { errors },
    watch,
  } = methods

  // Watch category for category guide highlighting
  const selectedCategory = watch('category')

  // Load dropdown data
  useEffect(() => {
    async function loadData() {
      setIsLoadingData(true)
      try {
        const [queuesData, customersData, usersData] = await Promise.all([
          getQueues(),
          getCustomers(),
          getUsers(),
        ])
        setQueues(queuesData)
        setCustomers(customersData)
        setUsers(usersData)
      } catch (err) {
        showError('Failed to load form data')
        console.error('Error loading form data:', err)
      } finally {
        setIsLoadingData(false)
      }
    }
    loadData()
  }, [showError])

  // Handle file selection
  const handleFileChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const files = event.target.files
      if (files) {
        setAttachments((prev) => [...prev, ...Array.from(files)])
      }
    },
    []
  )

  // Remove attachment
  const removeAttachment = useCallback((index: number) => {
    setAttachments((prev) => prev.filter((_, i) => i !== index))
  }, [])

  // Handle form submission
  const onSubmit = async (data: TicketFormValues) => {
    setIsSubmitting(true)
    try {
      // Prepare payload
      const payload = {
        subject: data.subject,
        description: data.description || undefined,
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

      // Create ticket
      const ticket = await createTicket(payload)

      // Upload attachments if any
      if (attachments.length > 0 && ticket.id) {
        try {
          await uploadTicketAttachments(ticket.id, attachments)
        } catch (uploadErr) {
          console.error('Failed to upload attachments:', uploadErr)
          // Continue even if attachment upload fails
        }
      }

      success(`Ticket ${ticket.display_id || ticket.id} created successfully`)
      navigate(`/tickets/${ticket.id}`)
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to create ticket'
      showError(errorMessage)
      console.error('Error creating ticket:', err)
    } finally {
      setIsSubmitting(false)
    }
  }

  // Handle cancel
  const handleCancel = () => {
    navigate('/tickets')
  }

  // Queue options for select
  const queueOptions = queues.map((q) => ({ value: String(q.id), label: q.name }))

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
    <PageLayout
      title="New Ticket"
      subtitle="Create a new service ticket"
      breadcrumbs={[
        { label: 'Tickets', href: '/tickets' },
        { label: 'New Ticket' },
      ]}
      isLoading={isLoadingData}
    >
      <FormProvider {...methods}>
        <form onSubmit={handleSubmit(onSubmit)} className="max-w-4xl">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Category Guide - Left Column */}
            <div className="lg:col-span-1">
              <Card className="sticky top-8">
                <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
                    <svg
                      className="w-5 h-5 mr-2 text-[#0176D3]"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                    Category Guide
                  </h3>
                </div>
                <div className="p-4 space-y-2 max-h-[500px] overflow-y-auto">
                  {CATEGORY_OPTIONS.map((category) => (
                    <button
                      key={category.value}
                      type="button"
                      onClick={() =>
                        methods.setValue('category', String(category.value))
                      }
                      className={cn(
                        'w-full p-3 rounded-lg border text-left transition-all',
                        selectedCategory === category.value
                          ? 'border-[#0176D3] bg-blue-50 dark:bg-blue-900/20'
                          : 'border-gray-200 dark:border-gray-700 hover:border-[#0176D3] hover:bg-gray-50 dark:hover:bg-gray-800'
                      )}
                    >
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        {category.label}
                      </p>
                      {category.description && (
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                          {category.description}
                        </p>
                      )}
                    </button>
                  ))}
                </div>
              </Card>
            </div>

            {/* Main Form - Right Column */}
            <div className="lg:col-span-2">
              <Card>
                <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    Ticket Details
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                    Fill in the required information below
                  </p>
                </div>

                <div className="p-6 space-y-6">
                  {/* Subject */}
                  <FormSection>
                    <div>
                      <FormLabel required>Subject</FormLabel>
                      <Input
                        {...register('subject')}
                        placeholder="Enter ticket subject..."
                        error={errors.subject?.message}
                      />
                    </div>
                  </FormSection>

                  {/* Category & Priority Row */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <FormLabel>Category</FormLabel>
                      <Controller
                        name="category"
                        control={control}
                        render={({ field }) => (
                          <Select
                            {...field}
                            placeholder="Select category..."
                            options={CATEGORY_OPTIONS.map((c) => ({
                              value: String(c.value),
                              label: c.label,
                            }))}
                            error={errors.category?.message}
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

                  {/* Queue */}
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
                    <p className="mt-1.5 text-sm text-gray-500">
                      Select which support queue this ticket should be assigned
                      to
                    </p>
                  </div>

                  {/* Customer & Assignee Row */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
                      rows={5}
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

                  {/* Attachments */}
                  <div>
                    <FormLabel>Attachments</FormLabel>
                    <div className="mt-1">
                      <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg cursor-pointer hover:border-[#0176D3] hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                        <div className="flex flex-col items-center justify-center pt-5 pb-6">
                          <svg
                            className="w-8 h-8 mb-2 text-gray-400"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                            />
                          </svg>
                          <p className="text-sm text-gray-500 dark:text-gray-400">
                            <span className="font-semibold">
                              Click to upload
                            </span>{' '}
                            or drag and drop
                          </p>
                          <p className="text-xs text-gray-400">
                            PNG, JPG, PDF up to 10MB
                          </p>
                        </div>
                        <input
                          type="file"
                          className="hidden"
                          multiple
                          accept="image/*,.pdf,.doc,.docx"
                          onChange={handleFileChange}
                        />
                      </label>

                      {/* Attachment list */}
                      {attachments.length > 0 && (
                        <ul className="mt-3 space-y-2">
                          {attachments.map((file, index) => (
                            <li
                              key={`${file.name}-${index}`}
                              className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded"
                            >
                              <div className="flex items-center">
                                <svg
                                  className="w-5 h-5 text-gray-400 mr-2"
                                  fill="none"
                                  stroke="currentColor"
                                  viewBox="0 0 24 24"
                                >
                                  <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
                                  />
                                </svg>
                                <span className="text-sm text-gray-700 dark:text-gray-300 truncate max-w-xs">
                                  {file.name}
                                </span>
                                <span className="text-xs text-gray-400 ml-2">
                                  ({(file.size / 1024).toFixed(1)} KB)
                                </span>
                              </div>
                              <button
                                type="button"
                                onClick={() => removeAttachment(index)}
                                className="p-1 text-gray-400 hover:text-red-500"
                              >
                                <svg
                                  className="w-4 h-4"
                                  fill="none"
                                  stroke="currentColor"
                                  viewBox="0 0 24 24"
                                >
                                  <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M6 18L18 6M6 6l12 12"
                                  />
                                </svg>
                              </button>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </div>

                  {/* Form Actions */}
                  <FormActions align="right">
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={handleCancel}
                      disabled={isSubmitting}
                    >
                      Cancel
                    </Button>
                    <Button
                      type="submit"
                      variant="primary"
                      isLoading={isSubmitting}
                    >
                      Create Ticket
                    </Button>
                  </FormActions>
                </div>
              </Card>
            </div>
          </div>
        </form>
      </FormProvider>
    </PageLayout>
  )
}

export default CreateTicketPage
