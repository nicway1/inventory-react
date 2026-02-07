/**
 * AssetDetail Component
 *
 * Salesforce-style asset detail page matching Flask TrueLog design.
 * Features:
 * - Page header with asset image, tag, name, status badge, condition badge
 * - Action buttons: Edit, Checkout, Transfer, Archive, Delete
 * - Info cards: Basic Info, Specifications, Assignment, Purchase Info
 * - Tabs: History, Service Records, Attachments, Notes
 * - Quick actions sidebar
 * - Tab title integration
 */

import { useCallback, useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { Tab } from '@headlessui/react'
import {
  PencilIcon,
  ArrowLeftIcon,
  PrinterIcon,
  TrashIcon,
  ArrowRightOnRectangleIcon,
  ArrowLeftOnRectangleIcon,
  ComputerDesktopIcon,
  CpuChipIcon,
  MapPinIcon,
  CurrencyDollarIcon,
  ClockIcon,
  DocumentTextIcon,
  WrenchScrewdriverIcon,
  PaperClipIcon,
  ChatBubbleLeftRightIcon,
  TicketIcon,
  InformationCircleIcon,
  Cog6ToothIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils/cn'
import { PageLayout } from '@/components/templates/PageLayout'
import { Card, CardHeader } from '@/components/molecules/Card'
import { Badge } from '@/components/atoms/Badge'
import { Button } from '@/components/atoms/Button'
import { Modal } from '@/components/organisms/Modal'
import { ConfirmDialog, useConfirmDialog } from '@/components/organisms/ConfirmDialog'
import { EmptyState } from '@/components/organisms/EmptyState'
import { useUpdateTabTitle } from '@/components/organisms/TabSystem'
import { apiClient } from '@/services/api'

// =============================================================================
// Types
// =============================================================================

interface Asset {
  id: number
  asset_tag?: string
  name?: string
  serial_num?: string
  model?: string
  manufacturer?: string
  category?: string
  asset_type?: string
  status?: string
  condition?: string
  customer?: string
  country?: string
  location?: {
    id: number
    name: string
    country?: string
  }
  inventory?: string
  cpu_type?: string
  cpu_cores?: string
  memory?: string
  harddrive?: string
  gpu_cores?: string
  keyboard?: string
  charger?: string
  diag?: string
  notes?: string
  tech_notes?: string
  cost_price?: number
  po?: string
  receiving_date?: string
  erased?: string
  image_url?: string
  created_at?: string
  updated_at?: string
}

interface HistoryEntry {
  id: number
  action: string
  notes?: string
  created_at: string
  user?: {
    id: number
    username: string
  }
}

interface RelatedTicket {
  id: number
  ticket_number?: string
  subject?: string
  title?: string
  status?: { value: string }
  priority?: { value: string }
  created_at?: string
}

interface ServiceRecord {
  id: number
  type: string
  description: string
  performed_by?: string
  performed_at?: string
  cost?: number
}

interface Attachment {
  id: number
  filename: string
  file_type?: string
  file_size?: number
  uploaded_by?: string
  uploaded_at?: string
}

// =============================================================================
// Status Badge Mappings
// =============================================================================

const statusVariants: Record<string, 'success' | 'warning' | 'danger' | 'info' | 'neutral'> = {
  deployed: 'success',
  'in stock': 'info',
  instock: 'info',
  available: 'info',
  'ready to deploy': 'info',
  readytodeploy: 'info',
  shipped: 'warning',
  repair: 'danger',
  maintenance: 'warning',
  archived: 'neutral',
  disposed: 'neutral',
  retired: 'neutral',
  lost: 'danger',
}

const conditionVariants: Record<string, 'success' | 'warning' | 'danger' | 'info' | 'neutral'> = {
  new: 'success',
  excellent: 'success',
  good: 'info',
  fair: 'warning',
  poor: 'danger',
  broken: 'danger',
}

function getStatusVariant(status?: string): 'success' | 'warning' | 'danger' | 'info' | 'neutral' {
  if (!status) return 'neutral'
  const normalized = status.toLowerCase().replace(/[^a-z]/g, '')
  return statusVariants[normalized] || statusVariants[status.toLowerCase()] || 'neutral'
}

function getConditionVariant(condition?: string): 'success' | 'warning' | 'danger' | 'info' | 'neutral' {
  if (!condition) return 'neutral'
  return conditionVariants[condition.toLowerCase()] || 'neutral'
}

// =============================================================================
// Sub-components
// =============================================================================

interface DetailFieldProps {
  label: string
  value?: string | number | null
  children?: React.ReactNode
}

function DetailField({ label, value, children }: DetailFieldProps) {
  return (
    <div className="py-2">
      <div className="text-xs font-semibold uppercase tracking-wide text-[#706E6B] dark:text-gray-400 mb-1">
        {label}
      </div>
      <div className="text-sm text-gray-900 dark:text-gray-100">
        {children || value || '-'}
      </div>
    </div>
  )
}

interface StatCardProps {
  icon: React.ElementType
  value: number
  label: string
  color: 'blue' | 'green' | 'orange' | 'purple'
}

function StatCard({ icon: Icon, value, label, color }: StatCardProps) {
  const colorClasses = {
    blue: {
      bg: 'bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/30 dark:to-blue-800/30',
      icon: 'text-[#0176D3]',
      value: 'text-[#0176D3]',
    },
    green: {
      bg: 'bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/30 dark:to-green-800/30',
      icon: 'text-[#2E844A]',
      value: 'text-[#2E844A]',
    },
    orange: {
      bg: 'bg-gradient-to-br from-orange-50 to-orange-100 dark:from-orange-900/30 dark:to-orange-800/30',
      icon: 'text-[#D97706]',
      value: 'text-[#D97706]',
    },
    purple: {
      bg: 'bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-900/30 dark:to-purple-800/30',
      icon: 'text-[#7C3AED]',
      value: 'text-[#7C3AED]',
    },
  }

  const colors = colorClasses[color]

  return (
    <div className="bg-white dark:bg-gray-800 border border-[#DDDBDA] dark:border-gray-700 rounded-lg p-4 text-center transition-all hover:shadow-md hover:-translate-y-0.5">
      <div className={cn('w-12 h-12 rounded-xl flex items-center justify-center mx-auto mb-3', colors.bg)}>
        <Icon className={cn('w-6 h-6', colors.icon)} />
      </div>
      <div className={cn('text-2xl font-bold', colors.value)}>{value}</div>
      <div className="text-xs font-semibold uppercase tracking-wide text-[#706E6B] dark:text-gray-400 mt-1">
        {label}
      </div>
    </div>
  )
}

interface TimelineItemProps {
  entry: HistoryEntry
  isLast: boolean
}

function TimelineItem({ entry, isLast }: TimelineItemProps) {
  return (
    <div className="flex gap-4 pb-4 relative">
      {!isLast && (
        <div className="absolute left-2 top-6 bottom-0 w-0.5 bg-[#DDDBDA] dark:bg-gray-700" />
      )}
      <div className="w-4 h-4 rounded-full bg-[#0176D3] flex-shrink-0 mt-1" />
      <div className="flex-1">
        <div className="text-sm font-semibold text-gray-900 dark:text-white">
          {entry.action}
        </div>
        <div className="text-xs text-[#706E6B] dark:text-gray-400 mt-1">
          {entry.created_at ? new Date(entry.created_at).toLocaleString() : ''}
          {entry.user && ` by ${entry.user.username}`}
        </div>
        {entry.notes && (
          <div className="text-xs text-[#706E6B] dark:text-gray-400 mt-2 bg-gray-100 dark:bg-gray-800 p-2 rounded">
            {entry.notes}
          </div>
        )}
      </div>
    </div>
  )
}

// =============================================================================
// Quick Actions Sidebar
// =============================================================================

interface QuickActionsSidebarProps {
  asset: Asset
  onCheckout: () => void
  onCheckin: () => void
  onCreateTicket: () => void
  onPrintLabel: () => void
  isCheckedOut: boolean
}

function QuickActionsSidebar({
  onCheckout,
  onCheckin,
  onCreateTicket,
  onPrintLabel,
  isCheckedOut,
}: QuickActionsSidebarProps) {
  return (
    <Card padding="none" className="sticky top-6">
      <CardHeader>Quick Actions</CardHeader>
      <div className="p-4 space-y-3">
        {isCheckedOut ? (
          <Button
            variant="primary"
            fullWidth
            leftIcon={<ArrowLeftOnRectangleIcon className="w-4 h-4" />}
            onClick={onCheckin}
          >
            Check In
          </Button>
        ) : (
          <Button
            variant="primary"
            fullWidth
            leftIcon={<ArrowRightOnRectangleIcon className="w-4 h-4" />}
            onClick={onCheckout}
          >
            Checkout to Customer
          </Button>
        )}
        <Button
          variant="secondary"
          fullWidth
          leftIcon={<TicketIcon className="w-4 h-4" />}
          onClick={onCreateTicket}
        >
          Create Ticket
        </Button>
        <Button
          variant="ghost"
          fullWidth
          leftIcon={<PrinterIcon className="w-4 h-4" />}
          onClick={onPrintLabel}
        >
          Print Label
        </Button>
      </div>
    </Card>
  )
}

// =============================================================================
// Main Component
// =============================================================================

export function AssetDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const updateTabTitle = useUpdateTabTitle()
  const { isOpen, title, description, variant, confirmText, cancelText, onConfirm, onClose, confirmDelete } =
    useConfirmDialog()

  // State
  const [asset, setAsset] = useState<Asset | null>(null)
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const [relatedTickets, setRelatedTickets] = useState<RelatedTicket[]>([])
  const [serviceRecords, setServiceRecords] = useState<ServiceRecord[]>([])
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isCheckoutModalOpen, setIsCheckoutModalOpen] = useState(false)
  const [isCheckinModalOpen, setIsCheckinModalOpen] = useState(false)
  const [selectedTab, setSelectedTab] = useState(0)

  // Fetch asset data
  const fetchAsset = useCallback(async () => {
    if (!id) return

    try {
      setIsLoading(true)
      setError(null)

      const response = await apiClient.get(`/v2/assets/${id}`)
      const data = response.data

      setAsset(data.asset || data)
      setHistory(data.history || [])
      setRelatedTickets(data.related_tickets || [])
      setServiceRecords(data.service_records || [])
      setAttachments(data.attachments || [])

      // Update tab title to asset tag
      const assetTag = data.asset?.asset_tag || data.asset_tag || `Asset #${id}`
      updateTabTitle(assetTag)
    } catch (err: unknown) {
      console.error('Error fetching asset:', err)
      const errorMessage = err instanceof Error ? err.message : 'Failed to load asset details'
      setError(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }, [id, updateTabTitle])

  useEffect(() => {
    fetchAsset()
  }, [fetchAsset])

  // Handlers
  const handleEdit = useCallback(() => {
    navigate(`/inventory/${id}/edit`)
  }, [navigate, id])

  const handleBack = useCallback(() => {
    navigate('/inventory')
  }, [navigate])

  const handleDelete = useCallback(() => {
    confirmDelete({
      title: 'Delete Asset',
      description: `Are you sure you want to delete "${asset?.asset_tag || asset?.serial_num || asset?.name}"? This action cannot be undone. All history and transactions for this asset will also be deleted.`,
      onConfirm: async () => {
        try {
          await apiClient.delete(`/v2/assets/${id}`)
          navigate('/inventory')
        } catch (err: unknown) {
          console.error('Error deleting asset:', err)
          const errorMessage = err instanceof Error ? err.message : 'Failed to delete asset'
          throw new Error(errorMessage)
        }
      },
    })
  }, [asset, id, navigate, confirmDelete])

  const handleCheckout = useCallback(() => {
    setIsCheckoutModalOpen(true)
  }, [])

  const handleCheckin = useCallback(() => {
    setIsCheckinModalOpen(true)
  }, [])

  const handleCheckoutSubmit = useCallback(async (customerId: string) => {
    try {
      await apiClient.post(`/v2/assets/${id}/checkout`, { customer_id: customerId })
      setIsCheckoutModalOpen(false)
      fetchAsset()
    } catch (err: unknown) {
      console.error('Error checking out asset:', err)
    }
  }, [id, fetchAsset])

  const handleCheckinSubmit = useCallback(async () => {
    try {
      await apiClient.post(`/v2/assets/${id}/checkin`)
      setIsCheckinModalOpen(false)
      fetchAsset()
    } catch (err: unknown) {
      console.error('Error checking in asset:', err)
    }
  }, [id, fetchAsset])

  const handleCreateTicket = useCallback(() => {
    navigate(`/tickets/new?asset_id=${id}`)
  }, [navigate, id])

  const handlePrintLabel = useCallback(() => {
    window.open(`/api/assets/${id}/label`, '_blank')
  }, [id])

  // Check if asset is checked out
  const isCheckedOut = asset?.status?.toLowerCase() === 'deployed' && !!asset?.customer

  // Get product image URL
  const getProductImage = () => {
    if (asset?.image_url) return asset.image_url

    const model = (asset?.model || '').toLowerCase()
    const name = (asset?.name || '').toLowerCase()
    const mfg = (asset?.manufacturer || '').toLowerCase()

    if (model.includes('macbook') || name.includes('macbook') || mfg === 'apple') {
      return '/static/images/products/macbook.png'
    }
    if (model.includes('thinkpad') || name.includes('thinkpad') || mfg === 'lenovo') {
      return '/static/images/products/laptop_lenovo.png'
    }
    if (model.includes('latitude') || model.includes('xps') || mfg === 'dell') {
      return '/static/images/products/laptop_dell.png'
    }
    if (model.includes('elitebook') || model.includes('probook') || mfg === 'hp') {
      return '/static/images/products/laptop_hp.png'
    }
    if (model.includes('surface') || mfg === 'microsoft') {
      return '/static/images/products/laptop_surface.png'
    }
    if (model.includes('iphone') || name.includes('iphone')) {
      return '/static/images/products/iphone.png'
    }
    if (model.includes('ipad') || name.includes('ipad')) {
      return '/static/images/products/ipad.png'
    }

    return null
  }

  const productImage = getProductImage()

  // Loading state
  if (isLoading) {
    return (
      <PageLayout isLoading>
        <div />
      </PageLayout>
    )
  }

  // Error state
  if (error || !asset) {
    return (
      <PageLayout>
        <EmptyState
          preset="error"
          title="Asset Not Found"
          description={error || 'The asset you are looking for could not be found.'}
          action={{
            label: 'Back to Inventory',
            onClick: handleBack,
          }}
        />
      </PageLayout>
    )
  }

  return (
    <PageLayout fullWidth>
      {/* Page Header */}
      <div className="bg-white dark:bg-gray-900 border-b border-[#DDDBDA] dark:border-gray-700">
        {/* Breadcrumb */}
        <div className="px-6 py-3">
          <nav className="text-xs text-[#706E6B] dark:text-gray-400">
            <Link to="/inventory" className="text-[#0176D3] hover:underline">
              Inventory
            </Link>
            <span className="mx-2">/</span>
            <span>Asset</span>
          </nav>
        </div>

        {/* Header Content */}
        <div className="px-6 pb-4 flex items-start justify-between gap-6">
          <div className="flex items-center gap-4">
            {/* Record Icon */}
            <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-[#0176D3] to-[#1B96FF] flex items-center justify-center text-white flex-shrink-0">
              <ComputerDesktopIcon className="w-6 h-6" />
            </div>

            {/* Title and Subtitle */}
            <div>
              <h1 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
                {asset.asset_tag || asset.name || 'Unknown Asset'}
                {asset.status && (
                  <Badge variant={getStatusVariant(asset.status)} size="sm" dot>
                    {asset.status}
                  </Badge>
                )}
                {asset.condition && (
                  <Badge variant={getConditionVariant(asset.condition)} size="sm">
                    {asset.condition}
                  </Badge>
                )}
              </h1>
              <p className="text-sm text-[#706E6B] dark:text-gray-400 mt-0.5">
                {asset.serial_num || 'No Serial Number'}
                {asset.model && ` | ${asset.model}`}
              </p>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2 flex-shrink-0">
            <Button variant="primary" size="sm" leftIcon={<PencilIcon className="w-4 h-4" />} onClick={handleEdit}>
              Edit
            </Button>
            <Button variant="ghost" size="sm" leftIcon={<ArrowLeftIcon className="w-4 h-4" />} onClick={handleBack}>
              Back to List
            </Button>
            {asset.serial_num && (
              <Button variant="ghost" size="sm" leftIcon={<PrinterIcon className="w-4 h-4" />} onClick={handlePrintLabel}>
                Print Label
              </Button>
            )}
            <Button variant="danger" size="sm" leftIcon={<TrashIcon className="w-4 h-4" />} onClick={handleDelete}>
              Delete
            </Button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-[1400px] mx-auto px-6 py-6">
        {/* Highlights Panel */}
        <div className="bg-white dark:bg-gray-900 border border-[#DDDBDA] dark:border-gray-700 rounded-lg mb-6 overflow-hidden">
          {/* Header */}
          <div className="bg-gradient-to-r from-[#0176D3] to-[#014486] px-5 py-3 text-white">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <ComputerDesktopIcon className="w-4 h-4" />
              Asset Highlights
            </div>
          </div>

          {/* Content */}
          <div className="p-6 flex gap-6 items-start">
            {/* Product Image Section */}
            <div className="relative flex-shrink-0 p-4 bg-gradient-to-br from-gray-100 to-blue-50 dark:from-gray-800 dark:to-gray-700 rounded-lg">
              {(asset.category || asset.asset_type) && (
                <span className="absolute top-2 left-2 px-2 py-0.5 bg-[#0176D3] text-white text-[10px] font-semibold uppercase tracking-wide rounded">
                  {asset.category || asset.asset_type}
                </span>
              )}
              {productImage ? (
                <img
                  src={productImage}
                  alt={asset.name || asset.model || 'Asset'}
                  className="w-44 h-44 object-contain rounded-lg bg-white border border-[#DDDBDA]"
                  onError={(e) => {
                    e.currentTarget.style.display = 'none'
                    const sibling = e.currentTarget.nextElementSibling
                    if (sibling) sibling.classList.remove('hidden')
                  }}
                />
              ) : null}
              <div
                className={cn(
                  'w-44 h-44 flex items-center justify-center bg-white border border-[#DDDBDA] rounded-lg text-[#0176D3]',
                  productImage && 'hidden'
                )}
              >
                <ComputerDesktopIcon className="w-16 h-16" />
              </div>
            </div>

            {/* Stats Section */}
            <div className="flex-1">
              <div className="grid grid-cols-3 gap-4">
                <StatCard
                  icon={DocumentTextIcon}
                  value={relatedTickets.length}
                  label="Related Cases"
                  color="blue"
                />
                <StatCard
                  icon={ClockIcon}
                  value={history.length}
                  label="History Entries"
                  color="green"
                />
                <StatCard
                  icon={WrenchScrewdriverIcon}
                  value={serviceRecords.length}
                  label="Service Records"
                  color="orange"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - 2/3 width */}
          <div className="lg:col-span-2 space-y-6">
            {/* Asset Information Card */}
            <Card padding="none">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <InformationCircleIcon className="w-4 h-4" />
                  Asset Information
                </div>
              </CardHeader>
              <div className="p-5">
                <div className="grid grid-cols-2 gap-x-8 gap-y-2">
                  <DetailField label="Asset Tag" value={asset.asset_tag} />
                  <DetailField label="Serial Number" value={asset.serial_num} />
                  <DetailField label="Name" value={asset.name} />
                  <DetailField label="Model" value={asset.model} />
                  <DetailField label="Manufacturer" value={asset.manufacturer} />
                  <DetailField label="Category / Type" value={asset.asset_type || asset.category} />
                  <DetailField label="Status">
                    {asset.status && (
                      <Badge variant={getStatusVariant(asset.status)} size="sm" dot>
                        {asset.status}
                      </Badge>
                    )}
                  </DetailField>
                  <DetailField label="Condition" value={asset.condition} />
                </div>
              </div>
            </Card>

            {/* Location & Assignment Card */}
            <Card padding="none">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <MapPinIcon className="w-4 h-4" />
                  Location & Assignment
                </div>
              </CardHeader>
              <div className="p-5">
                <div className="grid grid-cols-2 gap-x-8 gap-y-2">
                  <DetailField label="Customer" value={asset.customer} />
                  <DetailField label="Country" value={asset.country} />
                  <DetailField label="Location" value={asset.location?.name} />
                  <DetailField label="Inventory" value={asset.inventory} />
                </div>
              </div>
            </Card>

            {/* Specifications Card */}
            <Card padding="none">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <CpuChipIcon className="w-4 h-4" />
                  Specifications
                </div>
              </CardHeader>
              <div className="p-5">
                <div className="grid grid-cols-2 gap-x-8 gap-y-2">
                  <DetailField label="CPU Type" value={asset.cpu_type} />
                  <DetailField label="CPU Cores" value={asset.cpu_cores} />
                  <DetailField label="Memory" value={asset.memory} />
                  <DetailField label="Hard Drive" value={asset.harddrive} />
                  <DetailField label="GPU Cores" value={asset.gpu_cores} />
                  <DetailField label="Keyboard" value={asset.keyboard} />
                  <DetailField label="Charger" value={asset.charger} />
                  <DetailField label="Diagnostics" value={asset.diag} />
                </div>
              </div>
            </Card>

            {/* Related Cases Table */}
            <Card padding="none">
              <div className="flex items-center justify-between px-5 py-3 bg-gray-100 dark:bg-gray-800 border-b border-[#DDDBDA] dark:border-gray-700">
                <span className="text-sm font-bold text-gray-900 dark:text-white flex items-center gap-2">
                  Related Cases
                  <span className="px-2 py-0.5 bg-[#0176D3] text-white text-xs font-semibold rounded-full">
                    {relatedTickets.length}
                  </span>
                </span>
              </div>
              {relatedTickets.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="bg-gray-100 dark:bg-gray-800 border-b border-[#DDDBDA] dark:border-gray-700">
                        <th className="text-left px-4 py-3 text-xs font-semibold uppercase text-[#706E6B] dark:text-gray-400">
                          Case Number
                        </th>
                        <th className="text-left px-4 py-3 text-xs font-semibold uppercase text-[#706E6B] dark:text-gray-400">
                          Subject
                        </th>
                        <th className="text-left px-4 py-3 text-xs font-semibold uppercase text-[#706E6B] dark:text-gray-400">
                          Status
                        </th>
                        <th className="text-left px-4 py-3 text-xs font-semibold uppercase text-[#706E6B] dark:text-gray-400">
                          Priority
                        </th>
                        <th className="text-left px-4 py-3 text-xs font-semibold uppercase text-[#706E6B] dark:text-gray-400">
                          Created
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {relatedTickets.map((ticket) => (
                        <tr
                          key={ticket.id}
                          className="border-b border-[#DDDBDA] dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800/50"
                        >
                          <td className="px-4 py-3 text-sm">
                            <Link to={`/tickets/${ticket.id}`} className="text-[#0176D3] hover:underline">
                              {ticket.ticket_number || ticket.id}
                            </Link>
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-900 dark:text-gray-100">
                            {ticket.subject || ticket.title || '-'}
                          </td>
                          <td className="px-4 py-3">
                            <Badge variant={getStatusVariant(ticket.status?.value)} size="sm">
                              {ticket.status?.value || 'Open'}
                            </Badge>
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-900 dark:text-gray-100">
                            {ticket.priority?.value || '-'}
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                            {ticket.created_at ? new Date(ticket.created_at).toLocaleDateString() : '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="py-8 text-center text-sm text-[#706E6B] dark:text-gray-400">
                  <DocumentTextIcon className="w-10 h-10 mx-auto mb-2 opacity-50" />
                  <p>No related cases found for this asset</p>
                </div>
              )}
            </Card>

            {/* Tabs Section */}
            <Card padding="none">
              <Tab.Group selectedIndex={selectedTab} onChange={setSelectedTab}>
                <Tab.List className="flex border-b border-[#DDDBDA] dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
                  <Tab
                    className={({ selected }) =>
                      cn(
                        'px-4 py-3 text-sm font-medium focus:outline-none',
                        selected
                          ? 'text-[#0176D3] border-b-2 border-[#0176D3] bg-white dark:bg-gray-900'
                          : 'text-[#706E6B] dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                      )
                    }
                  >
                    <div className="flex items-center gap-2">
                      <ClockIcon className="w-4 h-4" />
                      History
                    </div>
                  </Tab>
                  <Tab
                    className={({ selected }) =>
                      cn(
                        'px-4 py-3 text-sm font-medium focus:outline-none',
                        selected
                          ? 'text-[#0176D3] border-b-2 border-[#0176D3] bg-white dark:bg-gray-900'
                          : 'text-[#706E6B] dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                      )
                    }
                  >
                    <div className="flex items-center gap-2">
                      <WrenchScrewdriverIcon className="w-4 h-4" />
                      Service Records
                    </div>
                  </Tab>
                  <Tab
                    className={({ selected }) =>
                      cn(
                        'px-4 py-3 text-sm font-medium focus:outline-none',
                        selected
                          ? 'text-[#0176D3] border-b-2 border-[#0176D3] bg-white dark:bg-gray-900'
                          : 'text-[#706E6B] dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                      )
                    }
                  >
                    <div className="flex items-center gap-2">
                      <PaperClipIcon className="w-4 h-4" />
                      Attachments
                    </div>
                  </Tab>
                  <Tab
                    className={({ selected }) =>
                      cn(
                        'px-4 py-3 text-sm font-medium focus:outline-none',
                        selected
                          ? 'text-[#0176D3] border-b-2 border-[#0176D3] bg-white dark:bg-gray-900'
                          : 'text-[#706E6B] dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                      )
                    }
                  >
                    <div className="flex items-center gap-2">
                      <ChatBubbleLeftRightIcon className="w-4 h-4" />
                      Notes
                    </div>
                  </Tab>
                </Tab.List>

                <Tab.Panels className="p-5">
                  {/* History Tab */}
                  <Tab.Panel>
                    {history.length > 0 ? (
                      <div className="space-y-1">
                        {history.map((entry, index) => (
                          <TimelineItem key={entry.id} entry={entry} isLast={index === history.length - 1} />
                        ))}
                      </div>
                    ) : (
                      <div className="py-8 text-center text-sm text-[#706E6B] dark:text-gray-400">
                        <ClockIcon className="w-10 h-10 mx-auto mb-2 opacity-50" />
                        <p>No activity recorded</p>
                      </div>
                    )}
                  </Tab.Panel>

                  {/* Service Records Tab */}
                  <Tab.Panel>
                    {serviceRecords.length > 0 ? (
                      <div className="space-y-3">
                        {serviceRecords.map((record) => (
                          <div
                            key={record.id}
                            className="p-4 border border-[#DDDBDA] dark:border-gray-700 rounded-lg"
                          >
                            <div className="flex items-center justify-between mb-2">
                              <span className="font-medium text-gray-900 dark:text-white">{record.type}</span>
                              {record.cost && (
                                <span className="text-sm text-[#0176D3]">
                                  ${record.cost.toLocaleString()}
                                </span>
                              )}
                            </div>
                            <p className="text-sm text-gray-600 dark:text-gray-400">{record.description}</p>
                            <div className="text-xs text-[#706E6B] dark:text-gray-500 mt-2">
                              {record.performed_at && new Date(record.performed_at).toLocaleDateString()}
                              {record.performed_by && ` by ${record.performed_by}`}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="py-8 text-center text-sm text-[#706E6B] dark:text-gray-400">
                        <WrenchScrewdriverIcon className="w-10 h-10 mx-auto mb-2 opacity-50" />
                        <p>No service records</p>
                      </div>
                    )}
                  </Tab.Panel>

                  {/* Attachments Tab */}
                  <Tab.Panel>
                    {attachments.length > 0 ? (
                      <div className="space-y-2">
                        {attachments.map((attachment) => (
                          <div
                            key={attachment.id}
                            className="flex items-center justify-between p-3 border border-[#DDDBDA] dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50"
                          >
                            <div className="flex items-center gap-3">
                              <PaperClipIcon className="w-5 h-5 text-[#706E6B]" />
                              <div>
                                <p className="text-sm font-medium text-gray-900 dark:text-white">
                                  {attachment.filename}
                                </p>
                                <p className="text-xs text-[#706E6B] dark:text-gray-400">
                                  {attachment.file_size && `${Math.round(attachment.file_size / 1024)} KB`}
                                  {attachment.uploaded_at && ` - ${new Date(attachment.uploaded_at).toLocaleDateString()}`}
                                </p>
                              </div>
                            </div>
                            <Button variant="ghost" size="sm">
                              Download
                            </Button>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="py-8 text-center text-sm text-[#706E6B] dark:text-gray-400">
                        <PaperClipIcon className="w-10 h-10 mx-auto mb-2 opacity-50" />
                        <p>No attachments</p>
                      </div>
                    )}
                  </Tab.Panel>

                  {/* Notes Tab */}
                  <Tab.Panel>
                    <div className="space-y-4">
                      <div>
                        <div className="text-xs font-semibold uppercase tracking-wide text-[#706E6B] dark:text-gray-400 mb-2">
                          General Notes
                        </div>
                        <div className="text-sm text-gray-900 dark:text-gray-100 bg-gray-50 dark:bg-gray-800 p-3 rounded-lg min-h-[60px]">
                          {asset.notes || 'No notes'}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs font-semibold uppercase tracking-wide text-[#706E6B] dark:text-gray-400 mb-2">
                          Technical Notes
                        </div>
                        <div className="text-sm text-gray-900 dark:text-gray-100 bg-gray-50 dark:bg-gray-800 p-3 rounded-lg min-h-[60px]">
                          {asset.tech_notes || 'No technical notes'}
                        </div>
                      </div>
                    </div>
                  </Tab.Panel>
                </Tab.Panels>
              </Tab.Group>
            </Card>
          </div>

          {/* Right Column - 1/3 width */}
          <div className="space-y-6">
            {/* Quick Actions */}
            <QuickActionsSidebar
              asset={asset}
              onCheckout={handleCheckout}
              onCheckin={handleCheckin}
              onCreateTicket={handleCreateTicket}
              onPrintLabel={handlePrintLabel}
              isCheckedOut={isCheckedOut}
            />

            {/* Notes Card */}
            <Card padding="none">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <DocumentTextIcon className="w-4 h-4" />
                  Notes
                </div>
              </CardHeader>
              <div className="p-5">
                <DetailField label="General Notes" value={asset.notes} />
                <DetailField label="Technical Notes" value={asset.tech_notes} />
              </div>
            </Card>

            {/* Purchase Information Card */}
            <Card padding="none">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <CurrencyDollarIcon className="w-4 h-4" />
                  Purchase Information
                </div>
              </CardHeader>
              <div className="p-5">
                <DetailField
                  label="Cost Price"
                  value={asset.cost_price ? `$${asset.cost_price.toLocaleString(undefined, { minimumFractionDigits: 2 })}` : undefined}
                />
                <DetailField label="PO Number" value={asset.po} />
                <DetailField
                  label="Receiving Date"
                  value={asset.receiving_date ? new Date(asset.receiving_date).toLocaleDateString() : undefined}
                />
                <DetailField label="Erased" value={asset.erased} />
              </div>
            </Card>

            {/* Activity Timeline Card */}
            <Card padding="none">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <ClockIcon className="w-4 h-4" />
                  Recent Activity
                </div>
              </CardHeader>
              <div className="p-5">
                {history.slice(0, 5).length > 0 ? (
                  <div className="space-y-1">
                    {history.slice(0, 5).map((entry, index) => (
                      <TimelineItem key={entry.id} entry={entry} isLast={index === Math.min(history.length, 5) - 1} />
                    ))}
                  </div>
                ) : (
                  <div className="py-4 text-center text-sm text-[#706E6B] dark:text-gray-400">
                    No activity recorded
                  </div>
                )}
              </div>
            </Card>

            {/* System Information Card */}
            <Card padding="none">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Cog6ToothIcon className="w-4 h-4" />
                  System Information
                </div>
              </CardHeader>
              <div className="p-5">
                <DetailField label="Asset ID" value={asset.id} />
                <DetailField
                  label="Created"
                  value={asset.created_at ? new Date(asset.created_at).toLocaleString() : undefined}
                />
                <DetailField
                  label="Last Updated"
                  value={asset.updated_at ? new Date(asset.updated_at).toLocaleString() : undefined}
                />
              </div>
            </Card>
          </div>
        </div>
      </div>

      {/* Checkout Modal */}
      <Modal
        isOpen={isCheckoutModalOpen}
        onClose={() => setIsCheckoutModalOpen(false)}
        title="Checkout Asset"
        size="md"
        footer={
          <>
            <Button variant="ghost" onClick={() => setIsCheckoutModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" onClick={() => handleCheckoutSubmit('1')}>
              Checkout
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Select a customer to checkout this asset to:
          </p>
          {/* TODO: Add customer selection dropdown */}
          <div className="text-sm text-[#706E6B]">
            Customer selection will be implemented here.
          </div>
        </div>
      </Modal>

      {/* Checkin Modal */}
      <Modal
        isOpen={isCheckinModalOpen}
        onClose={() => setIsCheckinModalOpen(false)}
        title="Check In Asset"
        size="md"
        footer={
          <>
            <Button variant="ghost" onClick={() => setIsCheckinModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" onClick={handleCheckinSubmit}>
              Check In
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Are you sure you want to check in this asset? It will be marked as available.
          </p>
          <div className="p-4 bg-gray-100 dark:bg-gray-800 rounded-lg">
            <div className="text-sm font-medium text-gray-900 dark:text-white">
              {asset.asset_tag || asset.name}
            </div>
            <div className="text-xs text-[#706E6B] dark:text-gray-400 mt-1">
              Currently assigned to: {asset.customer || 'Unknown'}
            </div>
          </div>
        </div>
      </Modal>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        isOpen={isOpen}
        onClose={onClose}
        onConfirm={onConfirm}
        title={title}
        description={description}
        variant={variant}
        confirmText={confirmText}
        cancelText={cancelText}
      />
    </PageLayout>
  )
}

export default AssetDetail
