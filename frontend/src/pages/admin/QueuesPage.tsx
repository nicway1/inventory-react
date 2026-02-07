/**
 * QueuesPage Component
 *
 * Admin queue management page with CRUD operations,
 * search, pagination, and display order management.
 */

import { useState, useCallback, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  PlusIcon,
  MagnifyingGlassIcon,
  PencilIcon,
  TrashIcon,
  QueueListIcon,
  ArrowsUpDownIcon,
  BellIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils/cn'
import { AdminLayout } from '@/components/templates/AdminLayout'
import { DataTable, type ColumnDef } from '@/components/organisms/DataTable'
import { Modal } from '@/components/organisms/Modal'
import { useToast } from '@/components/organisms/Toast'
import {
  useAdminQueues,
  useCreateQueue,
  useUpdateQueue,
  useDeleteQueue,
} from '@/hooks/useAdmin'
import type { AdminQueue, CreateQueueRequest, UpdateQueueRequest, AdminListParams } from '@/types/admin'

// Queue form modal
interface QueueFormModalProps {
  isOpen: boolean
  onClose: () => void
  queue?: AdminQueue | null
  existingQueues: AdminQueue[]
  onSubmit: (data: CreateQueueRequest | UpdateQueueRequest) => void
  isLoading: boolean
}

function QueueFormModal({
  isOpen,
  onClose,
  queue,
  existingQueues,
  onSubmit,
  isLoading,
}: QueueFormModalProps) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    display_order: 0,
  })

  useEffect(() => {
    if (queue) {
      setFormData({
        name: queue.name,
        description: queue.description || '',
        display_order: queue.display_order,
      })
    } else {
      // Set default display order to be after existing queues
      const maxOrder = existingQueues.reduce(
        (max, q) => Math.max(max, q.display_order),
        0
      )
      setFormData({
        name: '',
        description: '',
        display_order: maxOrder + 1,
      })
    }
  }, [queue, existingQueues, isOpen])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const data: CreateQueueRequest | UpdateQueueRequest = {
      name: formData.name,
      description: formData.description || undefined,
      display_order: formData.display_order,
    }
    onSubmit(data)
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={queue ? 'Edit Queue' : 'Create New Queue'}
      size="md"
      footer={
        <>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            form="queue-form"
            disabled={isLoading}
            className="px-4 py-2 text-sm font-medium text-white bg-[#0176d3] rounded-md hover:bg-[#014486] disabled:opacity-50"
          >
            {isLoading ? 'Saving...' : queue ? 'Update Queue' : 'Create Queue'}
          </button>
        </>
      }
    >
      <form id="queue-form" onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Queue Name <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            required
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            placeholder="e.g., Support, Sales, Technical"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#0176d3] focus:border-transparent dark:bg-gray-800 dark:border-gray-600"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Description
          </label>
          <textarea
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            rows={3}
            placeholder="Brief description of this queue's purpose..."
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#0176d3] focus:border-transparent dark:bg-gray-800 dark:border-gray-600"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Display Order
          </label>
          <input
            type="number"
            min="0"
            value={formData.display_order}
            onChange={(e) =>
              setFormData({ ...formData, display_order: parseInt(e.target.value) || 0 })
            }
            className="w-32 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#0176d3] focus:border-transparent dark:bg-gray-800 dark:border-gray-600"
          />
          <p className="mt-1 text-xs text-gray-500">
            Lower numbers appear first in lists
          </p>
        </div>
      </form>
    </Modal>
  )
}

// Notification settings modal (placeholder for future implementation)
interface NotificationSettingsModalProps {
  isOpen: boolean
  onClose: () => void
  queue: AdminQueue | null
}

function NotificationSettingsModal({
  isOpen,
  onClose,
  queue,
}: NotificationSettingsModalProps) {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Notification Settings - ${queue?.name}`}
      size="lg"
      footer={
        <button
          type="button"
          onClick={onClose}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
        >
          Close
        </button>
      }
    >
      <div className="space-y-4">
        <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <h3 className="font-medium text-gray-900 dark:text-white mb-2">
            Email Notifications
          </h3>
          <div className="space-y-2">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                defaultChecked
                className="w-4 h-4 text-[#0176d3] border-gray-300 rounded focus:ring-[#0176d3]"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Notify on new ticket
              </span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                defaultChecked
                className="w-4 h-4 text-[#0176d3] border-gray-300 rounded focus:ring-[#0176d3]"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Notify on ticket assignment
              </span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                className="w-4 h-4 text-[#0176d3] border-gray-300 rounded focus:ring-[#0176d3]"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Notify on ticket closure
              </span>
            </label>
          </div>
        </div>

        <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <h3 className="font-medium text-gray-900 dark:text-white mb-2">
            Notify Recipients
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
            Add email addresses to receive notifications for this queue.
          </p>
          <input
            type="text"
            placeholder="Enter email addresses (comma separated)"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#0176d3] focus:border-transparent dark:bg-gray-800 dark:border-gray-600"
          />
        </div>

        <p className="text-sm text-gray-500 text-center">
          Full notification settings are managed in the backend.
          Contact your administrator for advanced configuration.
        </p>
      </div>
    </Modal>
  )
}

// Delete confirmation modal
interface DeleteConfirmModalProps {
  isOpen: boolean
  onClose: () => void
  queue: AdminQueue | null
  onConfirm: () => void
  isLoading: boolean
}

function DeleteConfirmModal({
  isOpen,
  onClose,
  queue,
  onConfirm,
  isLoading,
}: DeleteConfirmModalProps) {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Delete Queue"
      size="sm"
      footer={
        <>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isLoading}
            className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 disabled:opacity-50"
          >
            {isLoading ? 'Deleting...' : 'Delete'}
          </button>
        </>
      }
    >
      <div className="text-gray-600 dark:text-gray-400">
        <p className="mb-3">
          Are you sure you want to delete queue <strong>{queue?.name}</strong>?
        </p>
        <p className="text-sm text-yellow-600 bg-yellow-50 p-3 rounded-md">
          Note: Queues with associated tickets cannot be deleted.
          You must reassign those tickets first.
        </p>
      </div>
    </Modal>
  )
}

export function QueuesPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const toast = useToast()

  // State
  const [page, setPage] = useState(1)
  const [searchTerm, setSearchTerm] = useState('')
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false)
  const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState(false)
  const [selectedQueue, setSelectedQueue] = useState<AdminQueue | null>(null)

  // Query params
  const queryParams: AdminListParams = {
    page,
    per_page: 20,
    search: searchTerm || undefined,
    sort: 'display_order',
    order: 'asc',
  }

  // Data fetching
  const { data, isLoading } = useAdminQueues(queryParams)
  const { data: allQueuesData } = useAdminQueues({ per_page: 100, sort: 'display_order', order: 'asc' })
  const allQueues = allQueuesData?.queues || []

  // Mutations
  const createQueue = useCreateQueue()
  const updateQueue = useUpdateQueue()
  const deleteQueue = useDeleteQueue()

  // Check for action param on mount
  useEffect(() => {
    if (searchParams.get('action') === 'create') {
      setIsFormOpen(true)
      searchParams.delete('action')
      setSearchParams(searchParams)
    }
  }, [searchParams, setSearchParams])

  // Handlers
  const handleSearch = useCallback((value: string) => {
    setSearchTerm(value)
    setPage(1)
  }, [])

  const handleOpenCreate = useCallback(() => {
    setSelectedQueue(null)
    setIsFormOpen(true)
  }, [])

  const handleOpenEdit = useCallback((queue: AdminQueue) => {
    setSelectedQueue(queue)
    setIsFormOpen(true)
  }, [])

  const handleOpenNotifications = useCallback((queue: AdminQueue) => {
    setSelectedQueue(queue)
    setIsNotificationsOpen(true)
  }, [])

  const handleOpenDelete = useCallback((queue: AdminQueue) => {
    setSelectedQueue(queue)
    setIsDeleteConfirmOpen(true)
  }, [])

  const handleFormSubmit = useCallback(
    async (data: CreateQueueRequest | UpdateQueueRequest) => {
      try {
        if (selectedQueue) {
          await updateQueue.mutateAsync({ id: selectedQueue.id, data })
          toast.success('Queue updated successfully')
        } else {
          await createQueue.mutateAsync(data as CreateQueueRequest)
          toast.success('Queue created successfully')
        }
        setIsFormOpen(false)
        setSelectedQueue(null)
      } catch (error: unknown) {
        const message = error instanceof Error ? error.message : 'Failed to save queue'
        toast.error(message)
      }
    },
    [selectedQueue, updateQueue, createQueue, toast]
  )

  const handleDelete = useCallback(async () => {
    if (!selectedQueue) return
    try {
      await deleteQueue.mutateAsync(selectedQueue.id)
      toast.success('Queue deleted successfully')
      setIsDeleteConfirmOpen(false)
      setSelectedQueue(null)
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to delete queue'
      toast.error(message)
    }
  }, [selectedQueue, deleteQueue, toast])

  // Table columns
  const columns: ColumnDef<AdminQueue>[] = [
    {
      id: 'display_order',
      header: '#',
      width: '60px',
      cell: (row) => (
        <div className="flex items-center gap-1 text-gray-400">
          <ArrowsUpDownIcon className="w-4 h-4" />
          <span>{row.display_order}</span>
        </div>
      ),
    },
    {
      id: 'name',
      header: 'Queue Name',
      sortable: true,
      cell: (row) => (
        <div className="flex items-center gap-2">
          <QueueListIcon className="w-5 h-5 text-[#9050e9]" />
          <span className="font-medium text-gray-900 dark:text-white">{row.name}</span>
        </div>
      ),
    },
    {
      id: 'description',
      header: 'Description',
      cell: (row) => (
        <span className="text-sm text-gray-500 dark:text-gray-400 line-clamp-2">
          {row.description || '-'}
        </span>
      ),
    },
    {
      id: 'created_at',
      header: 'Created',
      sortable: true,
      cell: (row) => (
        <span className="text-sm text-gray-500">
          {new Date(row.created_at).toLocaleDateString()}
        </span>
      ),
    },
    {
      id: 'actions',
      header: 'Actions',
      align: 'right',
      cell: (row) => (
        <div className="flex items-center justify-end gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation()
              handleOpenNotifications(row)
            }}
            className="p-1.5 text-gray-400 hover:text-[#fe9339] hover:bg-gray-100 rounded transition-colors"
            title="Notification Settings"
          >
            <BellIcon className="w-4 h-4" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation()
              handleOpenEdit(row)
            }}
            className="p-1.5 text-gray-400 hover:text-[#0176d3] hover:bg-gray-100 rounded transition-colors"
            title="Edit"
          >
            <PencilIcon className="w-4 h-4" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation()
              handleOpenDelete(row)
            }}
            className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-gray-100 rounded transition-colors"
            title="Delete"
          >
            <TrashIcon className="w-4 h-4" />
          </button>
        </div>
      ),
    },
  ]

  return (
    <AdminLayout
      title="Queue Management"
      subtitle="Manage ticket queues and their settings"
      actions={
        <button
          onClick={handleOpenCreate}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-[#0176d3] rounded-md hover:bg-[#014486] transition-colors"
        >
          <PlusIcon className="w-4 h-4" />
          Add Queue
        </button>
      }
    >
      {/* Filters */}
      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4 mb-6 shadow-sm">
        <div className="flex flex-col sm:flex-row gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <MagnifyingGlassIcon className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search by queue name..."
              value={searchTerm}
              onChange={(e) => handleSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#0176d3] focus:border-transparent dark:bg-gray-800 dark:border-gray-600"
            />
          </div>

          {/* Info */}
          <div className="flex items-center text-sm text-gray-500">
            <QueueListIcon className="w-4 h-4 mr-1" />
            {data?.meta.total || 0} queues total
          </div>
        </div>
      </div>

      {/* Data Table */}
      <DataTable
        data={data?.queues || []}
        columns={columns}
        isLoading={isLoading}
        emptyMessage="No queues found"
        getRowId={(row) => String(row.id)}
        pagination={
          data?.meta
            ? {
                page: data.meta.page,
                pageSize: data.meta.per_page,
                total: data.meta.total,
                onPageChange: setPage,
              }
            : undefined
        }
      />

      {/* Modals */}
      <QueueFormModal
        isOpen={isFormOpen}
        onClose={() => {
          setIsFormOpen(false)
          setSelectedQueue(null)
        }}
        queue={selectedQueue}
        existingQueues={allQueues}
        onSubmit={handleFormSubmit}
        isLoading={createQueue.isPending || updateQueue.isPending}
      />

      <NotificationSettingsModal
        isOpen={isNotificationsOpen}
        onClose={() => {
          setIsNotificationsOpen(false)
          setSelectedQueue(null)
        }}
        queue={selectedQueue}
      />

      <DeleteConfirmModal
        isOpen={isDeleteConfirmOpen}
        onClose={() => {
          setIsDeleteConfirmOpen(false)
          setSelectedQueue(null)
        }}
        queue={selectedQueue}
        onConfirm={handleDelete}
        isLoading={deleteQueue.isPending}
      />
    </AdminLayout>
  )
}

export default QueuesPage
