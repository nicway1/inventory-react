/**
 * InventoryList Component
 *
 * Main inventory page with tabs for Assets and Accessories.
 * Features: filters, search, bulk actions, checkout cart, pagination.
 */

import React, { useState, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  PlusIcon,
  ArrowDownTrayIcon,
  ShoppingCartIcon,
  FunnelIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArchiveBoxIcon,
  TruckIcon,
  WrenchScrewdriverIcon,
  CubeIcon,
} from '@heroicons/react/24/outline'
import { PageLayout } from '@/components/templates/PageLayout'
import { DataTable, type ColumnDef } from '@/components/organisms/DataTable'
import { Badge } from '@/components/atoms/Badge'
import { Button } from '@/components/atoms/Button'
import { SearchInput } from '@/components/molecules/SearchInput'
import { Modal } from '@/components/organisms/Modal'
import { NoSearchResults } from '@/components/organisms/EmptyState'
import { cn } from '@/utils/cn'
import { useLocalStorage } from '@/hooks/useLocalStorage'
import { useDebounce } from '@/hooks/useDebounce'
import type {
  Asset,
  Accessory,
  AssetStatus,
  InventoryFilters,
  AccessoryFilters,
  CheckoutCartItem,
  Customer,
} from '@/types/inventory'
import {
  fetchAssets,
  fetchAccessories,
  fetchCustomers,
  processCheckout,
  exportAssetsToCSV,
  exportAccessoriesToCSV,
  bulkUpdateAssetStatus,
} from '@/services/inventory.service'

// Tab types
type InventoryTab = 'assets' | 'accessories'

// Status badge configuration
const statusConfig: Record<AssetStatus, { variant: 'success' | 'warning' | 'danger' | 'info' | 'neutral'; icon: React.ElementType }> = {
  IN_STOCK: { variant: 'info', icon: CubeIcon },
  DEPLOYED: { variant: 'success', icon: CheckCircleIcon },
  READY_TO_DEPLOY: { variant: 'info', icon: TruckIcon },
  REPAIR: { variant: 'warning', icon: WrenchScrewdriverIcon },
  ARCHIVED: { variant: 'neutral', icon: ArchiveBoxIcon },
  DISPOSED: { variant: 'danger', icon: XCircleIcon },
}

// Status options for filter
const statusOptions: { value: AssetStatus | ''; label: string }[] = [
  { value: '', label: 'All Statuses' },
  { value: 'IN_STOCK', label: 'In Stock' },
  { value: 'DEPLOYED', label: 'Deployed' },
  { value: 'READY_TO_DEPLOY', label: 'Ready to Deploy' },
  { value: 'REPAIR', label: 'Repair' },
  { value: 'ARCHIVED', label: 'Archived' },
  { value: 'DISPOSED', label: 'Disposed' },
]

// Asset table columns
const assetColumns: ColumnDef<Asset>[] = [
  {
    id: 'image',
    header: '',
    width: '60px',
    cell: (row) => (
      <div className="w-10 h-10 rounded bg-gray-100 flex items-center justify-center overflow-hidden">
        {row.image_url ? (
          <img src={row.image_url} alt={row.name} className="w-full h-full object-cover" />
        ) : (
          <CubeIcon className="w-5 h-5 text-gray-400" />
        )}
      </div>
    ),
  },
  {
    id: 'asset_tag',
    header: 'Asset Tag',
    accessorKey: 'asset_tag',
    sortable: true,
    cell: (row) => (
      <span className="font-medium text-gray-900">{row.asset_tag}</span>
    ),
  },
  {
    id: 'name',
    header: 'Name',
    accessorKey: 'name',
    sortable: true,
    cell: (row) => (
      <div>
        <div className="font-medium text-gray-900">{row.name || row.product}</div>
        {row.cpu_type && (
          <div className="text-xs text-gray-500">
            {row.cpu_type}{row.cpu_cores ? `, ${row.cpu_cores} cores` : ''}
          </div>
        )}
        {(row.memory || row.harddrive) && (
          <div className="text-xs text-gray-500">
            {row.memory && `${row.memory} RAM`}
            {row.memory && row.harddrive && ', '}
            {row.harddrive && `${row.harddrive} Storage`}
          </div>
        )}
      </div>
    ),
  },
  {
    id: 'model',
    header: 'Model',
    accessorKey: 'model',
    sortable: true,
  },
  {
    id: 'serial_num',
    header: 'Serial',
    accessorKey: 'serial_num',
    cell: (row) => (
      <span className="font-mono text-sm text-gray-600">{row.serial_num || '-'}</span>
    ),
  },
  {
    id: 'status',
    header: 'Status',
    accessorKey: 'status',
    sortable: true,
    cell: (row) => {
      const config = statusConfig[row.status] || statusConfig.IN_STOCK
      const Icon = config.icon
      return (
        <Badge variant={config.variant} size="sm">
          <Icon className="w-3 h-3 mr-1" />
          {row.status_label?.name || row.status.replace('_', ' ')}
        </Badge>
      )
    },
  },
  {
    id: 'customer',
    header: 'Customer',
    cell: (row) => (
      <div>
        <div className="text-sm text-gray-900">{row.customer?.name || row.customer_name || '-'}</div>
        {row.country && (
          <div className="text-xs text-gray-500">{row.country}</div>
        )}
        {row.legal_hold && (
          <span className="inline-flex items-center px-2 py-0.5 mt-1 rounded bg-red-600 text-white text-xs font-bold uppercase">
            Legal Hold
          </span>
        )}
      </div>
    ),
  },
  {
    id: 'condition',
    header: 'Condition',
    accessorKey: 'condition',
    cell: (row) => {
      if (!row.condition) return <span className="text-gray-400">-</span>
      const conditionColors: Record<string, string> = {
        NEW: 'text-green-600',
        GOOD: 'text-blue-600',
        FAIR: 'text-yellow-600',
        POOR: 'text-orange-600',
      }
      return (
        <span className={cn('text-sm font-medium', conditionColors[row.condition] || 'text-gray-600')}>
          {row.condition}
        </span>
      )
    },
  },
]

// Accessory table columns
const accessoryColumns: ColumnDef<Accessory>[] = [
  {
    id: 'image',
    header: '',
    width: '60px',
    cell: (row) => (
      <div className="w-10 h-10 rounded bg-gray-100 flex items-center justify-center overflow-hidden">
        {row.image_url ? (
          <img src={row.image_url} alt={row.name} className="w-full h-full object-cover" />
        ) : (
          <CubeIcon className="w-5 h-5 text-gray-400" />
        )}
      </div>
    ),
  },
  {
    id: 'name',
    header: 'Name',
    accessorKey: 'name',
    sortable: true,
    cell: (row) => (
      <span className="font-medium text-gray-900">{row.name}</span>
    ),
  },
  {
    id: 'category',
    header: 'Category',
    accessorKey: 'category',
    sortable: true,
  },
  {
    id: 'manufacturer',
    header: 'Manufacturer',
    accessorKey: 'manufacturer',
    sortable: true,
    cell: (row) => row.manufacturer || <span className="text-gray-400">-</span>,
  },
  {
    id: 'total_quantity',
    header: 'Total',
    accessorKey: 'total_quantity',
    sortable: true,
    align: 'right',
    cell: (row) => (
      <span className="font-semibold text-gray-900">{row.total_quantity}</span>
    ),
  },
  {
    id: 'available_quantity',
    header: 'Available',
    accessorKey: 'available_quantity',
    sortable: true,
    align: 'right',
    cell: (row) => (
      <span className={cn(
        'font-semibold',
        row.available_quantity > 0 ? 'text-blue-600' : 'text-red-600'
      )}>
        {row.available_quantity}
      </span>
    ),
  },
  {
    id: 'checked_out',
    header: 'Checked Out',
    align: 'right',
    cell: (row) => {
      const checkedOut = row.total_quantity - row.available_quantity
      return (
        <span className="text-gray-600">{checkedOut}</span>
      )
    },
  },
  {
    id: 'status',
    header: 'Status',
    accessorKey: 'status',
    cell: (row) => {
      const variant = row.status === 'Available' ? 'success' : row.status === 'Out of Stock' ? 'danger' : 'warning'
      return (
        <Badge variant={variant} size="sm">
          {row.status}
        </Badge>
      )
    },
  },
]

export function InventoryList() {
  const navigate = useNavigate()

  // Active tab state
  const [activeTab, setActiveTab] = useState<InventoryTab>('assets')

  // Assets state
  const [assets, setAssets] = useState<Asset[]>([])
  const [assetsLoading, setAssetsLoading] = useState(false)
  const [assetsTotalCount, setAssetsTotalCount] = useState(0)
  const [assetsPage, setAssetsPage] = useState(1)
  const [assetsSortBy, setAssetsSortBy] = useState('asset_tag')
  const [assetsSortOrder, setAssetsSortOrder] = useState<'asc' | 'desc'>('asc')
  const [assetsFilters, setAssetsFilters] = useState<InventoryFilters>({})
  const [assetsSearchQuery, setAssetsSearchQuery] = useState('')

  // Accessories state
  const [accessories, setAccessories] = useState<Accessory[]>([])
  const [accessoriesLoading, setAccessoriesLoading] = useState(false)
  const [accessoriesTotalCount, setAccessoriesTotalCount] = useState(0)
  const [accessoriesPage, setAccessoriesPage] = useState(1)
  const [accessoriesSortBy, setAccessoriesSortBy] = useState('name')
  const [accessoriesSortOrder, setAccessoriesSortOrder] = useState<'asc' | 'desc'>('asc')
  const [accessoriesFilters, setAccessoriesFilters] = useState<AccessoryFilters>({})
  const [accessoriesSearchQuery, setAccessoriesSearchQuery] = useState('')

  // Selection state
  const [selectedAssetIds, setSelectedAssetIds] = useState<string[]>([])
  const [selectedAccessoryIds, setSelectedAccessoryIds] = useState<string[]>([])

  // Checkout cart state (persisted to localStorage)
  const [checkoutCart, setCheckoutCart, clearCheckoutCart] = useLocalStorage<CheckoutCartItem[]>('truelog-checkout-cart', [])
  const [isCheckoutModalOpen, setIsCheckoutModalOpen] = useState(false)
  const [customers, setCustomers] = useState<Customer[]>([])
  const [selectedCustomerId, setSelectedCustomerId] = useState<number | null>(null)
  const [checkoutLoading, setCheckoutLoading] = useState(false)

  // Bulk actions state
  const [isBulkStatusModalOpen, setIsBulkStatusModalOpen] = useState(false)
  const [bulkStatusValue, setBulkStatusValue] = useState<AssetStatus>('IN_STOCK')
  const [bulkActionLoading, setBulkActionLoading] = useState(false)

  // Filter visibility
  const [showFilters, setShowFilters] = useState(true)

  // Debounced search
  const debouncedAssetsSearch = useDebounce(assetsSearchQuery, 300)
  const debouncedAccessoriesSearch = useDebounce(accessoriesSearchQuery, 300)

  const pageSize = 25

  // Fetch assets
  const loadAssets = useCallback(async () => {
    setAssetsLoading(true)
    try {
      const response = await fetchAssets({
        page: assetsPage,
        per_page: pageSize,
        sort: assetsSortBy,
        order: assetsSortOrder,
        search: debouncedAssetsSearch || undefined,
        status: assetsFilters.status || undefined,
        asset_type: assetsFilters.type || undefined,
        manufacturer: assetsFilters.manufacturer || undefined,
      })
      setAssets(response.items)
      setAssetsTotalCount(response.total)
    } catch (error) {
      console.error('Failed to fetch assets:', error)
      setAssets([])
      setAssetsTotalCount(0)
    } finally {
      setAssetsLoading(false)
    }
  }, [assetsPage, assetsSortBy, assetsSortOrder, debouncedAssetsSearch, assetsFilters])

  // Fetch accessories
  const loadAccessories = useCallback(async () => {
    setAccessoriesLoading(true)
    try {
      const response = await fetchAccessories({
        page: accessoriesPage,
        per_page: pageSize,
        sort: accessoriesSortBy,
        order: accessoriesSortOrder,
        search: debouncedAccessoriesSearch || undefined,
        category: accessoriesFilters.category || undefined,
        manufacturer: accessoriesFilters.manufacturer || undefined,
        country: accessoriesFilters.country || undefined,
      })
      setAccessories(response.items)
      setAccessoriesTotalCount(response.total)
    } catch (error) {
      console.error('Failed to fetch accessories:', error)
      setAccessories([])
      setAccessoriesTotalCount(0)
    } finally {
      setAccessoriesLoading(false)
    }
  }, [accessoriesPage, accessoriesSortBy, accessoriesSortOrder, debouncedAccessoriesSearch, accessoriesFilters])

  // Load customers for checkout
  const loadCustomers = useCallback(async () => {
    try {
      const data = await fetchCustomers()
      setCustomers(data)
    } catch (error) {
      console.error('Failed to fetch customers:', error)
    }
  }, [])

  // Effect to load data based on active tab
  useEffect(() => {
    if (activeTab === 'assets') {
      loadAssets()
    } else {
      loadAccessories()
    }
  }, [activeTab, loadAssets, loadAccessories])

  // Load customers on mount
  useEffect(() => {
    loadCustomers()
  }, [loadCustomers])

  // Handle sort change for assets
  const handleAssetsSort = useCallback((column: string) => {
    if (assetsSortBy === column) {
      setAssetsSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setAssetsSortBy(column)
      setAssetsSortOrder('asc')
    }
    setAssetsPage(1)
  }, [assetsSortBy])

  // Handle sort change for accessories
  const handleAccessoriesSort = useCallback((column: string) => {
    if (accessoriesSortBy === column) {
      setAccessoriesSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setAccessoriesSortBy(column)
      setAccessoriesSortOrder('asc')
    }
    setAccessoriesPage(1)
  }, [accessoriesSortBy])

  // Handle asset row click
  const handleAssetRowClick = useCallback((asset: Asset) => {
    navigate(`/inventory/assets/${asset.id}`)
  }, [navigate])

  // Handle accessory row click
  const handleAccessoryRowClick = useCallback((accessory: Accessory) => {
    navigate(`/inventory/accessories/${accessory.id}`)
  }, [navigate])

  // Add selected items to checkout cart
  const addToCheckoutCart = useCallback(() => {
    const newItems: CheckoutCartItem[] = []

    if (activeTab === 'assets') {
      const selectedAssets = assets.filter((a) => selectedAssetIds.includes(String(a.id)))
      selectedAssets.forEach((asset) => {
        if (!checkoutCart.some((item) => item.id === asset.id && item.type === 'asset')) {
          newItems.push({
            id: asset.id,
            name: asset.name || asset.product || 'Unknown Asset',
            type: 'asset',
            asset_tag: asset.asset_tag,
            image_url: asset.image_url,
            quantity: 1,
          })
        }
      })
      setSelectedAssetIds([])
    } else {
      const selectedAccessoriesList = accessories.filter((a) => selectedAccessoryIds.includes(String(a.id)))
      selectedAccessoriesList.forEach((accessory) => {
        if (!checkoutCart.some((item) => item.id === accessory.id && item.type === 'accessory')) {
          newItems.push({
            id: accessory.id,
            name: accessory.name,
            type: 'accessory',
            category: accessory.category,
            image_url: accessory.image_url,
            quantity: 1,
          })
        }
      })
      setSelectedAccessoryIds([])
    }

    if (newItems.length > 0) {
      setCheckoutCart([...checkoutCart, ...newItems])
    }
  }, [activeTab, assets, accessories, selectedAssetIds, selectedAccessoryIds, checkoutCart, setCheckoutCart])

  // Remove item from checkout cart
  const removeFromCheckoutCart = useCallback((itemId: number, itemType: 'asset' | 'accessory') => {
    setCheckoutCart(checkoutCart.filter((item) => !(item.id === itemId && item.type === itemType)))
  }, [checkoutCart, setCheckoutCart])

  // Update quantity in checkout cart
  const updateCheckoutQuantity = useCallback((itemId: number, itemType: 'asset' | 'accessory', quantity: number) => {
    setCheckoutCart(checkoutCart.map((item) => {
      if (item.id === itemId && item.type === itemType) {
        return { ...item, quantity: Math.max(1, quantity) }
      }
      return item
    }))
  }, [checkoutCart, setCheckoutCart])

  // Process checkout
  const handleProcessCheckout = useCallback(async () => {
    if (!selectedCustomerId || checkoutCart.length === 0) return

    setCheckoutLoading(true)
    try {
      await processCheckout({
        customer_id: selectedCustomerId,
        items: checkoutCart.map((item) => ({
          id: item.id,
          type: item.type,
          quantity: item.quantity,
        })),
      })
      clearCheckoutCart()
      setSelectedCustomerId(null)
      setIsCheckoutModalOpen(false)
      // Reload data to reflect changes
      if (activeTab === 'assets') {
        loadAssets()
      } else {
        loadAccessories()
      }
    } catch (error) {
      console.error('Checkout failed:', error)
    } finally {
      setCheckoutLoading(false)
    }
  }, [selectedCustomerId, checkoutCart, clearCheckoutCart, activeTab, loadAssets, loadAccessories])

  // Bulk status change
  const handleBulkStatusChange = useCallback(async () => {
    if (selectedAssetIds.length === 0) return

    setBulkActionLoading(true)
    try {
      await bulkUpdateAssetStatus({
        asset_ids: selectedAssetIds.map(Number),
        status: bulkStatusValue,
      })
      setSelectedAssetIds([])
      setIsBulkStatusModalOpen(false)
      loadAssets()
    } catch (error) {
      console.error('Bulk status change failed:', error)
    } finally {
      setBulkActionLoading(false)
    }
  }, [selectedAssetIds, bulkStatusValue, loadAssets])

  // Export to CSV
  const handleExport = useCallback(async () => {
    try {
      let blob: Blob
      let filename: string

      if (activeTab === 'assets') {
        const ids = selectedAssetIds.length > 0 ? selectedAssetIds.map(Number) : undefined
        blob = await exportAssetsToCSV(ids)
        filename = 'assets_export.csv'
      } else {
        const ids = selectedAccessoryIds.length > 0 ? selectedAccessoryIds.map(Number) : undefined
        blob = await exportAccessoriesToCSV(ids)
        filename = 'accessories_export.csv'
      }

      // Download the file
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Export failed:', error)
    }
  }, [activeTab, selectedAssetIds, selectedAccessoryIds])

  // Clear filters
  const clearFilters = useCallback(() => {
    if (activeTab === 'assets') {
      setAssetsFilters({})
      setAssetsSearchQuery('')
      setAssetsPage(1)
    } else {
      setAccessoriesFilters({})
      setAccessoriesSearchQuery('')
      setAccessoriesPage(1)
    }
  }, [activeTab])

  // Computed values
  const hasSelectedItems = activeTab === 'assets' ? selectedAssetIds.length > 0 : selectedAccessoryIds.length > 0
  const selectedCount = activeTab === 'assets' ? selectedAssetIds.length : selectedAccessoryIds.length
  const cartItemCount = checkoutCart.length

  // Tab component
  const TabButton = ({ tab, label, count }: { tab: InventoryTab; label: string; count: number }) => (
    <button
      onClick={() => setActiveTab(tab)}
      className={cn(
        'px-4 py-2 text-sm font-medium rounded-t-lg transition-colors',
        activeTab === tab
          ? 'bg-white text-[#0176D3] border-t border-l border-r border-[#DDDBDA] -mb-px'
          : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
      )}
    >
      {label}
      <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-gray-200 text-gray-600">
        {count}
      </span>
    </button>
  )

  // Filter select component
  const FilterSelect = ({
    label,
    value,
    onChange,
    options,
  }: {
    label: string
    value: string
    onChange: (value: string) => void
    options: { value: string; label: string }[]
  }) => (
    <div>
      <label className="block text-xs font-medium text-gray-700 mb-1">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0176D3]/20 focus:border-[#0176D3]"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  )

  // Action buttons
  const actionButtons = (
    <div className="flex items-center gap-3">
      <Button
        variant="primary"
        size="sm"
        leftIcon={<PlusIcon className="w-4 h-4" />}
        onClick={() => navigate(activeTab === 'assets' ? '/inventory/assets/new' : '/inventory/accessories/new')}
      >
        Add {activeTab === 'assets' ? 'Asset' : 'Accessory'}
      </Button>
      <Button
        variant="secondary"
        size="sm"
        leftIcon={<ArrowDownTrayIcon className="w-4 h-4" />}
        onClick={() => navigate('/inventory/import')}
      >
        Import
      </Button>
    </div>
  )

  return (
    <PageLayout
      title="Inventory"
      breadcrumbs={[{ label: 'Inventory' }]}
      actions={actionButtons}
    >
      {/* Tabs */}
      <div className="flex items-center justify-between mb-4 border-b border-[#DDDBDA]">
        <div className="flex gap-1">
          <TabButton tab="assets" label="Assets" count={assetsTotalCount} />
          <TabButton tab="accessories" label="Accessories" count={accessoriesTotalCount} />
        </div>

        {/* Bulk actions */}
        <div className="flex items-center gap-2 pb-2">
          {hasSelectedItems && (
            <>
              <span className="text-sm text-gray-600">
                {selectedCount} selected
              </span>
              <Button
                variant="secondary"
                size="sm"
                leftIcon={<ShoppingCartIcon className="w-4 h-4" />}
                onClick={addToCheckoutCart}
              >
                Add to Cart
              </Button>
              {activeTab === 'assets' && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setIsBulkStatusModalOpen(true)}
                >
                  Change Status
                </Button>
              )}
              <Button
                variant="secondary"
                size="sm"
                leftIcon={<ArrowDownTrayIcon className="w-4 h-4" />}
                onClick={handleExport}
              >
                Export CSV
              </Button>
            </>
          )}

          {/* Checkout cart button */}
          <Button
            variant={cartItemCount > 0 ? 'primary' : 'ghost'}
            size="sm"
            leftIcon={<ShoppingCartIcon className="w-4 h-4" />}
            onClick={() => setIsCheckoutModalOpen(true)}
          >
            Checkout
            {cartItemCount > 0 && (
              <span className="ml-1 px-1.5 py-0.5 text-xs rounded-full bg-white text-[#0176D3]">
                {cartItemCount}
              </span>
            )}
          </Button>
        </div>
      </div>

      {/* Filter bar */}
      <div className="bg-white rounded-lg border border-[#DDDBDA] shadow-sm mb-4">
        <div className="p-4">
          <div className="flex items-center gap-4 mb-4">
            <SearchInput
              value={activeTab === 'assets' ? assetsSearchQuery : accessoriesSearchQuery}
              onChange={activeTab === 'assets' ? setAssetsSearchQuery : setAccessoriesSearchQuery}
              placeholder={`Search ${activeTab}...`}
              className="flex-1 max-w-md"
            />
            <Button
              variant="ghost"
              size="sm"
              leftIcon={<FunnelIcon className="w-4 h-4" />}
              onClick={() => setShowFilters(!showFilters)}
            >
              {showFilters ? 'Hide Filters' : 'Show Filters'}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              leftIcon={<ArrowPathIcon className="w-4 h-4" />}
              onClick={activeTab === 'assets' ? loadAssets : loadAccessories}
            >
              Refresh
            </Button>
          </div>

          {showFilters && (
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
              {activeTab === 'assets' ? (
                <>
                  <FilterSelect
                    label="Status"
                    value={assetsFilters.status || ''}
                    onChange={(value) => {
                      setAssetsFilters({ ...assetsFilters, status: value as AssetStatus | '' })
                      setAssetsPage(1)
                    }}
                    options={statusOptions}
                  />
                  <FilterSelect
                    label="Type"
                    value={assetsFilters.type || ''}
                    onChange={(value) => {
                      setAssetsFilters({ ...assetsFilters, type: value })
                      setAssetsPage(1)
                    }}
                    options={[
                      { value: '', label: 'All Types' },
                      { value: 'laptop', label: 'Laptop' },
                      { value: 'desktop', label: 'Desktop' },
                      { value: 'monitor', label: 'Monitor' },
                      { value: 'tablet', label: 'Tablet' },
                      { value: 'phone', label: 'Phone' },
                    ]}
                  />
                  <FilterSelect
                    label="Manufacturer"
                    value={assetsFilters.manufacturer || ''}
                    onChange={(value) => {
                      setAssetsFilters({ ...assetsFilters, manufacturer: value })
                      setAssetsPage(1)
                    }}
                    options={[
                      { value: '', label: 'All Manufacturers' },
                      { value: 'apple', label: 'Apple' },
                      { value: 'dell', label: 'Dell' },
                      { value: 'hp', label: 'HP' },
                      { value: 'lenovo', label: 'Lenovo' },
                    ]}
                  />
                  <FilterSelect
                    label="Customer"
                    value={assetsFilters.customer || ''}
                    onChange={(value) => {
                      setAssetsFilters({ ...assetsFilters, customer: value })
                      setAssetsPage(1)
                    }}
                    options={[
                      { value: '', label: 'All Customers' },
                      ...customers.map((c) => ({ value: String(c.id), label: c.name })),
                    ]}
                  />
                  <div className="flex items-end">
                    <Button variant="ghost" size="sm" onClick={clearFilters}>
                      Clear Filters
                    </Button>
                  </div>
                </>
              ) : (
                <>
                  <FilterSelect
                    label="Category"
                    value={accessoriesFilters.category || ''}
                    onChange={(value) => {
                      setAccessoriesFilters({ ...accessoriesFilters, category: value })
                      setAccessoriesPage(1)
                    }}
                    options={[
                      { value: '', label: 'All Categories' },
                      { value: 'keyboard', label: 'Keyboard' },
                      { value: 'mouse', label: 'Mouse' },
                      { value: 'cable', label: 'Cable' },
                      { value: 'adapter', label: 'Adapter' },
                    ]}
                  />
                  <FilterSelect
                    label="Manufacturer"
                    value={accessoriesFilters.manufacturer || ''}
                    onChange={(value) => {
                      setAccessoriesFilters({ ...accessoriesFilters, manufacturer: value })
                      setAccessoriesPage(1)
                    }}
                    options={[
                      { value: '', label: 'All Manufacturers' },
                    ]}
                  />
                  <FilterSelect
                    label="Status"
                    value={accessoriesFilters.status || ''}
                    onChange={(value) => {
                      setAccessoriesFilters({ ...accessoriesFilters, status: value as 'Available' | 'Out of Stock' | 'Low Stock' | '' })
                      setAccessoriesPage(1)
                    }}
                    options={[
                      { value: '', label: 'All Statuses' },
                      { value: 'Available', label: 'Available' },
                      { value: 'Out of Stock', label: 'Out of Stock' },
                      { value: 'Low Stock', label: 'Low Stock' },
                    ]}
                  />
                  <div className="flex items-end">
                    <Button variant="ghost" size="sm" onClick={clearFilters}>
                      Clear Filters
                    </Button>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Data table */}
      {activeTab === 'assets' ? (
        assets.length === 0 && !assetsLoading && debouncedAssetsSearch ? (
          <div className="bg-white rounded-lg border border-[#DDDBDA] shadow-sm">
            <NoSearchResults query={debouncedAssetsSearch} onClear={() => setAssetsSearchQuery('')} />
          </div>
        ) : (
          <DataTable
            data={assets}
            columns={assetColumns}
            isLoading={assetsLoading}
            emptyMessage="No assets found"
            getRowId={(row) => String(row.id)}
            onRowClick={handleAssetRowClick}
            selection={{
              selected: selectedAssetIds,
              onSelect: setSelectedAssetIds,
            }}
            sorting={{
              sortBy: assetsSortBy,
              sortOrder: assetsSortOrder,
              onSort: handleAssetsSort,
            }}
            pagination={{
              page: assetsPage,
              pageSize,
              total: assetsTotalCount,
              onPageChange: setAssetsPage,
            }}
            rowClassName={(row) =>
              row.legal_hold ? 'bg-red-50 border-l-4 border-red-600' : ''
            }
          />
        )
      ) : (
        accessories.length === 0 && !accessoriesLoading && debouncedAccessoriesSearch ? (
          <div className="bg-white rounded-lg border border-[#DDDBDA] shadow-sm">
            <NoSearchResults query={debouncedAccessoriesSearch} onClear={() => setAccessoriesSearchQuery('')} />
          </div>
        ) : (
          <DataTable
            data={accessories}
            columns={accessoryColumns}
            isLoading={accessoriesLoading}
            emptyMessage="No accessories found"
            getRowId={(row) => String(row.id)}
            onRowClick={handleAccessoryRowClick}
            selection={{
              selected: selectedAccessoryIds,
              onSelect: setSelectedAccessoryIds,
            }}
            sorting={{
              sortBy: accessoriesSortBy,
              sortOrder: accessoriesSortOrder,
              onSort: handleAccessoriesSort,
            }}
            pagination={{
              page: accessoriesPage,
              pageSize,
              total: accessoriesTotalCount,
              onPageChange: setAccessoriesPage,
            }}
          />
        )
      )}

      {/* Checkout Modal */}
      <Modal
        isOpen={isCheckoutModalOpen}
        onClose={() => setIsCheckoutModalOpen(false)}
        title="Checkout Cart"
        size="lg"
        footer={
          <>
            <Button
              variant="ghost"
              onClick={() => {
                clearCheckoutCart()
              }}
              disabled={checkoutCart.length === 0}
            >
              Clear Cart
            </Button>
            <Button
              variant="primary"
              onClick={handleProcessCheckout}
              isLoading={checkoutLoading}
              disabled={!selectedCustomerId || checkoutCart.length === 0}
            >
              Process Checkout
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          {/* Customer selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Select Customer
            </label>
            <select
              value={selectedCustomerId || ''}
              onChange={(e) => setSelectedCustomerId(e.target.value ? Number(e.target.value) : null)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0176D3]/20 focus:border-[#0176D3]"
            >
              <option value="">Choose a customer...</option>
              {customers.map((customer) => (
                <option key={customer.id} value={customer.id}>
                  {customer.name}
                </option>
              ))}
            </select>
          </div>

          {/* Cart items */}
          <div className="border-t pt-4">
            <h4 className="text-sm font-medium text-gray-900 mb-3">Items ({checkoutCart.length})</h4>
            {checkoutCart.length === 0 ? (
              <p className="text-gray-500 text-center py-4">No items in cart</p>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {checkoutCart.map((item) => (
                  <div
                    key={`${item.type}-${item.id}`}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded bg-gray-200 flex items-center justify-center">
                        {item.image_url ? (
                          <img src={item.image_url} alt={item.name} className="w-full h-full object-cover rounded" />
                        ) : (
                          <CubeIcon className="w-5 h-5 text-gray-400" />
                        )}
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">{item.name}</p>
                        <p className="text-xs text-gray-500">
                          {item.type === 'asset' ? `Asset Tag: ${item.asset_tag}` : item.category}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {item.type === 'accessory' && (
                        <input
                          type="number"
                          min="1"
                          value={item.quantity}
                          onChange={(e) => updateCheckoutQuantity(item.id, item.type, parseInt(e.target.value) || 1)}
                          className="w-16 px-2 py-1 text-sm border border-gray-300 rounded"
                        />
                      )}
                      <button
                        onClick={() => removeFromCheckoutCart(item.id, item.type)}
                        className="p-1 text-gray-400 hover:text-red-600"
                      >
                        <XCircleIcon className="w-5 h-5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </Modal>

      {/* Bulk Status Change Modal */}
      <Modal
        isOpen={isBulkStatusModalOpen}
        onClose={() => setIsBulkStatusModalOpen(false)}
        title="Change Status"
        size="sm"
        footer={
          <>
            <Button variant="ghost" onClick={() => setIsBulkStatusModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleBulkStatusChange}
              isLoading={bulkActionLoading}
            >
              Update Status
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Change status for {selectedAssetIds.length} selected asset(s)
          </p>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              New Status
            </label>
            <select
              value={bulkStatusValue}
              onChange={(e) => setBulkStatusValue(e.target.value as AssetStatus)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0176D3]/20 focus:border-[#0176D3]"
            >
              {statusOptions.filter((s) => s.value).map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </Modal>
    </PageLayout>
  )
}

export default InventoryList
