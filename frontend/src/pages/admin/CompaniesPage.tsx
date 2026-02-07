/**
 * CompaniesPage Component
 *
 * Admin company management page with CRUD operations,
 * search, pagination, and parent company relationships.
 */

import { useState, useCallback, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  PlusIcon,
  MagnifyingGlassIcon,
  PencilIcon,
  TrashIcon,
  BuildingOfficeIcon,
  BuildingOffice2Icon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils/cn'
import { AdminLayout } from '@/components/templates/AdminLayout'
import { DataTable, type ColumnDef } from '@/components/organisms/DataTable'
import { Modal } from '@/components/organisms/Modal'
import { useToast } from '@/components/organisms/Toast'
import {
  useCompanies,
  useCreateCompany,
  useUpdateCompany,
  useDeleteCompany,
} from '@/hooks/useAdmin'
import type { Company, CreateCompanyRequest, UpdateCompanyRequest, CompanyListParams } from '@/types/admin'

// Company form modal
interface CompanyFormModalProps {
  isOpen: boolean
  onClose: () => void
  company?: Company | null
  parentCompanies: Company[]
  onSubmit: (data: CreateCompanyRequest | UpdateCompanyRequest) => void
  isLoading: boolean
}

function CompanyFormModal({
  isOpen,
  onClose,
  company,
  parentCompanies,
  onSubmit,
  isLoading,
}: CompanyFormModalProps) {
  const [formData, setFormData] = useState({
    name: '',
    display_name: '',
    description: '',
    address: '',
    contact_name: '',
    contact_email: '',
    parent_company_id: '' as string | number,
    is_parent_company: false,
  })

  useEffect(() => {
    if (company) {
      setFormData({
        name: company.name,
        display_name: company.display_name || '',
        description: company.description || '',
        address: company.address || '',
        contact_name: company.contact_name || '',
        contact_email: company.contact_email || '',
        parent_company_id: company.parent_company_id || '',
        is_parent_company: company.is_parent_company,
      })
    } else {
      setFormData({
        name: '',
        display_name: '',
        description: '',
        address: '',
        contact_name: '',
        contact_email: '',
        parent_company_id: '',
        is_parent_company: false,
      })
    }
  }, [company, isOpen])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const data: CreateCompanyRequest | UpdateCompanyRequest = {
      name: formData.name,
      display_name: formData.display_name || undefined,
      description: formData.description || undefined,
      address: formData.address || undefined,
      contact_name: formData.contact_name || undefined,
      contact_email: formData.contact_email || undefined,
      parent_company_id: formData.parent_company_id ? Number(formData.parent_company_id) : null,
      is_parent_company: formData.is_parent_company,
    }
    onSubmit(data)
  }

  // Filter out current company from parent options to prevent circular reference
  const availableParentCompanies = parentCompanies.filter(
    (c) => c.id !== company?.id && c.is_parent_company
  )

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={company ? 'Edit Company' : 'Create New Company'}
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
            form="company-form"
            disabled={isLoading}
            className="px-4 py-2 text-sm font-medium text-white bg-[#0176d3] rounded-md hover:bg-[#014486] disabled:opacity-50"
          >
            {isLoading ? 'Saving...' : company ? 'Update Company' : 'Create Company'}
          </button>
        </>
      }
    >
      <form id="company-form" onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Company Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#0176d3] focus:border-transparent dark:bg-gray-800 dark:border-gray-600"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Display Name
            </label>
            <input
              type="text"
              value={formData.display_name}
              onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
              placeholder="Friendly display name"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#0176d3] focus:border-transparent dark:bg-gray-800 dark:border-gray-600"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Description
          </label>
          <textarea
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            rows={2}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#0176d3] focus:border-transparent dark:bg-gray-800 dark:border-gray-600"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Address
          </label>
          <textarea
            value={formData.address}
            onChange={(e) => setFormData({ ...formData, address: e.target.value })}
            rows={2}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#0176d3] focus:border-transparent dark:bg-gray-800 dark:border-gray-600"
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Contact Name
            </label>
            <input
              type="text"
              value={formData.contact_name}
              onChange={(e) => setFormData({ ...formData, contact_name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#0176d3] focus:border-transparent dark:bg-gray-800 dark:border-gray-600"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Contact Email
            </label>
            <input
              type="email"
              value={formData.contact_email}
              onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#0176d3] focus:border-transparent dark:bg-gray-800 dark:border-gray-600"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Parent Company
            </label>
            <select
              value={formData.parent_company_id}
              onChange={(e) => setFormData({ ...formData, parent_company_id: e.target.value })}
              disabled={formData.is_parent_company}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#0176d3] focus:border-transparent dark:bg-gray-800 dark:border-gray-600 disabled:opacity-50"
            >
              <option value="">No Parent (Standalone)</option>
              {availableParentCompanies.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.display_name || c.name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <label className="flex items-center gap-2 cursor-pointer py-2">
              <input
                type="checkbox"
                checked={formData.is_parent_company}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    is_parent_company: e.target.checked,
                    parent_company_id: e.target.checked ? '' : formData.parent_company_id,
                  })
                }
                className="w-4 h-4 text-[#0176d3] border-gray-300 rounded focus:ring-[#0176d3]"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                This is a parent company
              </span>
            </label>
          </div>
        </div>
      </form>
    </Modal>
  )
}

// Delete confirmation modal
interface DeleteConfirmModalProps {
  isOpen: boolean
  onClose: () => void
  company: Company | null
  onConfirm: () => void
  isLoading: boolean
}

function DeleteConfirmModal({
  isOpen,
  onClose,
  company,
  onConfirm,
  isLoading,
}: DeleteConfirmModalProps) {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Delete Company"
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
          Are you sure you want to delete company <strong>{company?.name}</strong>?
        </p>
        <p className="text-sm text-yellow-600 bg-yellow-50 p-3 rounded-md">
          Note: Companies with associated users or child companies cannot be deleted.
          You must reassign or remove those first.
        </p>
      </div>
    </Modal>
  )
}

export function CompaniesPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const toast = useToast()

  // State
  const [page, setPage] = useState(1)
  const [searchTerm, setSearchTerm] = useState('')
  const [showParentOnly, setShowParentOnly] = useState(false)
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState(false)
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null)

  // Query params
  const queryParams: CompanyListParams = {
    page,
    per_page: 20,
    search: searchTerm || undefined,
    parent_only: showParentOnly || undefined,
    sort: 'name',
    order: 'asc',
  }

  // Data fetching
  const { data, isLoading } = useCompanies(queryParams)
  const { data: allCompaniesData } = useCompanies({ per_page: 100 })
  const allCompanies = allCompaniesData?.companies || []

  // Mutations
  const createCompany = useCreateCompany()
  const updateCompany = useUpdateCompany()
  const deleteCompany = useDeleteCompany()

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
    setSelectedCompany(null)
    setIsFormOpen(true)
  }, [])

  const handleOpenEdit = useCallback((company: Company) => {
    setSelectedCompany(company)
    setIsFormOpen(true)
  }, [])

  const handleOpenDelete = useCallback((company: Company) => {
    setSelectedCompany(company)
    setIsDeleteConfirmOpen(true)
  }, [])

  const handleFormSubmit = useCallback(
    async (data: CreateCompanyRequest | UpdateCompanyRequest) => {
      try {
        if (selectedCompany) {
          await updateCompany.mutateAsync({ id: selectedCompany.id, data })
          toast.success('Company updated successfully')
        } else {
          await createCompany.mutateAsync(data as CreateCompanyRequest)
          toast.success('Company created successfully')
        }
        setIsFormOpen(false)
        setSelectedCompany(null)
      } catch (error: unknown) {
        const message = error instanceof Error ? error.message : 'Failed to save company'
        toast.error(message)
      }
    },
    [selectedCompany, updateCompany, createCompany, toast]
  )

  const handleDelete = useCallback(async () => {
    if (!selectedCompany) return
    try {
      await deleteCompany.mutateAsync(selectedCompany.id)
      toast.success('Company deleted successfully')
      setIsDeleteConfirmOpen(false)
      setSelectedCompany(null)
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to delete company'
      toast.error(message)
    }
  }, [selectedCompany, deleteCompany, toast])

  // Table columns
  const columns: ColumnDef<Company>[] = [
    {
      id: 'name',
      header: 'Company Name',
      sortable: true,
      cell: (row) => (
        <div className="flex items-center gap-2">
          {row.is_parent_company ? (
            <BuildingOffice2Icon className="w-5 h-5 text-[#9050e9]" />
          ) : (
            <BuildingOfficeIcon className="w-5 h-5 text-gray-400" />
          )}
          <div>
            <span className="font-medium text-gray-900 dark:text-white">
              {row.display_name || row.name}
            </span>
            {row.display_name && row.display_name !== row.name && (
              <span className="text-xs text-gray-400 ml-2">({row.name})</span>
            )}
          </div>
        </div>
      ),
    },
    {
      id: 'type',
      header: 'Type',
      cell: (row) =>
        row.is_parent_company ? (
          <span className="px-2 py-1 text-xs font-medium bg-purple-100 text-purple-700 rounded dark:bg-purple-900/30 dark:text-purple-400">
            Parent Company
          </span>
        ) : row.parent_company_id ? (
          <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-700 rounded dark:bg-blue-900/30 dark:text-blue-400">
            Subsidiary
          </span>
        ) : (
          <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-700 rounded dark:bg-gray-800 dark:text-gray-400">
            Standalone
          </span>
        ),
    },
    {
      id: 'contact_name',
      header: 'Contact',
      cell: (row) => (
        <div>
          <div className="text-sm text-gray-900 dark:text-white">{row.contact_name || '-'}</div>
          {row.contact_email && (
            <div className="text-xs text-gray-500">{row.contact_email}</div>
          )}
        </div>
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
      title="Company Management"
      subtitle="Manage companies and their relationships"
      actions={
        <button
          onClick={handleOpenCreate}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-[#0176d3] rounded-md hover:bg-[#014486] transition-colors"
        >
          <PlusIcon className="w-4 h-4" />
          Add Company
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
              placeholder="Search by company name..."
              value={searchTerm}
              onChange={(e) => handleSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#0176d3] focus:border-transparent dark:bg-gray-800 dark:border-gray-600"
            />
          </div>

          {/* Parent Only Toggle */}
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={showParentOnly}
              onChange={(e) => {
                setShowParentOnly(e.target.checked)
                setPage(1)
              }}
              className="w-4 h-4 text-[#0176d3] border-gray-300 rounded focus:ring-[#0176d3]"
            />
            <span className="text-sm text-gray-600 dark:text-gray-400">
              Parent Companies Only
            </span>
          </label>
        </div>
      </div>

      {/* Data Table */}
      <DataTable
        data={data?.companies || []}
        columns={columns}
        isLoading={isLoading}
        emptyMessage="No companies found"
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
      <CompanyFormModal
        isOpen={isFormOpen}
        onClose={() => {
          setIsFormOpen(false)
          setSelectedCompany(null)
        }}
        company={selectedCompany}
        parentCompanies={allCompanies}
        onSubmit={handleFormSubmit}
        isLoading={createCompany.isPending || updateCompany.isPending}
      />

      <DeleteConfirmModal
        isOpen={isDeleteConfirmOpen}
        onClose={() => {
          setIsDeleteConfirmOpen(false)
          setSelectedCompany(null)
        }}
        company={selectedCompany}
        onConfirm={handleDelete}
        isLoading={deleteCompany.isPending}
      />
    </AdminLayout>
  )
}

export default CompaniesPage
