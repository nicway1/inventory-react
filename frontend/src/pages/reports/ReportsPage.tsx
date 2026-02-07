/**
 * ReportsPage Component
 *
 * Main reports list page with:
 * - List of available report templates
 * - Category filtering
 * - Search functionality
 * - Report description and metadata
 */

import { useState, useMemo, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  DocumentTextIcon,
  ClockIcon,
  ComputerDesktopIcon,
  ChartPieIcon,
  ChartBarIcon,
  CalendarIcon,
  UsersIcon,
  ArrowPathIcon,
  PlayIcon,
  BookmarkIcon,
  TrashIcon,
} from '@heroicons/react/24/outline'
import { useQuery } from '@tanstack/react-query'
import { cn } from '@/utils/cn'
import { PageLayout } from '@/components/templates/PageLayout'
import { Button } from '@/components/atoms/Button'
import { Badge } from '@/components/atoms/Badge'
import { SearchInput } from '@/components/molecules/SearchInput'
import { Modal } from '@/components/organisms/Modal'
import { reportsService } from '@/services/reports.service'
import type {
  ReportCategory,
  ReportFilters,
  SavedReport,
} from '@/types/reports'

// Icon component mapping
const IconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  'file-text': DocumentTextIcon,
  'clock': ClockIcon,
  'laptop': ComputerDesktopIcon,
  'pie-chart': ChartPieIcon,
  'bar-chart-2': ChartBarIcon,
  'calendar': CalendarIcon,
  'users': UsersIcon,
}

// Category options for filter
const CATEGORY_OPTIONS: Array<{ value: ReportCategory | 'all'; label: string }> = [
  { value: 'all', label: 'All Categories' },
  { value: 'tickets', label: 'Ticket Reports' },
  { value: 'inventory', label: 'Inventory Reports' },
  { value: 'users', label: 'User Reports' },
  { value: 'analytics', label: 'Analytics' },
]

// Category config with colors
const categoryConfig: Record<ReportCategory, { label: string; color: string; bgColor: string }> = {
  tickets: {
    label: 'Tickets',
    color: 'text-purple-700 dark:text-purple-400',
    bgColor: 'bg-purple-100 dark:bg-purple-900/30',
  },
  inventory: {
    label: 'Inventory',
    color: 'text-green-700 dark:text-green-400',
    bgColor: 'bg-green-100 dark:bg-green-900/30',
  },
  users: {
    label: 'Users',
    color: 'text-blue-700 dark:text-blue-400',
    bgColor: 'bg-blue-100 dark:bg-blue-900/30',
  },
  analytics: {
    label: 'Analytics',
    color: 'text-orange-700 dark:text-orange-400',
    bgColor: 'bg-orange-100 dark:bg-orange-900/30',
  },
}

export function ReportsPage() {
  const navigate = useNavigate()

  // State
  const [filters, setFilters] = useState<ReportFilters>({
    category: 'all',
    search: '',
  })
  const [savedReports, setSavedReports] = useState<SavedReport[]>([])
  const [activeTab, setActiveTab] = useState<'templates' | 'saved'>('templates')
  const [deleteModalOpen, setDeleteModalOpen] = useState(false)
  const [reportToDelete, setReportToDelete] = useState<SavedReport | null>(null)

  // Fetch report templates
  const {
    data: templatesData,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['reportTemplates', filters.category === 'all' ? undefined : filters.category],
    queryFn: () =>
      reportsService.getReportTemplates(
        filters.category === 'all' ? undefined : filters.category
      ),
  })

  // Load saved reports on mount
  useEffect(() => {
    setSavedReports(reportsService.getSavedReports())
  }, [])

  // Filter templates by search
  const filteredTemplates = useMemo(() => {
    if (!templatesData?.data) return []
    if (!filters.search) return templatesData.data

    const searchLower = filters.search.toLowerCase()
    return templatesData.data.filter(
      (template) =>
        template.name.toLowerCase().includes(searchLower) ||
        template.description.toLowerCase().includes(searchLower)
    )
  }, [templatesData?.data, filters.search])

  // Filter saved reports by search
  const filteredSavedReports = useMemo(() => {
    if (!filters.search) return savedReports

    const searchLower = filters.search.toLowerCase()
    return savedReports.filter(
      (report) =>
        report.name.toLowerCase().includes(searchLower) ||
        report.template_name.toLowerCase().includes(searchLower)
    )
  }, [savedReports, filters.search])

  // Handle search change
  const handleSearch = useCallback((value: string) => {
    setFilters((prev) => ({ ...prev, search: value }))
  }, [])

  // Handle category change
  const handleCategoryChange = useCallback((category: ReportCategory | 'all') => {
    setFilters((prev) => ({ ...prev, category }))
  }, [])

  // Navigate to generate report
  const handleGenerateReport = useCallback(
    (templateId: string) => {
      navigate(`/reports/generate/${templateId}`)
    },
    [navigate]
  )

  // Run saved report
  const handleRunSavedReport = useCallback(
    (report: SavedReport) => {
      navigate(`/reports/generate/${report.template_id}?savedId=${report.id}`)
    },
    [navigate]
  )

  // Delete saved report
  const handleDeleteSavedReport = useCallback(() => {
    if (reportToDelete) {
      reportsService.deleteSavedReport(reportToDelete.id)
      setSavedReports(reportsService.getSavedReports())
      setDeleteModalOpen(false)
      setReportToDelete(null)
    }
  }, [reportToDelete])

  // Confirm delete
  const confirmDelete = useCallback((report: SavedReport) => {
    setReportToDelete(report)
    setDeleteModalOpen(true)
  }, [])

  // Get icon component for template
  const getTemplateIcon = (iconName: string) => {
    const IconComponent = IconMap[iconName] || DocumentTextIcon
    return IconComponent
  }

  // Page actions
  const pageActions = (
    <>
      <Button
        variant="ghost"
        size="sm"
        leftIcon={<ArrowPathIcon className="w-4 h-4" />}
        onClick={() => refetch()}
        disabled={isLoading}
      >
        Refresh
      </Button>
    </>
  )

  return (
    <PageLayout
      title="Reports"
      subtitle="Generate and manage reports"
      breadcrumbs={[{ label: 'Reports' }]}
      actions={pageActions}
    >
      <div className="space-y-4">
        {/* Filter Bar */}
        <div className="bg-white dark:bg-gray-900 rounded border border-[#DDDBDA] dark:border-gray-700 shadow-sm">
          <div className="p-4 flex flex-wrap items-center gap-3">
            {/* Search */}
            <div className="flex-1 min-w-[200px] max-w-md">
              <SearchInput
                value={filters.search}
                onChange={handleSearch}
                placeholder="Search reports..."
                size="sm"
              />
            </div>

            {/* Category Tabs */}
            <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
              {CATEGORY_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  onClick={() => handleCategoryChange(option.value)}
                  className={cn(
                    'px-3 py-1.5 text-sm font-medium rounded-md transition-all',
                    filters.category === option.value
                      ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                      : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                  )}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-[#DDDBDA] dark:border-gray-700">
          <button
            onClick={() => setActiveTab('templates')}
            className={cn(
              'px-4 py-2 text-sm font-medium border-b-2 transition-all',
              activeTab === 'templates'
                ? 'border-[#0176D3] text-[#0176D3]'
                : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
            )}
          >
            Report Templates ({filteredTemplates.length})
          </button>
          <button
            onClick={() => setActiveTab('saved')}
            className={cn(
              'px-4 py-2 text-sm font-medium border-b-2 transition-all',
              activeTab === 'saved'
                ? 'border-[#0176D3] text-[#0176D3]'
                : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
            )}
          >
            Saved Reports ({filteredSavedReports.length})
          </button>
        </div>

        {/* Content */}
        {activeTab === 'templates' ? (
          /* Report Templates Grid */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {isLoading ? (
              // Loading skeleton
              Array.from({ length: 6 }).map((_, i) => (
                <div
                  key={i}
                  className="bg-white dark:bg-gray-900 rounded-lg border border-[#DDDBDA] dark:border-gray-700 p-5 animate-pulse"
                >
                  <div className="flex items-start gap-4">
                    <div className="w-10 h-10 bg-gray-200 dark:bg-gray-700 rounded-lg" />
                    <div className="flex-1 space-y-2">
                      <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
                      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2" />
                    </div>
                  </div>
                  <div className="mt-4 h-12 bg-gray-200 dark:bg-gray-700 rounded" />
                </div>
              ))
            ) : filteredTemplates.length === 0 ? (
              <div className="col-span-full text-center py-12">
                <DocumentTextIcon className="w-12 h-12 mx-auto text-gray-400" />
                <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-white">
                  No reports found
                </h3>
                <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                  Try adjusting your search or filter criteria.
                </p>
              </div>
            ) : (
              filteredTemplates.map((template) => {
                const IconComponent = getTemplateIcon(template.icon)
                const catConfig = categoryConfig[template.category]

                return (
                  <div
                    key={template.id}
                    className={cn(
                      'bg-white dark:bg-gray-900 rounded-lg border border-[#DDDBDA] dark:border-gray-700',
                      'hover:border-[#0176D3] dark:hover:border-[#1B96FF] transition-all',
                      'group cursor-pointer'
                    )}
                    onClick={() => handleGenerateReport(template.id)}
                  >
                    <div className="p-5">
                      <div className="flex items-start gap-4">
                        {/* Icon */}
                        <div
                          className={cn(
                            'flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center',
                            catConfig.bgColor
                          )}
                        >
                          <IconComponent className={cn('w-5 h-5', catConfig.color)} />
                        </div>

                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          <h3 className="text-base font-semibold text-gray-900 dark:text-white group-hover:text-[#0176D3] dark:group-hover:text-[#1B96FF] transition-colors">
                            {template.name}
                          </h3>
                          <Badge
                            variant="neutral"
                            size="sm"
                            className={cn('mt-1', catConfig.bgColor, catConfig.color)}
                          >
                            {catConfig.label}
                          </Badge>
                        </div>
                      </div>

                      <p className="mt-3 text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                        {template.description}
                      </p>

                      {/* Footer */}
                      <div className="mt-4 pt-4 border-t border-[#DDDBDA] dark:border-gray-700 flex items-center justify-between">
                        <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-500">
                          <span>Formats:</span>
                          {template.output_formats.map((format) => (
                            <span
                              key={format}
                              className="uppercase bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded"
                            >
                              {format}
                            </span>
                          ))}
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="opacity-0 group-hover:opacity-100 transition-opacity"
                          leftIcon={<PlayIcon className="w-4 h-4" />}
                        >
                          Run
                        </Button>
                      </div>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        ) : (
          /* Saved Reports */
          <div className="bg-white dark:bg-gray-900 rounded-lg border border-[#DDDBDA] dark:border-gray-700">
            {filteredSavedReports.length === 0 ? (
              <div className="text-center py-12">
                <BookmarkIcon className="w-12 h-12 mx-auto text-gray-400" />
                <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-white">
                  No saved reports
                </h3>
                <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                  Generate a report and save it for quick access later.
                </p>
                <Button
                  variant="primary"
                  size="sm"
                  className="mt-4"
                  onClick={() => setActiveTab('templates')}
                >
                  Browse Templates
                </Button>
              </div>
            ) : (
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[#DDDBDA] dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
                    <th className="text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider px-4 py-3">
                      Report Name
                    </th>
                    <th className="text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider px-4 py-3">
                      Template
                    </th>
                    <th className="text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider px-4 py-3">
                      Saved
                    </th>
                    <th className="text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider px-4 py-3">
                      Last Run
                    </th>
                    <th className="text-right text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider px-4 py-3">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#DDDBDA] dark:divide-gray-700">
                  {filteredSavedReports.map((report) => (
                    <tr
                      key={report.id}
                      className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                    >
                      <td className="px-4 py-3">
                        <span className="font-medium text-gray-900 dark:text-white">
                          {report.name}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-sm text-gray-600 dark:text-gray-400">
                          {report.template_name}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-sm text-gray-500">
                          {new Date(report.savedAt).toLocaleDateString()}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-sm text-gray-500">
                          {report.lastRun
                            ? new Date(report.lastRun).toLocaleDateString()
                            : 'Never'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            leftIcon={<PlayIcon className="w-4 h-4" />}
                            onClick={() => handleRunSavedReport(report)}
                          >
                            Run
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-red-600 hover:text-red-700"
                            leftIcon={<TrashIcon className="w-4 h-4" />}
                            onClick={() => confirmDelete(report)}
                          >
                            Delete
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={deleteModalOpen}
        onClose={() => setDeleteModalOpen(false)}
        title="Delete Saved Report"
        size="sm"
        footer={
          <>
            <Button variant="ghost" onClick={() => setDeleteModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="danger" onClick={handleDeleteSavedReport}>
              Delete
            </Button>
          </>
        }
      >
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Are you sure you want to delete the saved report "{reportToDelete?.name}"?
          This action cannot be undone.
        </p>
      </Modal>
    </PageLayout>
  )
}

export default ReportsPage
