/**
 * CustomerListPage Component
 *
 * Customer list page with search, filters, sorting, and pagination.
 * Matches Flask TrueLog customer_users.html design.
 */

import { useState, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  PlusIcon,
  FunnelIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils/cn'
import { PageLayout } from '@/components/templates/PageLayout'
import { Button } from '@/components/atoms/Button'
import { Badge } from '@/components/atoms/Badge'
import { SearchInput } from '@/components/molecules/SearchInput'
import { Card } from '@/components/molecules/Card'
import { DataTable, type ColumnDef } from '@/components/organisms/DataTable'
import { NoDataAvailable, NoSearchResults } from '@/components/organisms/EmptyState'
import { useCustomers, useCompanies, useCustomerRefresh } from '@/hooks/useCustomers'
import { useOpenTab } from '@/components/organisms/TabSystem'
import type { CustomerListItem, CustomerListParams, Country } from '@/types/customer'
import { COUNTRY_OPTIONS, COUNTRY_COLORS } from '@/types/customer'
import { CustomerModal } from './CustomerModal'

export function CustomerListPage() {
  const navigate = useNavigate()
  const openTab = useOpenTab()
  const { refreshList } = useCustomerRefresh()

  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingCustomer, setEditingCustomer] = useState<CustomerListItem | null>(null)

  // Filter state
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCountry, setSelectedCountry] = useState<Country | ''>('')
  const [selectedCompanyId, setSelectedCompanyId] = useState<number | ''>('')

  // Pagination and sorting state
  const [page, setPage] = useState(1)
  const [pageSize] = useState(25)
  const [sortBy, setSortBy] = useState('name')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')

  // Query params
  const queryParams: CustomerListParams = useMemo(
    () => ({
      page,
      per_page: pageSize,
      sort_by: sortBy,
      sort_order: sortOrder,
      search: searchQuery || undefined,
      country: selectedCountry || undefined,
      company_id: selectedCompanyId || undefined,
    }),
    [page, pageSize, sortBy, sortOrder, searchQuery, selectedCountry, selectedCompanyId]
  )

  // Fetch customers
  const {
    data: customersData,
    isLoading,
    isError,
    refetch,
  } = useCustomers(queryParams)

  // Fetch companies for filter
  const { data: companies = [] } = useCompanies()

  // Handle search
  const handleSearch = useCallback((value: string) => {
    setSearchQuery(value)
    setPage(1) // Reset to first page on search
  }, [])

  // Handle sort
  const handleSort = useCallback((column: string) => {
    if (sortBy === column) {
      setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortBy(column)
      setSortOrder('asc')
    }
    setPage(1)
  }, [sortBy])

  // Handle row click
  const handleRowClick = useCallback(
    (customer: CustomerListItem) => {
      openTab(`/customers/${customer.id}`, customer.name, 'customer')
    },
    [openTab]
  )

  // Handle add customer
  const handleAddCustomer = useCallback(() => {
    setEditingCustomer(null)
    setIsModalOpen(true)
  }, [])

  // Handle modal close
  const handleModalClose = useCallback(() => {
    setIsModalOpen(false)
    setEditingCustomer(null)
  }, [])

  // Handle modal success
  const handleModalSuccess = useCallback(() => {
    setIsModalOpen(false)
    setEditingCustomer(null)
    refreshList()
  }, [refreshList])

  // Clear filters
  const handleClearFilters = useCallback(() => {
    setSearchQuery('')
    setSelectedCountry('')
    setSelectedCompanyId('')
    setPage(1)
  }, [])

  // Check if filters are active
  const hasActiveFilters = searchQuery || selectedCountry || selectedCompanyId

  // Table columns
  const columns: ColumnDef<CustomerListItem>[] = useMemo(
    () => [
      {
        id: 'name',
        header: 'Name',
        accessorKey: 'name',
        sortable: true,
        minWidth: '150px',
        cell: (row) => (
          <div className="font-medium text-gray-900 dark:text-white">
            {row.name}
          </div>
        ),
      },
      {
        id: 'company',
        header: 'Company',
        sortable: true,
        minWidth: '150px',
        cell: (row) => (
          <div className="text-sm text-gray-600 dark:text-gray-400">
            {row.company?.name || (
              <span className="text-gray-400 italic">Not Assigned</span>
            )}
          </div>
        ),
      },
      {
        id: 'country',
        header: 'Country',
        sortable: true,
        minWidth: '120px',
        cell: (row) => {
          if (!row.country) {
            return <span className="text-gray-400 text-sm">Not Set</span>
          }
          const colors = COUNTRY_COLORS[row.country] || COUNTRY_COLORS.OTHER
          return (
            <span
              className={cn(
                'px-2 py-1 text-xs font-medium rounded-full',
                colors.bg,
                colors.text
              )}
            >
              {row.country}
            </span>
          )
        },
      },
      {
        id: 'contact_number',
        header: 'Phone',
        accessorKey: 'contact_number',
        sortable: true,
        minWidth: '120px',
        cell: (row) => (
          <div className="text-sm text-gray-600 dark:text-gray-400 truncate max-w-[120px]">
            {row.contact_number || '-'}
          </div>
        ),
      },
      {
        id: 'email',
        header: 'Email',
        accessorKey: 'email',
        sortable: true,
        minWidth: '180px',
        cell: (row) => (
          <div className="text-sm text-gray-600 dark:text-gray-400 truncate max-w-[180px]">
            {row.email || '-'}
          </div>
        ),
      },
      {
        id: 'address',
        header: 'Address',
        accessorKey: 'address',
        minWidth: '200px',
        cell: (row) => (
          <div className="text-sm text-gray-600 dark:text-gray-400 truncate max-w-[200px]">
            {row.address || '-'}
          </div>
        ),
      },
      {
        id: 'assets_count',
        header: 'Assets',
        sortable: true,
        align: 'center',
        minWidth: '80px',
        cell: (row) => (
          <Badge variant="success" size="sm">
            {row.assets_count}
          </Badge>
        ),
      },
      {
        id: 'tickets_count',
        header: 'Tickets',
        sortable: true,
        align: 'center',
        minWidth: '80px',
        cell: (row) => (
          <Badge variant="info" size="sm">
            {row.tickets_count}
          </Badge>
        ),
      },
    ],
    []
  )

  // Render content
  const renderContent = () => {
    if (isError) {
      return (
        <Card>
          <div className="p-8 text-center">
            <p className="text-red-600 dark:text-red-400">
              Failed to load customers. Please try again.
            </p>
            <Button
              variant="secondary"
              size="sm"
              className="mt-4"
              onClick={() => refetch()}
            >
              Retry
            </Button>
          </div>
        </Card>
      )
    }

    if (!isLoading && customersData?.data.length === 0) {
      if (hasActiveFilters) {
        return (
          <Card>
            <NoSearchResults
              query={searchQuery}
              onClear={handleClearFilters}
            />
          </Card>
        )
      }
      return (
        <Card>
          <NoDataAvailable
            entityName="customers"
            onAdd={handleAddCustomer}
          />
        </Card>
      )
    }

    return (
      <DataTable
        data={customersData?.data || []}
        columns={columns}
        isLoading={isLoading}
        onRowClick={handleRowClick}
        getRowId={(row) => String(row.id)}
        emptyMessage="No customers found"
        sorting={{
          sortBy,
          sortOrder,
          onSort: handleSort,
        }}
        pagination={
          customersData
            ? {
                page: customersData.meta.pagination.page,
                pageSize: customersData.meta.pagination.per_page,
                total: customersData.meta.pagination.total_items,
                onPageChange: setPage,
              }
            : undefined
        }
      />
    )
  }

  return (
    <PageLayout
      title="Customers"
      subtitle="Manage customer accounts and contacts"
      breadcrumbs={[{ label: 'Customers' }]}
      actions={
        <Button
          variant="primary"
          leftIcon={<PlusIcon className="w-5 h-5" />}
          onClick={handleAddCustomer}
        >
          Add Customer
        </Button>
      }
    >
      {/* Filter Bar */}
      <Card className="mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Search */}
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5 uppercase tracking-wide">
              Search
            </label>
            <SearchInput
              value={searchQuery}
              onChange={handleSearch}
              placeholder="Search by name..."
              size="sm"
            />
          </div>

          {/* Country Filter */}
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5 uppercase tracking-wide">
              Country
            </label>
            <select
              value={selectedCountry}
              onChange={(e) => {
                setSelectedCountry(e.target.value as Country | '')
                setPage(1)
              }}
              className={cn(
                'w-full h-10 rounded border px-3 text-sm',
                'bg-white dark:bg-gray-800',
                'border-[#DDDBDA] dark:border-gray-600',
                'focus:outline-none focus:ring-2 focus:ring-[#0176D3]/20 focus:border-[#0176D3]'
              )}
            >
              <option value="">All Countries</option>
              {COUNTRY_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          {/* Company Filter */}
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5 uppercase tracking-wide">
              Company
            </label>
            <select
              value={selectedCompanyId}
              onChange={(e) => {
                setSelectedCompanyId(e.target.value ? Number(e.target.value) : '')
                setPage(1)
              }}
              className={cn(
                'w-full h-10 rounded border px-3 text-sm',
                'bg-white dark:bg-gray-800',
                'border-[#DDDBDA] dark:border-gray-600',
                'focus:outline-none focus:ring-2 focus:ring-[#0176D3]/20 focus:border-[#0176D3]'
              )}
            >
              <option value="">All Companies</option>
              {companies.map((company) => (
                <option key={company.id} value={company.id}>
                  {company.name}
                </option>
              ))}
            </select>
          </div>

          {/* Actions */}
          <div className="flex items-end gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => refetch()}
              leftIcon={<ArrowPathIcon className="w-4 h-4" />}
            >
              Refresh
            </Button>
            {hasActiveFilters && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleClearFilters}
                leftIcon={<FunnelIcon className="w-4 h-4" />}
              >
                Clear
              </Button>
            )}
          </div>
        </div>

        {/* Results count */}
        {customersData && (
          <div className="mt-4 pt-4 border-t border-[#DDDBDA] dark:border-gray-700">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Showing{' '}
              <span className="font-semibold">{customersData.data.length}</span> of{' '}
              <span className="font-semibold">{customersData.meta.pagination.total_items}</span> customers
              {hasActiveFilters && (
                <span className="text-blue-600 dark:text-blue-400 ml-1">(filtered)</span>
              )}
            </p>
          </div>
        )}
      </Card>

      {/* Customer Table */}
      {renderContent()}

      {/* Create/Edit Modal */}
      <CustomerModal
        isOpen={isModalOpen}
        onClose={handleModalClose}
        onSuccess={handleModalSuccess}
        customer={editingCustomer}
      />
    </PageLayout>
  )
}

export default CustomerListPage
