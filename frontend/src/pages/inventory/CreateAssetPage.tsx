/**
 * CreateAssetPage Component
 *
 * Create new asset page with form validation using React Hook Form + Zod.
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm, FormProvider, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { PageLayout } from '@/components/templates/PageLayout'
import { Button, Input, Select, TextArea } from '@/components/atoms'
import { FormSection, FormActions, FormLabel } from '@/components/molecules/FormGroup'
import { Card } from '@/components/molecules/Card'
import { useToast } from '@/hooks'
import { cn } from '@/utils/cn'
import { createAsset, uploadAssetImage } from '@/services/assets.service'
import { getCustomers } from '@/services/tickets.service'
import type { Customer } from '@/types'
import {
  STATUS_OPTIONS,
  CONDITION_OPTIONS,
  ASSET_TYPE_OPTIONS,
  MANUFACTURER_OPTIONS,
} from '@/types/assets'

// Form validation schema
const assetFormSchema = z.object({
  name: z.string().min(1, 'Name is required').max(200, 'Name must be less than 200 characters'),
  asset_tag: z.string().optional(),
  serial_number: z.string().optional(),
  model: z.string().optional(),
  manufacturer: z.string().optional(),
  asset_type: z.string().optional(),
  status: z.string().min(1, 'Status is required'),
  condition: z.string().optional(),
  cpu_type: z.string().optional(),
  memory: z.string().optional(),
  harddrive: z.string().optional(),
  customer: z.string().optional(),
  notes: z.string().optional(),
  auto_generate_tag: z.boolean().optional(),
})

type AssetFormValues = z.infer<typeof assetFormSchema>

export function CreateAssetPage() {
  const navigate = useNavigate()
  const { success, error: showError } = useToast()
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Data states
  const [customers, setCustomers] = useState<Customer[]>([])
  const [isLoadingData, setIsLoadingData] = useState(true)

  // Image upload state
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)

  // Form state
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [autoGenerateTag, setAutoGenerateTag] = useState(true)

  // Initialize form
  const methods = useForm<AssetFormValues>({
    resolver: zodResolver(assetFormSchema),
    defaultValues: {
      name: '',
      asset_tag: '',
      serial_number: '',
      model: '',
      manufacturer: '',
      asset_type: '',
      status: 'IN_STOCK',
      condition: 'Good',
      cpu_type: '',
      memory: '',
      harddrive: '',
      customer: '',
      notes: '',
      auto_generate_tag: true,
    },
  })

  const {
    register,
    handleSubmit,
    control,
    setValue,
    watch,
    formState: { errors },
  } = methods

  // Load dropdown data
  useEffect(() => {
    async function loadData() {
      setIsLoadingData(true)
      try {
        const customersData = await getCustomers()
        setCustomers(customersData)
      } catch (err) {
        showError('Failed to load form data')
        console.error('Error loading form data:', err)
      } finally {
        setIsLoadingData(false)
      }
    }
    loadData()
  }, [showError])

  // Handle image selection
  const handleImageChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0]
      if (file) {
        // Validate file type
        const validTypes = ['image/png', 'image/jpeg', 'image/gif', 'image/webp']
        if (!validTypes.includes(file.type)) {
          showError('Invalid file type. Please upload a PNG, JPG, GIF, or WebP image.')
          return
        }

        // Validate file size (5MB max)
        if (file.size > 5 * 1024 * 1024) {
          showError('File too large. Maximum size is 5MB.')
          return
        }

        setImageFile(file)

        // Create preview
        const reader = new FileReader()
        reader.onloadend = () => {
          setImagePreview(reader.result as string)
        }
        reader.readAsDataURL(file)
      }
    },
    [showError]
  )

  // Remove image
  const removeImage = useCallback(() => {
    setImageFile(null)
    setImagePreview(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }, [])

  // Generate asset tag
  const generateAssetTag = useCallback(() => {
    const timestamp = Date.now().toString(36).toUpperCase()
    const random = Math.random().toString(36).substring(2, 6).toUpperCase()
    return `TL-${timestamp}-${random}`
  }, [])

  // Handle form submission
  const onSubmit = async (data: AssetFormValues) => {
    setIsSubmitting(true)
    try {
      // Generate asset tag if auto-generate is enabled and no tag provided
      let assetTag = data.asset_tag
      if (autoGenerateTag && !assetTag) {
        assetTag = generateAssetTag()
      }

      // Validate that at least asset_tag or serial_number is provided
      if (!assetTag && !data.serial_number) {
        showError('Either Asset Tag or Serial Number is required')
        setIsSubmitting(false)
        return
      }

      // Prepare payload
      const payload = {
        name: data.name,
        asset_tag: assetTag || undefined,
        serial_number: data.serial_number || undefined,
        model: data.model || undefined,
        manufacturer: data.manufacturer || undefined,
        asset_type: data.asset_type || undefined,
        status: data.status,
        condition: data.condition || undefined,
        cpu_type: data.cpu_type || undefined,
        memory: data.memory || undefined,
        harddrive: data.harddrive || undefined,
        customer: data.customer || undefined,
        notes: data.notes || undefined,
      }

      // Create asset
      const asset = await createAsset(payload)

      // Upload image if provided
      if (imageFile && asset.id) {
        try {
          await uploadAssetImage(asset.id, imageFile)
        } catch (uploadErr) {
          console.error('Failed to upload image:', uploadErr)
          // Continue even if image upload fails
        }
      }

      success(`Asset ${asset.asset_tag || asset.serial_number} created successfully`)
      navigate(`/inventory/${asset.id}`)
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to create asset'
      showError(errorMessage)
      console.error('Error creating asset:', err)
    } finally {
      setIsSubmitting(false)
    }
  }

  // Handle cancel
  const handleCancel = () => {
    navigate('/inventory')
  }

  // Customer options for select
  const customerOptions = [
    { value: '', label: 'Select customer (optional)...' },
    ...customers.map((c) => ({
      value: c.name,
      label: c.company ? `${c.name} (${c.company})` : c.name,
    })),
  ]

  return (
    <PageLayout
      title="New Asset"
      subtitle="Add a new device to inventory"
      breadcrumbs={[
        { label: 'Inventory', href: '/inventory' },
        { label: 'New Asset' },
      ]}
      isLoading={isLoadingData}
    >
      <FormProvider {...methods}>
        <form onSubmit={handleSubmit(onSubmit)} className="max-w-4xl">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Image Upload - Left Column */}
            <div className="lg:col-span-1">
              <Card className="sticky top-8">
                <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    Asset Image
                  </h3>
                </div>
                <div className="p-4">
                  {/* Image Preview */}
                  <div
                    className={cn(
                      'relative w-full aspect-square rounded-lg border-2 border-dashed overflow-hidden',
                      imagePreview
                        ? 'border-[#0176D3]'
                        : 'border-gray-300 dark:border-gray-600'
                    )}
                  >
                    {imagePreview ? (
                      <>
                        <img
                          src={imagePreview}
                          alt="Asset preview"
                          className="w-full h-full object-cover"
                        />
                        <button
                          type="button"
                          onClick={removeImage}
                          className="absolute top-2 right-2 p-1 bg-red-500 text-white rounded-full hover:bg-red-600"
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
                      </>
                    ) : (
                      <label className="flex flex-col items-center justify-center w-full h-full cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                        <svg
                          className="w-12 h-12 text-gray-400 mb-2"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                          />
                        </svg>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          Click to upload image
                        </p>
                        <p className="text-xs text-gray-400 mt-1">
                          PNG, JPG, GIF, WebP (max 5MB)
                        </p>
                        <input
                          ref={fileInputRef}
                          type="file"
                          className="hidden"
                          accept="image/png,image/jpeg,image/gif,image/webp"
                          onChange={handleImageChange}
                        />
                      </label>
                    )}
                  </div>

                  {/* Auto-generate tag checkbox */}
                  <div className="mt-4 flex items-center">
                    <input
                      type="checkbox"
                      id="auto_generate_tag"
                      checked={autoGenerateTag}
                      onChange={(e) => {
                        setAutoGenerateTag(e.target.checked)
                        if (e.target.checked) {
                          setValue('asset_tag', '')
                        }
                      }}
                      className="h-4 w-4 text-[#0176D3] focus:ring-[#0176D3] border-gray-300 rounded"
                    />
                    <label
                      htmlFor="auto_generate_tag"
                      className="ml-2 text-sm text-gray-700 dark:text-gray-300"
                    >
                      Auto-generate Asset Tag
                    </label>
                  </div>
                </div>
              </Card>
            </div>

            {/* Main Form - Right Column */}
            <div className="lg:col-span-2">
              <Card>
                <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    Asset Details
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                    Fill in the device information below
                  </p>
                </div>

                <div className="p-6 space-y-6">
                  {/* Basic Info Section */}
                  <FormSection title="Basic Information">
                    {/* Name */}
                    <div>
                      <FormLabel required>Name</FormLabel>
                      <Input
                        {...register('name')}
                        placeholder="e.g., MacBook Pro 14-inch"
                        error={errors.name?.message}
                      />
                    </div>

                    {/* Asset Tag & Serial Number Row */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <FormLabel>Asset Tag</FormLabel>
                        <Input
                          {...register('asset_tag')}
                          placeholder={
                            autoGenerateTag
                              ? 'Will be auto-generated'
                              : 'e.g., TL-12345'
                          }
                          disabled={autoGenerateTag}
                          error={errors.asset_tag?.message}
                        />
                      </div>
                      <div>
                        <FormLabel>Serial Number</FormLabel>
                        <Input
                          {...register('serial_number')}
                          placeholder="e.g., C02X1234ABCD"
                          error={errors.serial_number?.message}
                        />
                      </div>
                    </div>

                    {/* Model & Manufacturer Row */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <FormLabel>Model</FormLabel>
                        <Input
                          {...register('model')}
                          placeholder="e.g., MacBook Pro A2338"
                          error={errors.model?.message}
                        />
                      </div>
                      <div>
                        <FormLabel>Manufacturer</FormLabel>
                        <Controller
                          name="manufacturer"
                          control={control}
                          render={({ field }) => (
                            <Select
                              {...field}
                              placeholder="Select manufacturer..."
                              options={[
                                { value: '', label: 'Select manufacturer...' },
                                ...MANUFACTURER_OPTIONS,
                              ]}
                              error={errors.manufacturer?.message}
                            />
                          )}
                        />
                      </div>
                    </div>

                    {/* Asset Type & Status Row */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <FormLabel>Asset Type</FormLabel>
                        <Controller
                          name="asset_type"
                          control={control}
                          render={({ field }) => (
                            <Select
                              {...field}
                              placeholder="Select type..."
                              options={[
                                { value: '', label: 'Select type...' },
                                ...ASSET_TYPE_OPTIONS,
                              ]}
                              error={errors.asset_type?.message}
                            />
                          )}
                        />
                      </div>
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
                    </div>

                    {/* Condition & Customer Row */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <FormLabel>Condition</FormLabel>
                        <Controller
                          name="condition"
                          control={control}
                          render={({ field }) => (
                            <Select
                              {...field}
                              options={[
                                { value: '', label: 'Select condition...' },
                                ...CONDITION_OPTIONS,
                              ]}
                              error={errors.condition?.message}
                            />
                          )}
                        />
                      </div>
                      <div>
                        <FormLabel>Customer</FormLabel>
                        <Controller
                          name="customer"
                          control={control}
                          render={({ field }) => (
                            <Select
                              {...field}
                              options={customerOptions}
                              error={errors.customer?.message}
                            />
                          )}
                        />
                      </div>
                    </div>
                  </FormSection>

                  {/* Specifications Section */}
                  <FormSection title="Specifications">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div>
                        <FormLabel>CPU</FormLabel>
                        <Input
                          {...register('cpu_type')}
                          placeholder="e.g., Apple M1 Pro"
                          error={errors.cpu_type?.message}
                        />
                      </div>
                      <div>
                        <FormLabel>Memory</FormLabel>
                        <Input
                          {...register('memory')}
                          placeholder="e.g., 16GB"
                          error={errors.memory?.message}
                        />
                      </div>
                      <div>
                        <FormLabel>Storage</FormLabel>
                        <Input
                          {...register('harddrive')}
                          placeholder="e.g., 512GB SSD"
                          error={errors.harddrive?.message}
                        />
                      </div>
                    </div>
                  </FormSection>

                  {/* Notes Section */}
                  <FormSection>
                    <div>
                      <FormLabel>Notes</FormLabel>
                      <TextArea
                        {...register('notes')}
                        placeholder="Add any additional notes about this asset..."
                        rows={4}
                        error={errors.notes?.message}
                      />
                    </div>
                  </FormSection>

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
                      Create Asset
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

export default CreateAssetPage
