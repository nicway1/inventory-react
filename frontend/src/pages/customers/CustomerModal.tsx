/**
 * CustomerModal Component
 *
 * Modal for creating and editing customers.
 * Uses react-hook-form with zod validation.
 */

import { useEffect, useMemo } from 'react'
import { useForm, FormProvider } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Modal } from '@/components/organisms/Modal'
import { Button } from '@/components/atoms/Button'
import { FormGroup } from '@/components/molecules/FormGroup'
import { cn } from '@/utils/cn'
import {
  useCreateCustomer,
  useUpdateCustomer,
  useCompanies,
} from '@/hooks/useCustomers'
import type { CustomerListItem, CustomerDetail, Country } from '@/types/customer'
import { COUNTRY_OPTIONS } from '@/types/customer'

// Form validation schema
const customerSchema = z.object({
  name: z.string().min(1, 'Name is required').max(255, 'Name is too long'),
  email: z
    .string()
    .email('Invalid email address')
    .optional()
    .or(z.literal('')),
  contact_number: z.string().max(50, 'Phone number is too long').optional(),
  address: z.string().max(500, 'Address is too long').optional(),
  country: z.string().optional(),
  company_id: z.number().nullable().optional(),
})

type CustomerFormValues = z.infer<typeof customerSchema>

interface CustomerModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  customer?: CustomerListItem | CustomerDetail | null
}

export function CustomerModal({
  isOpen,
  onClose,
  onSuccess,
  customer,
}: CustomerModalProps) {
  const isEditMode = !!customer

  // Mutations
  const createMutation = useCreateCustomer()
  const updateMutation = useUpdateCustomer()

  // Fetch companies for dropdown
  const { data: companies = [] } = useCompanies()

  // Form setup
  const methods = useForm<CustomerFormValues>({
    resolver: zodResolver(customerSchema),
    defaultValues: {
      name: '',
      email: '',
      contact_number: '',
      address: '',
      country: '',
      company_id: null,
    },
  })

  const {
    handleSubmit,
    reset,
    register,
    formState: { errors, isSubmitting },
    setValue,
    watch,
  } = methods

  // Reset form when modal opens/closes or customer changes
  useEffect(() => {
    if (isOpen) {
      if (customer) {
        reset({
          name: customer.name || '',
          email: customer.email || '',
          contact_number: customer.contact_number || '',
          address: customer.address || '',
          country: customer.country || '',
          company_id: customer.company_id || null,
        })
      } else {
        reset({
          name: '',
          email: '',
          contact_number: '',
          address: '',
          country: '',
          company_id: null,
        })
      }
    }
  }, [isOpen, customer, reset])

  // Handle form submission
  const onSubmit = async (data: CustomerFormValues) => {
    try {
      const formData = {
        name: data.name,
        email: data.email || '',
        contact_number: data.contact_number || '',
        address: data.address || '',
        country: (data.country as Country) || null,
        company_id: data.company_id || null,
      }

      if (isEditMode && customer) {
        await updateMutation.mutateAsync({
          id: customer.id,
          data: formData,
        })
      } else {
        await createMutation.mutateAsync(formData)
      }

      onSuccess()
    } catch (error) {
      console.error('Failed to save customer:', error)
    }
  }

  // Loading state
  const isLoading =
    isSubmitting || createMutation.isPending || updateMutation.isPending

  // Error message
  const errorMessage =
    createMutation.error?.message || updateMutation.error?.message

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEditMode ? 'Edit Customer' : 'Add Customer'}
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleSubmit(onSubmit)}
            isLoading={isLoading}
          >
            {isEditMode ? 'Save Changes' : 'Create Customer'}
          </Button>
        </>
      }
    >
      <FormProvider {...methods}>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Error Alert */}
          {errorMessage && (
            <div className="p-3 rounded bg-red-50 border border-red-200 text-red-700 text-sm">
              {errorMessage}
            </div>
          )}

          {/* Name */}
          <FormGroup
            name="name"
            label="Name"
            required
            placeholder="Enter customer name"
          />

          {/* Email */}
          <FormGroup
            name="email"
            label="Email"
            type="email"
            placeholder="Enter email address"
          />

          {/* Phone */}
          <FormGroup
            name="contact_number"
            label="Phone"
            type="tel"
            placeholder="Enter phone number"
          />

          {/* Address */}
          <div>
            <label
              htmlFor="address"
              className={cn(
                'block text-xs font-medium mb-1.5 uppercase tracking-wide',
                'text-[#706E6B] dark:text-gray-400'
              )}
            >
              Address
            </label>
            <textarea
              id="address"
              {...register('address')}
              rows={3}
              placeholder="Enter address"
              className={cn(
                'w-full rounded border px-3 py-2 text-sm',
                'bg-white dark:bg-gray-800',
                'text-gray-900 dark:text-gray-100',
                'border-[#DDDBDA] dark:border-gray-600',
                'focus:outline-none focus:ring-2 focus:ring-[#0176D3]/20 focus:border-[#0176D3]',
                'placeholder:text-gray-400 dark:placeholder:text-gray-500',
                errors.address && 'border-red-500 focus:border-red-500'
              )}
            />
            {errors.address && (
              <p className="mt-1.5 text-xs text-red-500">
                {errors.address.message}
              </p>
            )}
          </div>

          {/* Country */}
          <div>
            <label
              htmlFor="country"
              className={cn(
                'block text-xs font-medium mb-1.5 uppercase tracking-wide',
                'text-[#706E6B] dark:text-gray-400'
              )}
            >
              Country
            </label>
            <select
              id="country"
              {...register('country')}
              className={cn(
                'w-full h-10 rounded border px-3 text-sm',
                'bg-white dark:bg-gray-800',
                'text-gray-900 dark:text-gray-100',
                'border-[#DDDBDA] dark:border-gray-600',
                'focus:outline-none focus:ring-2 focus:ring-[#0176D3]/20 focus:border-[#0176D3]'
              )}
            >
              <option value="">Select a country</option>
              {COUNTRY_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          {/* Company */}
          <div>
            <label
              htmlFor="company_id"
              className={cn(
                'block text-xs font-medium mb-1.5 uppercase tracking-wide',
                'text-[#706E6B] dark:text-gray-400'
              )}
            >
              Company
            </label>
            <select
              id="company_id"
              value={watch('company_id') || ''}
              onChange={(e) =>
                setValue(
                  'company_id',
                  e.target.value ? Number(e.target.value) : null
                )
              }
              className={cn(
                'w-full h-10 rounded border px-3 text-sm',
                'bg-white dark:bg-gray-800',
                'text-gray-900 dark:text-gray-100',
                'border-[#DDDBDA] dark:border-gray-600',
                'focus:outline-none focus:ring-2 focus:ring-[#0176D3]/20 focus:border-[#0176D3]'
              )}
            >
              <option value="">No company</option>
              {companies.map((company) => (
                <option key={company.id} value={company.id}>
                  {company.name}
                </option>
              ))}
            </select>
          </div>
        </form>
      </FormProvider>
    </Modal>
  )
}

export default CustomerModal
