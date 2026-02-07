/**
 * UsersPage Component
 *
 * Admin user management page with CRUD operations,
 * search/filter, pagination, and password reset.
 */

import { useState, useCallback, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  PlusIcon,
  MagnifyingGlassIcon,
  PencilIcon,
  TrashIcon,
  KeyIcon,
  UserPlusIcon,
  FunnelIcon,
  XMarkIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils/cn'
import { AdminLayout } from '@/components/templates/AdminLayout'
import { DataTable, type ColumnDef } from '@/components/organisms/DataTable'
import { Modal } from '@/components/organisms/Modal'
import { useToast } from '@/components/organisms/Toast'
import {
  useUsers,
  useCreateUser,
  useUpdateUser,
  useDeleteUser,
  useResetUserPassword,
  useCompanies,
} from '@/hooks/useAdmin'
import type {
  AdminUser,
  AdminUserType,
  CreateUserRequest,
  UpdateUserRequest,
  UserListParams,
} from '@/types/admin'

// User type options
const userTypeOptions: { value: AdminUserType; label: string }[] = [
  { value: 'SUPER_ADMIN', label: 'Super Admin' },
  { value: 'DEVELOPER', label: 'Developer' },
  { value: 'COUNTRY_ADMIN', label: 'Country Admin' },
  { value: 'SUPERVISOR', label: 'Supervisor' },
  { value: 'CLIENT', label: 'Client' },
]

// User type badge component
function UserTypeBadge({ type }: { type: AdminUserType }) {
  const colors: Record<AdminUserType, string> = {
    SUPER_ADMIN: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    DEVELOPER: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
    COUNTRY_ADMIN: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    SUPERVISOR: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    CLIENT: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400',
  }

  return (
    <span className={cn('px-2 py-1 rounded text-xs font-medium', colors[type])}>
      {type.replace('_', ' ')}
    </span>
  )
}

// User form modal
interface UserFormModalProps {
  isOpen: boolean
  onClose: () => void
  user?: AdminUser | null
  companies: { id: number; name: string }[]
  onSubmit: (data: CreateUserRequest | UpdateUserRequest) => void
  isLoading: boolean
}

function UserFormModal({
  isOpen,
  onClose,
  user,
  companies,
  onSubmit,
  isLoading,
}: UserFormModalProps) {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    user_type: 'CLIENT' as AdminUserType,
    company_id: '' as string | number,
    assigned_country: '',
  })

  useEffect(() => {
    if (user) {
      setFormData({
        username: user.username,
        email: user.email,
        password: '',
        user_type: user.user_type,
        company_id: user.company_id || '',
        assigned_country: user.assigned_country || '',
      })
    } else {
      setFormData({
        username: '',
        email: '',
        password: '',
        user_type: 'CLIENT',
        company_id: '',
        assigned_country: '',
      })
    }
  }, [user, isOpen])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const data: CreateUserRequest | UpdateUserRequest = {
      username: formData.username,
      email: formData.email,
      user_type: formData.user_type,
      company_id: formData.company_id ? Number(formData.company_id) : null,
      assigned_country: formData.assigned_country || undefined,
    }
    if (formData.password) {
      (data as CreateUserRequest).password = formData.password
    }
    onSubmit(data)
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={user ? 'Edit User' : 'Create New User'}
      size="lg"
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
            form="user-form"
            disabled={isLoading}
            className="px-4 py-2 text-sm font-medium text-white bg-[#0176d3] rounded-md hover:bg-[#014486] disabled:opacity-50"
          >
            {isLoading ? 'Saving...' : user ? 'Update User' : 'Create User'}
          </button>
        </>
      }
    >
      <form id="user-form" onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Username <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              required
              value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#0176d3] focus:border-transparent dark:bg-gray-800 dark:border-gray-600"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Email <span className="text-red-500">*</span>
            </label>
            <input
              type="email"
              required
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#0176d3] focus:border-transparent dark:bg-gray-800 dark:border-gray-600"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Password {!user && <span className="text-red-500">*</span>}
            {user && <span className="text-gray-400 text-xs">(leave blank to keep current)</span>}
          </label>
          <input
            type="password"
            required={!user}
            value={formData.password}
            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#0176d3] focus:border-transparent dark:bg-gray-800 dark:border-gray-600"
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              User Type <span className="text-red-500">*</span>
            </label>
            <select
              required
              value={formData.user_type}
              onChange={(e) => setFormData({ ...formData, user_type: e.target.value as AdminUserType })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#0176d3] focus:border-transparent dark:bg-gray-800 dark:border-gray-600"
            >
              {userTypeOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Company
            </label>
            <select
              value={formData.company_id}
              onChange={(e) => setFormData({ ...formData, company_id: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#0176d3] focus:border-transparent dark:bg-gray-800 dark:border-gray-600"
            >
              <option value="">No Company</option>
              {companies.map((company) => (
                <option key={company.id} value={company.id}>
                  {company.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Assigned Country
          </label>
          <input
            type="text"
            value={formData.assigned_country}
            onChange={(e) => setFormData({ ...formData, assigned_country: e.target.value })}
            placeholder="e.g., SG, MY, PH"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#0176d3] focus:border-transparent dark:bg-gray-800 dark:border-gray-600"
          />
        </div>
      </form>
    </Modal>
  )
}

// Password reset modal
interface PasswordResetModalProps {
  isOpen: boolean
  onClose: () => void
  user: AdminUser | null
  onSubmit: (password: string) => void
  isLoading: boolean
}

function PasswordResetModal({ isOpen, onClose, user, onSubmit, isLoading }: PasswordResetModalProps) {
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  useEffect(() => {
    if (isOpen) {
      setPassword('')
      setConfirmPassword('')
    }
  }, [isOpen])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (password !== confirmPassword) {
      return
    }
    onSubmit(password)
  }

  const passwordsMatch = password === confirmPassword

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Reset Password for ${user?.username}`}
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
            type="submit"
            form="reset-password-form"
            disabled={isLoading || !passwordsMatch || !password}
            className="px-4 py-2 text-sm font-medium text-white bg-[#0176d3] rounded-md hover:bg-[#014486] disabled:opacity-50"
          >
            {isLoading ? 'Resetting...' : 'Reset Password'}
          </button>
        </>
      }
    >
      <form id="reset-password-form" onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            New Password <span className="text-red-500">*</span>
          </label>
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#0176d3] focus:border-transparent"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Confirm Password <span className="text-red-500">*</span>
          </label>
          <input
            type="password"
            required
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className={cn(
              'w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-[#0176d3] focus:border-transparent',
              confirmPassword && !passwordsMatch ? 'border-red-500' : 'border-gray-300'
            )}
          />
          {confirmPassword && !passwordsMatch && (
            <p className="mt-1 text-xs text-red-500">Passwords do not match</p>
          )}
        </div>
      </form>
    </Modal>
  )
}

// Delete confirmation modal
interface DeleteConfirmModalProps {
  isOpen: boolean
  onClose: () => void
  user: AdminUser | null
  onConfirm: () => void
  isLoading: boolean
}

function DeleteConfirmModal({ isOpen, onClose, user, onConfirm, isLoading }: DeleteConfirmModalProps) {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Deactivate User"
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
            {isLoading ? 'Deactivating...' : 'Deactivate'}
          </button>
        </>
      }
    >
      <p className="text-gray-600 dark:text-gray-400">
        Are you sure you want to deactivate user <strong>{user?.username}</strong>?
        This will prevent them from logging in.
      </p>
    </Modal>
  )
}

export function UsersPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const toast = useToast()

  // State
  const [page, setPage] = useState(1)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterUserType, setFilterUserType] = useState<AdminUserType | ''>('')
  const [showDeleted, setShowDeleted] = useState(false)
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [isPasswordResetOpen, setIsPasswordResetOpen] = useState(false)
  const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState(false)
  const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null)

  // Query params
  const queryParams: UserListParams = {
    page,
    per_page: 20,
    search: searchTerm || undefined,
    user_type: filterUserType || undefined,
    include_deleted: showDeleted,
    sort: 'created_at',
    order: 'desc',
  }

  // Data fetching
  const { data, isLoading, refetch } = useUsers(queryParams)
  const { data: companiesData } = useCompanies({ per_page: 100 })
  const companies = companiesData?.companies || []

  // Mutations
  const createUser = useCreateUser()
  const updateUser = useUpdateUser()
  const deleteUser = useDeleteUser()
  const resetPassword = useResetUserPassword()

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
    setSelectedUser(null)
    setIsFormOpen(true)
  }, [])

  const handleOpenEdit = useCallback((user: AdminUser) => {
    setSelectedUser(user)
    setIsFormOpen(true)
  }, [])

  const handleOpenPasswordReset = useCallback((user: AdminUser) => {
    setSelectedUser(user)
    setIsPasswordResetOpen(true)
  }, [])

  const handleOpenDelete = useCallback((user: AdminUser) => {
    setSelectedUser(user)
    setIsDeleteConfirmOpen(true)
  }, [])

  const handleFormSubmit = useCallback(
    async (data: CreateUserRequest | UpdateUserRequest) => {
      try {
        if (selectedUser) {
          await updateUser.mutateAsync({ id: selectedUser.id, data })
          toast.success('User updated successfully')
        } else {
          await createUser.mutateAsync(data as CreateUserRequest)
          toast.success('User created successfully')
        }
        setIsFormOpen(false)
        setSelectedUser(null)
      } catch (error: unknown) {
        const message = error instanceof Error ? error.message : 'Failed to save user'
        toast.error(message)
      }
    },
    [selectedUser, updateUser, createUser, toast]
  )

  const handlePasswordReset = useCallback(
    async (password: string) => {
      if (!selectedUser) return
      try {
        await resetPassword.mutateAsync({ id: selectedUser.id, password })
        toast.success('Password reset successfully')
        setIsPasswordResetOpen(false)
        setSelectedUser(null)
      } catch (error: unknown) {
        const message = error instanceof Error ? error.message : 'Failed to reset password'
        toast.error(message)
      }
    },
    [selectedUser, resetPassword, toast]
  )

  const handleDelete = useCallback(async () => {
    if (!selectedUser) return
    try {
      await deleteUser.mutateAsync({ id: selectedUser.id })
      toast.success('User deactivated successfully')
      setIsDeleteConfirmOpen(false)
      setSelectedUser(null)
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to deactivate user'
      toast.error(message)
    }
  }, [selectedUser, deleteUser, toast])

  // Table columns
  const columns: ColumnDef<AdminUser>[] = [
    {
      id: 'username',
      header: 'Username',
      accessorKey: 'username',
      sortable: true,
      cell: (row) => (
        <div className="flex items-center gap-2">
          <span className="font-medium text-gray-900 dark:text-white">{row.username}</span>
          {row.is_deleted && (
            <span className="px-1.5 py-0.5 text-xs bg-red-100 text-red-600 rounded">Inactive</span>
          )}
        </div>
      ),
    },
    {
      id: 'email',
      header: 'Email',
      accessorKey: 'email',
      sortable: true,
    },
    {
      id: 'user_type',
      header: 'Role',
      cell: (row) => <UserTypeBadge type={row.user_type} />,
    },
    {
      id: 'company_name',
      header: 'Company',
      cell: (row) => row.company_name || '-',
    },
    {
      id: 'status',
      header: 'Status',
      cell: (row) => (
        <div className="flex items-center gap-1.5">
          {row.is_deleted ? (
            <>
              <XCircleIcon className="w-4 h-4 text-red-500" />
              <span className="text-red-600 text-sm">Inactive</span>
            </>
          ) : (
            <>
              <CheckCircleIcon className="w-4 h-4 text-green-500" />
              <span className="text-green-600 text-sm">Active</span>
            </>
          )}
        </div>
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
              handleOpenPasswordReset(row)
            }}
            className="p-1.5 text-gray-400 hover:text-[#fe9339] hover:bg-gray-100 rounded transition-colors"
            title="Reset Password"
          >
            <KeyIcon className="w-4 h-4" />
          </button>
          {!row.is_deleted && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                handleOpenDelete(row)
              }}
              className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-gray-100 rounded transition-colors"
              title="Deactivate"
            >
              <TrashIcon className="w-4 h-4" />
            </button>
          )}
        </div>
      ),
    },
  ]

  return (
    <AdminLayout
      title="User Management"
      subtitle="Manage system users and their permissions"
      actions={
        <button
          onClick={handleOpenCreate}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-[#0176d3] rounded-md hover:bg-[#014486] transition-colors"
        >
          <UserPlusIcon className="w-4 h-4" />
          Add User
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
              placeholder="Search by username or email..."
              value={searchTerm}
              onChange={(e) => handleSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#0176d3] focus:border-transparent dark:bg-gray-800 dark:border-gray-600"
            />
          </div>

          {/* User Type Filter */}
          <div className="flex items-center gap-2">
            <FunnelIcon className="w-5 h-5 text-gray-400" />
            <select
              value={filterUserType}
              onChange={(e) => {
                setFilterUserType(e.target.value as AdminUserType | '')
                setPage(1)
              }}
              className="px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#0176d3] focus:border-transparent dark:bg-gray-800 dark:border-gray-600"
            >
              <option value="">All Roles</option>
              {userTypeOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Show Deleted Toggle */}
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={showDeleted}
              onChange={(e) => {
                setShowDeleted(e.target.checked)
                setPage(1)
              }}
              className="w-4 h-4 text-[#0176d3] border-gray-300 rounded focus:ring-[#0176d3]"
            />
            <span className="text-sm text-gray-600 dark:text-gray-400">Show Inactive</span>
          </label>
        </div>
      </div>

      {/* Data Table */}
      <DataTable
        data={data?.users || []}
        columns={columns}
        isLoading={isLoading}
        emptyMessage="No users found"
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
      <UserFormModal
        isOpen={isFormOpen}
        onClose={() => {
          setIsFormOpen(false)
          setSelectedUser(null)
        }}
        user={selectedUser}
        companies={companies}
        onSubmit={handleFormSubmit}
        isLoading={createUser.isPending || updateUser.isPending}
      />

      <PasswordResetModal
        isOpen={isPasswordResetOpen}
        onClose={() => {
          setIsPasswordResetOpen(false)
          setSelectedUser(null)
        }}
        user={selectedUser}
        onSubmit={handlePasswordReset}
        isLoading={resetPassword.isPending}
      />

      <DeleteConfirmModal
        isOpen={isDeleteConfirmOpen}
        onClose={() => {
          setIsDeleteConfirmOpen(false)
          setSelectedUser(null)
        }}
        user={selectedUser}
        onConfirm={handleDelete}
        isLoading={deleteUser.isPending}
      />
    </AdminLayout>
  )
}

export default UsersPage
