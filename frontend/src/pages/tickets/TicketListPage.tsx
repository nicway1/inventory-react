/**
 * TicketListPage Component
 *
 * Main ticket list page with:
 * - Page header with title and actions
 * - Filter bar (status, priority, queue, date range, search)
 * - DataTable with sorting, pagination, row selection
 * - Bulk actions (assign, status change, delete)
 * - Tab integration for opening tickets
 */

import { useState, useCallback, useMemo, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  PlusIcon,
  FunnelIcon,
  ArrowPathIcon,
  UserPlusIcon,
  TrashIcon,
  ArrowsRightLeftIcon,
  XMarkIcon,
  CalendarIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils/cn'
import { PageLayout } from '@/components/templates/PageLayout'
import { DataTable, type ColumnDef } from '@/components/organisms/DataTable'
import { Modal } from '@/components/organisms/Modal'
import { Button } from '@/components/atoms/Button'
import { Badge } from '@/components/atoms/Badge'
import { SearchInput } from '@/components/molecules/SearchInput'
import { Dropdown, DropdownButton, SelectDropdown } from '@/components/molecules/Dropdown'
import { useOpenTab, useUpdateTabTitle } from '@/components/organisms/TabSystem'
import {
  useTickets,
  useQueues,
  useAssignees,
  useDeleteTickets,
  useAssignTickets,
  useUpdateTicketsStatus,
  useTicketsRefresh,
} from '@/hooks/useTickets'
import type {
  Ticket,
  TicketStatus,
  TicketPriority,
  TicketFilters,
} from '@/types/ticket'
import { STATUS_CONFIG, PRIORITY_CONFIG } from '@/types/ticket'

// Status options for filter
const STATUS_OPTIONS = [
  { value: 'all', label: 'All Statuses' },
  { value: 'NEW', label: 'New' },
  { value: 'IN_PROGRESS', label: 'In Progress' },
  { value: 'PROCESSING', label: 'Processing' },
  { value: 'ON_HOLD', label: 'On Hold' },
  { value: 'RESOLVED', label: 'Resolved' },
  { value: 'RESOLVED_DELIVERED', label: 'Resolved - Delivered' },
]

// Priority options for filter
const PRIORITY_OPTIONS = [
  { value: 'all', label: 'All Priorities' },
  { value: 'LOW', label: 'Low' },
  { value: 'MEDIUM', label: 'Medium' },
  { value: 'HIGH', label: 'High' },
  { value: 'URGENT', label: 'Urgent' },
]

// Status badge variant mapping
const getStatusVariant = (status: TicketStatus): 'info' | 'warning' | 'success' | 'neutral' => {
  return STATUS_CONFIG[status]?.variant || 'neutral'
}

// Status label mapping
const getStatusLabel = (status: TicketStatus): string => {
  return STATUS_CONFIG[status]?.label || status
}

// Priority badge variant mapping
const getPriorityVariant = (priority: TicketPriority): 'neutral' | 'info' | 'warning' | 'danger' => {
  return PRIORITY_CONFIG[priority]?.variant || 'neutral'
}

// Priority label mapping
const getPriorityLabel = (priority: TicketPriority): string => {
  return PRIORITY_CONFIG[priority]?.label || priority
}

// Format date for display
const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

// Format date-time for display
const formatDateTime = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

export function TicketListPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const openTab = useOpenTab()
  const updateTabTitle = useUpdateTabTitle()
  const { refreshList } = useTicketsRefresh()

  // Update tab title on mount
  useEffect(() => {
    updateTabTitle('Tickets')
  }, [updateTabTitle])

  // State for filters
  const [filters, setFilters] = useState<TicketFilters>({
    status: (searchParams.get('status') as TicketStatus) || 'all',
    priority: (searchParams.get('priority') as TicketPriority) || 'all',
    queue_id: searchParams.get('queue') ? Number(searchParams.get('queue')) : 'all',
    date_from: searchParams.get('date_from') || '',
    date_to: searchParams.get('date_to') || '',
    search: searchParams.get('search') || '',
  })

  // State for pagination and sorting
  const [page, setPage] = useState(1)
  const [pageSize] = useState(25)
  const [sortBy, setSortBy] = useState('created_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  // State for selection
  const [selectedIds, setSelectedIds] = useState<string[]>([])

  // State for modals
  const [isAssignModalOpen, setIsAssignModalOpen] = useState(false)
  const [isStatusModalOpen, setIsStatusModalOpen] = useState(false)
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false)
  const [isFiltersExpanded, setIsFiltersExpanded] = useState(false)

  // State for bulk action values
  const [selectedAssignee, setSelectedAssignee] = useState<string>('')
  const [selectedStatus, setSelectedStatus] = useState<string>('')

  // Fetch data
  const { data: ticketsData, isLoading, isFetching } = useTickets({
    page,
    per_page: pageSize,
    sort_by: sortBy,
    sort_order: sortOrder,
    ...filters,
  })

  const { data: queues = [] } = useQueues()
  const { data: assignees = [] } = useAssignees()

  // Mutations
  const deleteTicketsMutation = useDeleteTickets()
  const assignTicketsMutation = useAssignTickets()
  const updateStatusMutation = useUpdateTicketsStatus()

  // Queue options for filter
  const queueOptions = useMemo(() => [
    { value: 'all', label: 'All Queues' },
    ...queues.map((q) => ({ value: String(q.id), label: q.name })),
  ], [queues])

  // Assignee options for modal
  const assigneeOptions = useMemo(() => [
    { value: '', label: 'Select Assignee...' },
    ...assignees.map((a) => ({ value: String(a.id), label: a.full_name || `${a.first_name} ${a.last_name}` })),
  ], [assignees])

  // Handle filter changes
  const handleFilterChange = useCallback((key: keyof TicketFilters, value: string | number) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
    setPage(1) // Reset to first page on filter change

    // Update URL params
    const newParams = new URLSearchParams(searchParams)
    if (value && value !== 'all' && value !== '') {
      newParams.set(key, String(value))
    } else {
      newParams.delete(key)
    }
    setSearchParams(newParams)
  }, [searchParams, setSearchParams])

  // Handle search
  const handleSearch = useCallback((value: string) => {
    handleFilterChange('search', value)
  }, [handleFilterChange])

  // Handle sort
  const handleSort = useCallback((column: string) => {
    if (sortBy === column) {
      setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortBy(column)
      setSortOrder('desc')
    }
    setPage(1)
  }, [sortBy])

  // Handle row click - open ticket in new tab
  const handleRowClick = useCallback((ticket: Ticket) => {
    const ticketLabel = ticket.display_id || `T-${ticket.id}`
    openTab(`/tickets/${ticket.id}`, `Ticket ${ticketLabel}`, 'ticket')
  }, [openTab])

  // Handle page change
  const handlePageChange = useCallback((newPage: number) => {
    setPage(newPage)
    setSelectedIds([]) // Clear selection on page change
  }, [])

  // Clear all filters
  const clearFilters = useCallback(() => {
    setFilters({
      status: 'all',
      priority: 'all',
      queue_id: 'all',
      date_from: '',
      date_to: '',
      search: '',
    })
    setSearchParams(new URLSearchParams())
    setPage(1)
  }, [setSearchParams])

  // Handle bulk assign
  const handleBulkAssign = useCallback(async () => {
    if (!selectedAssignee || selectedIds.length === 0) return

    try {
      await assignTicketsMutation.mutateAsync({
        ticketIds: selectedIds.map(Number),
        assigneeId: Number(selectedAssignee),
      })
      setIsAssignModalOpen(false)
      setSelectedIds([])
      setSelectedAssignee('')
    } catch (error) {
      console.error('Failed to assign tickets:', error)
    }
  }, [selectedAssignee, selectedIds, assignTicketsMutation])

  // Handle bulk status change
  const handleBulkStatusChange = useCallback(async () => {
    if (!selectedStatus || selectedIds.length === 0) return

    try {
      await updateStatusMutation.mutateAsync({
        ticketIds: selectedIds.map(Number),
        status: selectedStatus,
      })
      setIsStatusModalOpen(false)
      setSelectedIds([])
      setSelectedStatus('')
    } catch (error) {
      console.error('Failed to update status:', error)
    }
  }, [selectedStatus, selectedIds, updateStatusMutation])

  // Handle bulk delete
  const handleBulkDelete = useCallback(async () => {
    if (selectedIds.length === 0) return

    try {
      await deleteTicketsMutation.mutateAsync(selectedIds.map(Number))
      setIsDeleteModalOpen(false)
      setSelectedIds([])
    } catch (error) {
      console.error('Failed to delete tickets:', error)
    }
  }, [selectedIds, deleteTicketsMutation])

  // Table columns
  const columns: ColumnDef<Ticket>[] = useMemo(() => [
    {
      id: 'display_id',
      header: 'ID',
      accessorKey: 'display_id',
      sortable: true,
      width: '100px',
      cell: (row) => (
        <span className="font-mono text-sm text-[#0176D3] font-medium">
          {row.display_id || `T-${row.id}`}
        </span>
      ),
    },
    {
      id: 'subject',
      header: 'Subject',
      accessorKey: 'subject',
      sortable: true,
      minWidth: '200px',
      cell: (row) => (
        <div className="max-w-md">
          <div className="font-medium text-gray-900 truncate">{row.subject}</div>
          {row.customer_name && (
            <div className="text-xs text-gray-500 truncate">{row.customer_name}</div>
          )}
        </div>
      ),
    },
    {
      id: 'status',
      header: 'Status',
      accessorKey: 'status',
      sortable: true,
      width: '130px',
      cell: (row) => (
        <Badge variant={getStatusVariant(row.status)} size="sm" dot>
          {row.custom_status || getStatusLabel(row.status)}
        </Badge>
      ),
    },
    {
      id: 'priority',
      header: 'Priority',
      accessorKey: 'priority',
      sortable: true,
      width: '100px',
      cell: (row) => (
        <Badge variant={getPriorityVariant(row.priority)} size="sm">
          {getPriorityLabel(row.priority)}
        </Badge>
      ),
    },
    {
      id: 'queue_name',
      header: 'Queue',
      accessorKey: 'queue_name',
      sortable: true,
      width: '150px',
      cell: (row) => (
        <span className="text-sm text-gray-600">{row.queue_name || '-'}</span>
      ),
    },
    {
      id: 'assigned_to_name',
      header: 'Assignee',
      accessorKey: 'assigned_to_name',
      sortable: true,
      width: '150px',
      cell: (row) => (
        <span className="text-sm text-gray-600">{row.assigned_to_name || 'Unassigned'}</span>
      ),
    },
    {
      id: 'created_at',
      header: 'Created',
      accessorKey: 'created_at',
      sortable: true,
      width: '130px',
      cell: (row) => (
        <span className="text-sm text-gray-500">{formatDateTime(row.created_at)}</span>
      ),
    },
    {
      id: 'updated_at',
      header: 'Updated',
      accessorKey: 'updated_at',
      sortable: true,
      width: '130px',
      cell: (row) => (
        <span className="text-sm text-gray-500">
          {row.updated_at ? formatDateTime(row.updated_at) : '-'}
        </span>
      ),
    },
  ], [])

  // Check if any filters are active
  const hasActiveFilters = useMemo(() => {
    return (
      (filters.status && filters.status !== 'all') ||
      (filters.priority && filters.priority !== 'all') ||
      (filters.queue_id && filters.queue_id !== 'all') ||
      filters.date_from ||
      filters.date_to ||
      filters.search
    )
  }, [filters])

  // Page actions
  const pageActions = (
    <>
      <Button
        variant="ghost"
        size="sm"
        leftIcon={<ArrowPathIcon className="w-4 h-4" />}
        onClick={refreshList}
        disabled={isFetching}
      >
        Refresh
      </Button>
      <Button
        variant="primary"
        size="sm"
        leftIcon={<PlusIcon className="w-4 h-4" />}
        onClick={() => openTab('/tickets/new', 'New Ticket', 'ticket')}
      >
        New Ticket
      </Button>
    </>
  )

  return (
    <PageLayout
      title="Tickets"
      subtitle="Manage service and support tickets"
      breadcrumbs={[{ label: 'Tickets' }]}
      actions={pageActions}
    >
      <div className="space-y-4">
        {/* Filter Bar */}
        <div className="bg-white dark:bg-gray-900 rounded border border-[#DDDBDA] dark:border-gray-700 shadow-sm">
          {/* Main Filter Row */}
          <div className="p-4 flex flex-wrap items-center gap-3">
            {/* Search */}
            <div className="flex-1 min-w-[200px] max-w-md">
              <SearchInput
                value={filters.search}
                onChange={(value) => handleFilterChange('search', value)}
                placeholder="Search tickets..."
                size="sm"
              />
            </div>

            {/* Status Filter */}
            <SelectDropdown
              value={filters.status as string || 'all'}
              onChange={(value) => handleFilterChange('status', value)}
              options={STATUS_OPTIONS}
              size="sm"
              width="sm"
            />

            {/* Priority Filter */}
            <SelectDropdown
              value={filters.priority as string || 'all'}
              onChange={(value) => handleFilterChange('priority', value)}
              options={PRIORITY_OPTIONS}
              size="sm"
              width="sm"
            />

            {/* Queue Filter */}
            <SelectDropdown
              value={String(filters.queue_id) || 'all'}
              onChange={(value) => handleFilterChange('queue_id', value === 'all' ? 'all' : Number(value))}
              options={queueOptions}
              size="sm"
              width="md"
            />

            {/* Toggle More Filters */}
            <Button
              variant={isFiltersExpanded ? 'secondary' : 'ghost'}
              size="sm"
              leftIcon={<FunnelIcon className="w-4 h-4" />}
              onClick={() => setIsFiltersExpanded(!isFiltersExpanded)}
            >
              {isFiltersExpanded ? 'Less' : 'More'}
            </Button>

            {/* Clear Filters */}
            {hasActiveFilters && (
              <Button
                variant="ghost"
                size="sm"
                leftIcon={<XMarkIcon className="w-4 h-4" />}
                onClick={clearFilters}
              >
                Clear
              </Button>
            )}
          </div>

          {/* Expanded Filters Row */}
          {isFiltersExpanded && (
            <div className="px-4 pb-4 pt-0 flex flex-wrap items-center gap-3 border-t border-[#DDDBDA] dark:border-gray-700 mt-0 pt-4">
              {/* Date From */}
              <div className="flex items-center gap-2">
                <label className="text-sm text-gray-600 dark:text-gray-400 whitespace-nowrap">
                  From:
                </label>
                <input
                  type="date"
                  value={filters.date_from || ''}
                  onChange={(e) => handleFilterChange('date_from', e.target.value)}
                  className={cn(
                    'px-3 py-1.5 text-sm border rounded',
                    'border-[#DDDBDA] dark:border-gray-600',
                    'bg-white dark:bg-gray-800',
                    'text-gray-900 dark:text-gray-100',
                    'focus:outline-none focus:ring-2 focus:ring-[#0176D3]/20 focus:border-[#0176D3]'
                  )}
                />
              </div>

              {/* Date To */}
              <div className="flex items-center gap-2">
                <label className="text-sm text-gray-600 dark:text-gray-400 whitespace-nowrap">
                  To:
                </label>
                <input
                  type="date"
                  value={filters.date_to || ''}
                  onChange={(e) => handleFilterChange('date_to', e.target.value)}
                  className={cn(
                    'px-3 py-1.5 text-sm border rounded',
                    'border-[#DDDBDA] dark:border-gray-600',
                    'bg-white dark:bg-gray-800',
                    'text-gray-900 dark:text-gray-100',
                    'focus:outline-none focus:ring-2 focus:ring-[#0176D3]/20 focus:border-[#0176D3]'
                  )}
                />
              </div>
            </div>
          )}
        </div>

        {/* Bulk Actions Bar */}
        {selectedIds.length > 0 && (
          <div className="bg-[#0176D3]/10 dark:bg-[#0176D3]/20 rounded border border-[#0176D3]/30 p-3 flex items-center justify-between">
            <span className="text-sm font-medium text-[#0176D3] dark:text-[#1B96FF]">
              {selectedIds.length} ticket{selectedIds.length !== 1 ? 's' : ''} selected
            </span>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                leftIcon={<UserPlusIcon className="w-4 h-4" />}
                onClick={() => setIsAssignModalOpen(true)}
              >
                Assign
              </Button>
              <Button
                variant="ghost"
                size="sm"
                leftIcon={<ArrowsRightLeftIcon className="w-4 h-4" />}
                onClick={() => setIsStatusModalOpen(true)}
              >
                Change Status
              </Button>
              <Button
                variant="danger"
                size="sm"
                leftIcon={<TrashIcon className="w-4 h-4" />}
                onClick={() => setIsDeleteModalOpen(true)}
              >
                Delete
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedIds([])}
              >
                Cancel
              </Button>
            </div>
          </div>
        )}

        {/* Data Table */}
        <DataTable
          data={ticketsData?.data || []}
          columns={columns}
          isLoading={isLoading}
          emptyMessage="No tickets found"
          getRowId={(row) => String(row.id)}
          onRowClick={handleRowClick}
          selection={{
            selected: selectedIds,
            onSelect: setSelectedIds,
          }}
          sorting={{
            sortBy,
            sortOrder,
            onSort: handleSort,
          }}
          pagination={{
            page,
            pageSize,
            total: ticketsData?.meta?.pagination?.total || 0,
            onPageChange: handlePageChange,
          }}
        />

        {/* Assign Modal */}
        <Modal
          isOpen={isAssignModalOpen}
          onClose={() => setIsAssignModalOpen(false)}
          title="Assign Tickets"
          size="sm"
          footer={
            <>
              <Button
                variant="ghost"
                onClick={() => setIsAssignModalOpen(false)}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleBulkAssign}
                isLoading={assignTicketsMutation.isPending}
                disabled={!selectedAssignee}
              >
                Assign
              </Button>
            </>
          }
        >
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              Assign {selectedIds.length} ticket{selectedIds.length !== 1 ? 's' : ''} to:
            </p>
            <select
              value={selectedAssignee}
              onChange={(e) => setSelectedAssignee(e.target.value)}
              className={cn(
                'w-full px-3 py-2 text-sm border rounded',
                'border-[#DDDBDA] dark:border-gray-600',
                'bg-white dark:bg-gray-800',
                'text-gray-900 dark:text-gray-100',
                'focus:outline-none focus:ring-2 focus:ring-[#0176D3]/20 focus:border-[#0176D3]'
              )}
            >
              {assigneeOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </Modal>

        {/* Status Modal */}
        <Modal
          isOpen={isStatusModalOpen}
          onClose={() => setIsStatusModalOpen(false)}
          title="Change Status"
          size="sm"
          footer={
            <>
              <Button
                variant="ghost"
                onClick={() => setIsStatusModalOpen(false)}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleBulkStatusChange}
                isLoading={updateStatusMutation.isPending}
                disabled={!selectedStatus}
              >
                Update Status
              </Button>
            </>
          }
        >
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              Change status of {selectedIds.length} ticket{selectedIds.length !== 1 ? 's' : ''} to:
            </p>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className={cn(
                'w-full px-3 py-2 text-sm border rounded',
                'border-[#DDDBDA] dark:border-gray-600',
                'bg-white dark:bg-gray-800',
                'text-gray-900 dark:text-gray-100',
                'focus:outline-none focus:ring-2 focus:ring-[#0176D3]/20 focus:border-[#0176D3]'
              )}
            >
              <option value="">Select Status...</option>
              <option value="NEW">New</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="PROCESSING">Processing</option>
              <option value="ON_HOLD">On Hold</option>
              <option value="RESOLVED">Resolved</option>
              <option value="RESOLVED_DELIVERED">Resolved - Delivered</option>
            </select>
          </div>
        </Modal>

        {/* Delete Confirmation Modal */}
        <Modal
          isOpen={isDeleteModalOpen}
          onClose={() => setIsDeleteModalOpen(false)}
          title="Delete Tickets"
          size="sm"
          footer={
            <>
              <Button
                variant="ghost"
                onClick={() => setIsDeleteModalOpen(false)}
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                onClick={handleBulkDelete}
                isLoading={deleteTicketsMutation.isPending}
              >
                Delete
              </Button>
            </>
          }
        >
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              Are you sure you want to delete {selectedIds.length} ticket{selectedIds.length !== 1 ? 's' : ''}?
              This action cannot be undone.
            </p>
          </div>
        </Modal>
      </div>
    </PageLayout>
  )
}

export default TicketListPage
