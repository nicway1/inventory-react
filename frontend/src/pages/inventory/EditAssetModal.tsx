/**
 * EditAssetModal Component
 *
 * Modal for editing an existing asset with form validation.
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { useForm, FormProvider, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Modal } from '@/components/organisms/Modal'
import { Button, Input, Select, TextArea } from '@/components/atoms'
import { FormLabel, FormSection } from '@/components/molecules/FormGroup'
import { useToast } from '@/hooks'
import { cn } from '@/utils/cn'
import { getAsset, updateAsset, uploadAssetImage } from '@/services/assets.service'
import { getCustomers } from '@/services/tickets.service'
import type { Asset, Customer } from '@/types'
import {
  STATUS_OPTIONS,
  CONDITION_OPTIONS,
  ASSET_TYPE_OPTIONS,
  MANUFACTURER_OPTIONS,
} from '@/types/assets'

// Form validation schema
const editAssetSchema = z.object({
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
})

type EditAssetFormValues = z.infer<typeof editAssetSchema>

interface EditAssetModalProps {
  assetId: number | null
  isOpen: boolean
  onClose: () => void
  onSuccess?: (asset: Asset) => void
}

export function EditAssetModal({
  assetId,
  isOpen,
  onClose,
  onSuccess,
}: EditAssetModalProps) {
  const { success, error: showError } = useToast()
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Data states
  const [customers, setCustomers] = useState<Customer[]>([])
  const [isLoadingData, setIsLoadingData] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [asset, setAsset] = useState<Asset | null>(null)

  // Image state
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)

  // Initialize form
  const methods = useForm<EditAssetFormValues>({
    resolver: zodResolver(editAssetSchema),
    defaultValues: {
      name: '',
      asset_tag: '',
      serial_number: '',
      model: '',
      manufacturer: '',
      asset_type: '',
      status: 'IN_STOCK',
      condition: '',
      cpu_type: '',
      memory: '',
      harddrive: '',
      customer: '',
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
      if (!isOpen || !assetId) return

      setIsLoadingData(true)
      try {
        const [assetData, customersData] = await Promise.all([
          getAsset(assetId),
          getCustomers(),
        ])

        setAsset(assetData)
        setCustomers(customersData)

        // Set image preview if exists
        if (assetData.image_url) {
          setImagePreview(assetData.image_url)
        } else {
          setImagePreview(null)
        }

        // Reset form with asset data
        reset({
          name: assetData.name || '',
          asset_tag: assetData.asset_tag || '',
          serial_number: assetData.serial_number || '',
          model: assetData.model || '',
          manufacturer: assetData.manufacturer || '',
          asset_type: assetData.asset_type || '',
          status: assetData.status || 'IN_STOCK',
          condition: assetData.condition || '',
          cpu_type: assetData.cpu_type || '',
          memory: assetData.memory || '',
          harddrive: assetData.harddrive || '',
          customer: assetData.customer || '',
          notes: assetData.notes || '',
        })
      } catch (err) {
        showError('Failed to load asset data')
        console.error('Error loading asset data:', err)
        onClose()
      } finally {
        setIsLoadingData(false)
      }
    }

    loadData()
  }, [isOpen, assetId, reset, showError, onClose])

  // Handle image selection
  const handleImageChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0]
      if (file) {
        const validTypes = ['image/png', 'image/jpeg', 'image/gif', 'image/webp']
        if (!validTypes.includes(file.type)) {
          showError('Invalid file type. Please upload a PNG, JPG, GIF, or WebP image.')
          return
        }

        if (file.size > 5 * 1024 * 1024) {
          showError('File too large. Maximum size is 5MB.')
          return
        }

        setImageFile(file)

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

  // Handle form submission
  const onSubmit = async (data: EditAssetFormValues) => {
    if (!assetId) return

    setIsSubmitting(true)
    try {
      const payload = {
        name: data.name,
        asset_tag: data.asset_tag || undefined,
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

      const updatedAsset = await updateAsset(assetId, payload)

      // Upload new image if provided
      if (imageFile) {
        try {
          await uploadAssetImage(assetId, imageFile)
        } catch (uploadErr) {
          console.error('Failed to upload image:', uploadErr)
        }
      }

      success(
        `Asset ${updatedAsset.asset_tag || updatedAsset.serial_number} updated successfully`
      )
      onSuccess?.(updatedAsset)
      onClose()
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to update asset'
      showError(errorMessage)
      console.error('Error updating asset:', err)
    } finally {
      setIsSubmitting(false)
    }
  }

  // Customer options for select
  const customerOptions = [
    { value: '', label: 'No customer assigned' },
    ...customers.map((c) => ({
      value: c.name,
      label: c.company ? `${c.name} (${c.company})` : c.name,
    })),
  ]

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Edit Asset ${asset?.asset_tag || asset?.serial_number || `#${assetId}`}`}
      size="xl"
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
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            {/* Image Upload */}
            <div className="flex items-start gap-4">
              <div
                className={cn(
                  'relative w-24 h-24 flex-shrink-0 rounded-lg border-2 border-dashed overflow-hidden',
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
                      className="absolute top-1 right-1 p-0.5 bg-red-500 text-white rounded-full hover:bg-red-600"
                    >
                      <svg
                        className="w-3 h-3"
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
                  <label className="flex flex-col items-center justify-center w-full h-full cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800">
                    <svg
                      className="w-6 h-6 text-gray-400"
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
              <div className="flex-1">
                <FormLabel required>Name</FormLabel>
                <Input
                  {...register('name')}
                  placeholder="e.g., MacBook Pro 14-inch"
                  error={errors.name?.message}
                />
              </div>
            </div>

            {/* Asset Tag & Serial Number */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <FormLabel>Asset Tag</FormLabel>
                <Input
                  {...register('asset_tag')}
                  placeholder="e.g., TL-12345"
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

            {/* Model & Manufacturer */}
            <div className="grid grid-cols-2 gap-4">
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

            {/* Type & Status & Condition */}
            <div className="grid grid-cols-3 gap-4">
              <div>
                <FormLabel>Type</FormLabel>
                <Controller
                  name="asset_type"
                  control={control}
                  render={({ field }) => (
                    <Select
                      {...field}
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
            </div>

            {/* Specifications */}
            <FormSection title="Specifications">
              <div className="grid grid-cols-3 gap-4">
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

            {/* Customer */}
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

            {/* Notes */}
            <div>
              <FormLabel>Notes</FormLabel>
              <TextArea
                {...register('notes')}
                placeholder="Add any additional notes..."
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

export default EditAssetModal
