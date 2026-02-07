/**
 * CustomerDetailPage Component
 *
 * Customer detail page with tabs for assets, tickets, accessories, and history.
 * Matches Flask TrueLog view_customer_user.html design.
 */

import { useState, useCallback, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  PencilIcon,
  TrashIcon,
  ArrowLeftIcon,
  EnvelopeIcon,
  PhoneIcon,
  MapPinIcon,
  BuildingOfficeIcon,
  GlobeAltIcon,
  CalendarIcon,
  ClockIcon,
  ComputerDesktopIcon,
  TicketIcon,
  BoltIcon,
  ClipboardDocumentListIcon,
  CubeIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils/cn'
import { PageLayout } from '@/components/templates/PageLayout'
import { Button } from '@/components/atoms/Button'
import { Badge } from '@/components/atoms/Badge'
import { Card, CardHeader } from '@/components/molecules/Card'
import { DataTable, type ColumnDef } from '@/components/organisms/DataTable'
import { ConfirmDialog, useConfirmDialog } from '@/components/organisms/ConfirmDialog'
import { EmptyState } from '@/components/organisms/EmptyState'
import { Spinner } from '@/components/atoms/Spinner'
import {
  useCustomer,
  useDeleteCustomer,
  useCustomerTransactions,
} from '@/hooks/useCustomers'
import { useOpenTab, useUpdateTabTitle } from '@/components/organisms/TabSystem'
import type {
  CustomerAsset,
  CustomerAccessory,
  CustomerTicket,
  CustomerTransaction,
  Country,
} from '@/types/customer'
import { COUNTRY_COLORS } from '@/types/customer'
import { CustomerModal } from './CustomerModal'

// Tab definitions
type TabId = 'details' | 'assets' | 'tickets' | 'accessories' | 'transactions'

interface TabDefinition {
  id: TabId
  label: string
  icon: React.ElementType
  count?: number
}

export function CustomerDetailPage() {
  const { id } = useParams<{ id: string }>()
  const customerId = Number(id)
  const navigate = useNavigate()
  const openTab = useOpenTab()
  const updateTabTitle = useUpdateTabTitle()

  // State
  const [activeTab, setActiveTab] = useState<TabId>('details')
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)

  // Confirm dialog
  const confirmDialog = useConfirmDialog()

  // Fetch customer data
  const {
    data: customer,
    isLoading,
    isError,
    refetch,
  } = useCustomer(customerId)

  // Fetch transactions when tab is active
  const {
    data: transactions = [],
    isLoading: isLoadingTransactions,
  } = useCustomerTransactions(customerId, {
    enabled: activeTab === 'transactions',
  })

  // Delete mutation
  const deleteMutation = useDeleteCustomer()

  // Update tab title when customer loads
  if (customer) {
    updateTabTitle(customer.name)
  }

  // Handle back navigation
  const handleBack = useCallback(() => {
    navigate('/customers')
  }, [navigate])

  // Handle edit
  const handleEdit = useCallback(() => {
    setIsEditModalOpen(true)
  }, [])

  // Handle delete
  const handleDelete = useCallback(() => {
    confirmDialog.confirmDelete({
      title: 'Delete Customer',
      description: `Are you sure you want to delete "${customer?.name}"? This action cannot be undone.`,
      onConfirm: async () => {
        await deleteMutation.mutateAsync(customerId)
        navigate('/customers')
      },
    })
  }, [confirmDialog, customer?.name, customerId, deleteMutation, navigate])

  // Handle modal close
  const handleModalClose = useCallback(() => {
    setIsEditModalOpen(false)
  }, [])

  // Handle modal success
  const handleModalSuccess = useCallback(() => {
    setIsEditModalOpen(false)
    refetch()
  }, [refetch])

  // Handle asset click
  const handleAssetClick = useCallback(
    (asset: CustomerAsset) => {
      openTab(`/inventory/${asset.id}`, asset.name || asset.asset_tag, 'asset')
    },
    [openTab]
  )

  // Handle ticket click
  const handleTicketClick = useCallback(
    (ticket: CustomerTicket) => {
      openTab(`/tickets/${ticket.id}`, ticket.ticket_number, 'ticket')
    },
    [openTab]
  )

  // Handle accessory click
  const handleAccessoryClick = useCallback(
    (accessory: CustomerAccessory) => {
      openTab(`/accessories/${accessory.id}`, accessory.name, 'accessory')
    },
    [openTab]
  )

  // Tab definitions with counts
  const tabs: TabDefinition[] = useMemo(() => {
    if (!customer) return []
    return [
      { id: 'details', label: 'Details', icon: ClipboardDocumentListIcon },
      {
        id: 'assets',
        label: 'Assets',
        icon: ComputerDesktopIcon,
        count: customer.assigned_assets?.length || 0,
      },
      {
        id: 'tickets',
        label: 'Tickets',
        icon: TicketIcon,
        count: customer.related_tickets?.length || 0,
      },
      {
        id: 'accessories',
        label: 'Accessories',
        icon: BoltIcon,
        count: customer.assigned_accessories?.length || 0,
      },
      { id: 'transactions', label: 'Transactions', icon: ClockIcon },
    ]
  }, [customer])

  // Asset columns
  const assetColumns: ColumnDef<CustomerAsset>[] = useMemo(
    () => [
      {
        id: 'asset_tag',
        header: 'Asset Tag',
        accessorKey: 'asset_tag',
        cell: (row) => (
          <span className="font-medium text-gray-900 dark:text-white">
            {row.asset_tag}
          </span>
        ),
      },
      {
        id: 'name',
        header: 'Name',
        accessorKey: 'name',
      },
      {
        id: 'model',
        header: 'Model',
        accessorKey: 'model',
        cell: (row) => (
          <span className="text-gray-600 dark:text-gray-400">{row.model}</span>
        ),
      },
      {
        id: 'status',
        header: 'Status',
        accessorKey: 'status',
        cell: (row) => {
          const status = row.status?.toLowerCase()
          let variant: 'success' | 'info' | 'neutral' = 'neutral'
          if (status === 'deployed') variant = 'success'
          else if (status === 'in_stock') variant = 'info'
          return (
            <Badge variant={variant} size="sm">
              {row.status}
            </Badge>
          )
        },
      },
    ],
    []
  )

  // Accessory columns
  const accessoryColumns: ColumnDef<CustomerAccessory>[] = useMemo(
    () => [
      {
        id: 'name',
        header: 'Name',
        accessorKey: 'name',
        cell: (row) => (
          <span className="font-medium text-gray-900 dark:text-white">
            {row.name}
          </span>
        ),
      },
      {
        id: 'category',
        header: 'Category',
        accessorKey: 'category',
      },
      {
        id: 'model_no',
        header: 'Model',
        accessorKey: 'model_no',
        cell: (row) => (
          <span className="text-gray-600 dark:text-gray-400">{row.model_no}</span>
        ),
      },
      {
        id: 'quantity',
        header: 'Quantity',
        accessorKey: 'quantity',
        align: 'center',
        cell: (row) => (
          <Badge variant="info" size="sm">
            {row.quantity}
          </Badge>
        ),
      },
      {
        id: 'status',
        header: 'Status',
        accessorKey: 'status',
        cell: (row) => (
          <span className="text-gray-600 dark:text-gray-400">{row.status}</span>
        ),
      },
    ],
    []
  )

  // Ticket columns
  const ticketColumns: ColumnDef<CustomerTicket>[] = useMemo(
    () => [
      {
        id: 'ticket_number',
        header: 'Ticket #',
        accessorKey: 'ticket_number',
        cell: (row) => (
          <span className="font-medium text-blue-600 dark:text-blue-400">
            {row.ticket_number}
          </span>
        ),
      },
      {
        id: 'subject',
        header: 'Subject',
        accessorKey: 'subject',
        cell: (row) => (
          <div className="max-w-xs truncate">{row.subject || 'No subject'}</div>
        ),
      },
      {
        id: 'category',
        header: 'Category',
        accessorKey: 'category',
        cell: (row) => {
          const category = row.category?.replace(/_/g, ' ')
          return (
            <Badge variant="neutral" size="sm">
              {category || 'General'}
            </Badge>
          )
        },
      },
      {
        id: 'status',
        header: 'Status',
        accessorKey: 'status',
        cell: (row) => {
          const status = row.status?.toLowerCase()
          let variant: 'success' | 'info' | 'warning' | 'neutral' = 'neutral'
          if (status === 'new') variant = 'warning'
          else if (status === 'in_progress') variant = 'info'
          else if (status === 'resolved' || status === 'resolved_delivered')
            variant = 'success'
          return (
            <Badge variant={variant} size="sm" dot>
              {row.status?.replace(/_/g, ' ')}
            </Badge>
          )
        },
      },
      {
        id: 'queue_name',
        header: 'Queue',
        accessorKey: 'queue_name',
        cell: (row) => (
          <span className="text-gray-600 dark:text-gray-400">
            {row.queue_name || 'Unassigned'}
          </span>
        ),
      },
      {
        id: 'created_at',
        header: 'Created',
        accessorKey: 'created_at',
        cell: (row) => (
          <span className="text-gray-600 dark:text-gray-400">
            {row.created_at
              ? new Date(row.created_at).toLocaleDateString()
              : 'N/A'}
          </span>
        ),
      },
    ],
    []
  )

  // Transaction columns
  const transactionColumns: ColumnDef<CustomerTransaction>[] = useMemo(
    () => [
      {
        id: 'transaction_number',
        header: 'Transaction #',
        accessorKey: 'transaction_number',
        cell: (row) => (
          <span className="font-medium text-gray-900 dark:text-white">
            {row.transaction_number || 'N/A'}
          </span>
        ),
      },
      {
        id: 'item',
        header: 'Item',
        cell: (row) => {
          if (row.type === 'asset') {
            return (
              <div>
                {row.asset_name || 'Unknown Asset'}
                {row.asset_tag && (
                  <span className="text-gray-500 ml-1">({row.asset_tag})</span>
                )}
              </div>
            )
          }
          return (
            <div>
              {row.accessory_name || 'Unknown Accessory'}
              {row.accessory_category && (
                <span className="text-gray-500 ml-1">
                  ({row.accessory_category})
                </span>
              )}
            </div>
          )
        },
      },
      {
        id: 'transaction_type',
        header: 'Type',
        accessorKey: 'transaction_type',
        cell: (row) => {
          const type = row.transaction_type?.toLowerCase()
          let variant: 'success' | 'info' | 'warning' | 'neutral' = 'neutral'
          if (type === 'checkout') variant = 'success'
          else if (type === 'checkin' || type === 'return') variant = 'info'
          else if (type === 'add_stock') variant = 'warning'
          return (
            <Badge variant={variant} size="sm">
              {row.transaction_type}
            </Badge>
          )
        },
      },
      {
        id: 'quantity',
        header: 'Quantity',
        align: 'center',
        cell: (row) => (
          <span className="text-gray-600 dark:text-gray-400">
            {row.type === 'accessory' ? row.quantity || '1' : 'N/A'}
          </span>
        ),
      },
      {
        id: 'transaction_date',
        header: 'Date',
        accessorKey: 'transaction_date',
        cell: (row) => (
          <span className="text-gray-600 dark:text-gray-400">
            {row.transaction_date || 'N/A'}
          </span>
        ),
      },
      {
        id: 'notes',
        header: 'Notes',
        accessorKey: 'notes',
        cell: (row) => (
          <span className="text-gray-600 dark:text-gray-400 truncate max-w-[200px] block">
            {row.notes || 'No notes'}
          </span>
        ),
      },
    ],
    []
  )

  // Loading state
  if (isLoading) {
    return (
      <PageLayout
        title="Loading..."
        breadcrumbs={[
          { label: 'Customers', href: '/customers' },
          { label: 'Loading...' },
        ]}
      >
        <div className="flex items-center justify-center min-h-[400px]">
          <Spinner size="lg" />
        </div>
      </PageLayout>
    )
  }

  // Error state
  if (isError || !customer) {
    return (
      <PageLayout
        title="Error"
        breadcrumbs={[
          { label: 'Customers', href: '/customers' },
          { label: 'Error' },
        ]}
      >
        <Card>
          <EmptyState
            preset="error"
            title="Customer not found"
            description="The customer you are looking for does not exist or you do not have permission to view it."
            action={{
              label: 'Back to Customers',
              onClick: handleBack,
            }}
          />
        </Card>
      </PageLayout>
    )
  }

  // Get country colors
  const countryColors = customer.country
    ? COUNTRY_COLORS[customer.country as Country] || COUNTRY_COLORS.OTHER
    : null

  // Render tab content
  const renderTabContent = () => {
    switch (activeTab) {
      case 'details':
        return (
          <Card>
            <CardHeader>Contact Information</CardHeader>
            <dl className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
              <div className="flex items-start gap-3">
                <EnvelopeIcon className="w-5 h-5 text-gray-400 mt-0.5" />
                <div>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">
                    Email
                  </dt>
                  <dd className="text-sm text-gray-900 dark:text-white mt-1">
                    {customer.email || 'Not provided'}
                  </dd>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <PhoneIcon className="w-5 h-5 text-gray-400 mt-0.5" />
                <div>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">
                    Contact Number
                  </dt>
                  <dd className="text-sm text-gray-900 dark:text-white mt-1">
                    {customer.contact_number || 'Not provided'}
                  </dd>
                </div>
              </div>
              <div className="flex items-start gap-3 md:col-span-2">
                <MapPinIcon className="w-5 h-5 text-gray-400 mt-0.5" />
                <div>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">
                    Address
                  </dt>
                  <dd className="text-sm text-gray-900 dark:text-white mt-1">
                    {customer.address || 'Not provided'}
                  </dd>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <CalendarIcon className="w-5 h-5 text-gray-400 mt-0.5" />
                <div>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">
                    Created At
                  </dt>
                  <dd className="text-sm text-gray-900 dark:text-white mt-1">
                    {customer.created_at
                      ? new Date(customer.created_at).toLocaleString()
                      : 'Not available'}
                  </dd>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <ClockIcon className="w-5 h-5 text-gray-400 mt-0.5" />
                <div>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">
                    Last Updated
                  </dt>
                  <dd className="text-sm text-gray-900 dark:text-white mt-1">
                    {customer.updated_at
                      ? new Date(customer.updated_at).toLocaleString()
                      : 'Not available'}
                  </dd>
                </div>
              </div>
            </dl>
          </Card>
        )

      case 'assets':
        if (!customer.assigned_assets || customer.assigned_assets.length === 0) {
          return (
            <Card>
              <EmptyState
                icon={ComputerDesktopIcon}
                title="No assets assigned"
                description="No assets are currently assigned to this customer."
                size="sm"
              />
            </Card>
          )
        }
        return (
          <DataTable
            data={customer.assigned_assets}
            columns={assetColumns}
            onRowClick={handleAssetClick}
            getRowId={(row) => String(row.id)}
            emptyMessage="No assets assigned"
          />
        )

      case 'tickets':
        if (!customer.related_tickets || customer.related_tickets.length === 0) {
          return (
            <Card>
              <EmptyState
                icon={TicketIcon}
                title="No tickets"
                description="No tickets found for this customer."
                size="sm"
              />
            </Card>
          )
        }
        return (
          <DataTable
            data={customer.related_tickets}
            columns={ticketColumns}
            onRowClick={handleTicketClick}
            getRowId={(row) => String(row.id)}
            emptyMessage="No tickets found"
          />
        )

      case 'accessories':
        if (
          !customer.assigned_accessories ||
          customer.assigned_accessories.length === 0
        ) {
          return (
            <Card>
              <EmptyState
                icon={BoltIcon}
                title="No accessories assigned"
                description="No accessories are currently assigned to this customer."
                size="sm"
              />
            </Card>
          )
        }
        return (
          <DataTable
            data={customer.assigned_accessories}
            columns={accessoryColumns}
            onRowClick={handleAccessoryClick}
            getRowId={(row) => String(row.id)}
            emptyMessage="No accessories assigned"
          />
        )

      case 'transactions':
        if (isLoadingTransactions) {
          return (
            <Card>
              <div className="flex items-center justify-center py-12">
                <Spinner size="md" />
                <span className="ml-3 text-gray-600 dark:text-gray-400">
                  Loading transactions...
                </span>
              </div>
            </Card>
          )
        }
        if (transactions.length === 0) {
          return (
            <Card>
              <EmptyState
                icon={ClockIcon}
                title="No transactions"
                description="No transactions found for this customer."
                size="sm"
              />
            </Card>
          )
        }
        return (
          <DataTable
            data={transactions}
            columns={transactionColumns}
            getRowId={(row) => row.transaction_number || String(Math.random())}
            emptyMessage="No transactions found"
          />
        )

      default:
        return null
    }
  }

  return (
    <PageLayout
      title={customer.name}
      breadcrumbs={[
        { label: 'Customers', href: '/customers' },
        { label: customer.name },
      ]}
      actions={
        <div className="flex gap-2">
          <Button
            variant="secondary"
            leftIcon={<PencilIcon className="w-4 h-4" />}
            onClick={handleEdit}
          >
            Edit
          </Button>
          <Button
            variant="danger"
            leftIcon={<TrashIcon className="w-4 h-4" />}
            onClick={handleDelete}
          >
            Delete
          </Button>
        </div>
      }
    >
      {/* Back Link */}
      <button
        onClick={handleBack}
        className="flex items-center text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 mb-6"
      >
        <ArrowLeftIcon className="w-4 h-4 mr-2" />
        Back to Customers
      </button>

      {/* Customer Header Card */}
      <Card className="mb-6">
        <div className="flex flex-col sm:flex-row justify-between items-start gap-4">
          <div className="flex items-start gap-4">
            {/* Avatar */}
            <div
              className={cn(
                'w-12 h-12 rounded-full flex items-center justify-center',
                countryColors
                  ? countryColors.bg
                  : 'bg-gray-100 dark:bg-gray-700'
              )}
            >
              <span
                className={cn(
                  'text-lg font-bold',
                  countryColors ? countryColors.text : 'text-gray-600'
                )}
              >
                {customer.name.charAt(0).toUpperCase()}
              </span>
            </div>

            {/* Info */}
            <div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                {customer.name}
              </h2>
              <div className="flex items-center gap-2 mt-1 text-sm text-gray-500 dark:text-gray-400">
                <BuildingOfficeIcon className="w-4 h-4" />
                <span>{customer.company?.name || 'No Company'}</span>
              </div>
              {customer.country && countryColors && (
                <div className="mt-2">
                  <span
                    className={cn(
                      'inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium',
                      countryColors.bg,
                      countryColors.text
                    )}
                  >
                    <GlobeAltIcon className="w-3 h-3" />
                    {customer.country}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Quick Stats */}
          <div className="flex gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {customer.assigned_assets?.length || 0}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                Assets
              </div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {customer.related_tickets?.length || 0}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                Tickets
              </div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">
                {customer.assigned_accessories?.length || 0}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                Accessories
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Tab Navigation */}
      <div className="mb-4 border-b border-gray-200 dark:border-gray-700">
        <nav className="flex flex-wrap -mb-px" role="tablist">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'inline-flex items-center gap-2 px-4 py-3 border-b-2 text-sm font-medium transition-colors',
                activeTab === tab.id
                  ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
              )}
              role="tab"
              aria-selected={activeTab === tab.id}
            >
              <tab.icon className="w-5 h-5" />
              {tab.label}
              {tab.count !== undefined && tab.count > 0 && (
                <Badge variant="info" size="sm">
                  {tab.count}
                </Badge>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {renderTabContent()}

      {/* Edit Modal */}
      <CustomerModal
        isOpen={isEditModalOpen}
        onClose={handleModalClose}
        onSuccess={handleModalSuccess}
        customer={customer}
      />

      {/* Confirm Dialog */}
      <ConfirmDialog
        isOpen={confirmDialog.isOpen}
        onClose={confirmDialog.onClose}
        onConfirm={confirmDialog.onConfirm}
        title={confirmDialog.title}
        description={confirmDialog.description}
        variant={confirmDialog.variant}
        confirmText={confirmDialog.confirmText}
        cancelText={confirmDialog.cancelText}
      />
    </PageLayout>
  )
}

export default CustomerDetailPage
