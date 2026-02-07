/**
 * GenerateReportPage Component
 *
 * Report generation page with:
 * - Report type display and configuration
 * - Dynamic parameter inputs (date range, filters, etc.)
 * - Generate button with loading state
 * - Download options (PDF, CSV, Excel)
 * - Report preview/viewer integration
 */

import { useState, useEffect, useMemo, useCallback } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import {
  ArrowLeftIcon,
  ArrowPathIcon,
  ArrowDownTrayIcon,
  DocumentTextIcon,
  BookmarkIcon,
  PrinterIcon,
  ChartBarIcon,
  TableCellsIcon,
} from '@heroicons/react/24/outline'
import { useQuery, useMutation } from '@tanstack/react-query'
import { cn } from '@/utils/cn'
import { PageLayout } from '@/components/templates/PageLayout'
import { Button } from '@/components/atoms/Button'
import { Modal } from '@/components/organisms/Modal'
import { reportsService } from '@/services/reports.service'
import { ReportViewer } from './ReportViewer'
import type {
  ReportParameter,
  ReportResult,
  ReportFormat,
  GenerateReportRequest,
  SavedReport,
} from '@/types/reports'

// Default date range (last 30 days)
const getDefaultDateRange = () => {
  const today = new Date()
  const thirtyDaysAgo = new Date(today)
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)

  return {
    from: thirtyDaysAgo.toISOString().split('T')[0],
    to: today.toISOString().split('T')[0],
  }
}

export function GenerateReportPage() {
  const { templateId } = useParams<{ templateId: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  // State
  const [parameters, setParameters] = useState<Record<string, string | number | string[] | null>>({})
  const [selectedFormat, setSelectedFormat] = useState<ReportFormat>('json')
  const [reportResult, setReportResult] = useState<ReportResult | null>(null)
  const [viewMode, setViewMode] = useState<'table' | 'chart'>('table')
  const [saveModalOpen, setSaveModalOpen] = useState(false)
  const [reportName, setReportName] = useState('')

  // Fetch template
  const { data: template, isLoading: templateLoading } = useQuery({
    queryKey: ['reportTemplate', templateId],
    queryFn: () => reportsService.getReportTemplate(templateId || ''),
    enabled: !!templateId,
  })

  // Generate report mutation
  const generateMutation = useMutation({
    mutationFn: (request: GenerateReportRequest) => reportsService.generateReport(request),
    onSuccess: (result) => {
      setReportResult(result)
    },
  })

  // Initialize parameters from template defaults or saved report
  useEffect(() => {
    if (template) {
      const defaultParams: Record<string, string | number | string[] | null> = {}
      const dateRange = getDefaultDateRange()

      template.parameters.forEach((param) => {
        if (param.default !== undefined) {
          defaultParams[param.key] = param.default as string | number | string[]
        } else if (param.type === 'date') {
          // Set default dates
          if (param.key === 'date_from') {
            defaultParams[param.key] = dateRange.from
          } else if (param.key === 'date_to') {
            defaultParams[param.key] = dateRange.to
          }
        } else if (param.type === 'multi_select') {
          defaultParams[param.key] = []
        } else {
          defaultParams[param.key] = null
        }
      })

      // Load from saved report if specified
      const savedId = searchParams.get('savedId')
      if (savedId) {
        const savedReport = reportsService.getSavedReport(savedId)
        if (savedReport) {
          setParameters({ ...defaultParams, ...savedReport.parameters })
          setReportName(savedReport.name)
          return
        }
      }

      setParameters(defaultParams)
      setSelectedFormat(template.output_formats[0] || 'json')
    }
  }, [template, searchParams])

  // Handle parameter change
  const handleParameterChange = useCallback(
    (key: string, value: string | number | string[] | null) => {
      setParameters((prev) => ({ ...prev, [key]: value }))
    },
    []
  )

  // Handle multi-select change
  const handleMultiSelectChange = useCallback(
    (key: string, value: string, checked: boolean) => {
      setParameters((prev) => {
        const current = (prev[key] as string[]) || []
        if (checked) {
          return { ...prev, [key]: [...current, value] }
        } else {
          return { ...prev, [key]: current.filter((v) => v !== value) }
        }
      })
    },
    []
  )

  // Generate report
  const handleGenerate = useCallback(() => {
    if (!templateId) return

    generateMutation.mutate({
      template_id: templateId,
      parameters,
      format: selectedFormat,
    })
  }, [templateId, parameters, selectedFormat, generateMutation])

  // Export report
  const handleExport = useCallback(
    (format: ReportFormat) => {
      if (reportResult) {
        reportsService.exportReportData(reportResult, format)
      }
    },
    [reportResult]
  )

  // Print report
  const handlePrint = useCallback(() => {
    window.print()
  }, [])

  // Save report configuration
  const handleSaveReport = useCallback(() => {
    if (!template || !reportName.trim()) return

    const savedReport: SavedReport = {
      id: `rpt_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      name: reportName.trim(),
      template_id: template.id,
      template_name: template.name,
      parameters,
      savedAt: new Date().toISOString(),
      lastRun: reportResult ? new Date().toISOString() : undefined,
    }

    reportsService.saveReportConfig(savedReport)
    setSaveModalOpen(false)
    setReportName('')
  }, [template, reportName, parameters, reportResult])

  // Check if all required parameters are filled
  const canGenerate = useMemo(() => {
    if (!template) return false

    return template.parameters.every((param) => {
      if (!param.required) return true
      const value = parameters[param.key]
      if (value === null || value === undefined) return false
      if (typeof value === 'string' && value.trim() === '') return false
      if (Array.isArray(value) && value.length === 0) return false
      return true
    })
  }, [template, parameters])

  // Render parameter input
  const renderParameterInput = (param: ReportParameter) => {
    const value = parameters[param.key]

    switch (param.type) {
      case 'date':
        return (
          <input
            type="date"
            value={(value as string) || ''}
            onChange={(e) => handleParameterChange(param.key, e.target.value)}
            className={cn(
              'w-full px-3 py-2 text-sm border rounded-md',
              'border-[#DDDBDA] dark:border-gray-600',
              'bg-white dark:bg-gray-800',
              'text-gray-900 dark:text-gray-100',
              'focus:outline-none focus:ring-2 focus:ring-[#0176D3]/20 focus:border-[#0176D3]'
            )}
          />
        )

      case 'select':
        return (
          <select
            value={(value as string) || ''}
            onChange={(e) => handleParameterChange(param.key, e.target.value || null)}
            className={cn(
              'w-full px-3 py-2 text-sm border rounded-md',
              'border-[#DDDBDA] dark:border-gray-600',
              'bg-white dark:bg-gray-800',
              'text-gray-900 dark:text-gray-100',
              'focus:outline-none focus:ring-2 focus:ring-[#0176D3]/20 focus:border-[#0176D3]'
            )}
          >
            <option value="">Select {param.label}...</option>
            {param.options?.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        )

      case 'multi_select':
        return (
          <div className="space-y-2 max-h-40 overflow-y-auto p-2 border border-[#DDDBDA] dark:border-gray-600 rounded-md bg-white dark:bg-gray-800">
            {param.options?.map((opt) => (
              <label
                key={opt}
                className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 p-1 rounded"
              >
                <input
                  type="checkbox"
                  checked={(value as string[])?.includes(opt) || false}
                  onChange={(e) => handleMultiSelectChange(param.key, opt, e.target.checked)}
                  className="w-4 h-4 rounded border-[#DDDBDA] text-[#0176D3] focus:ring-[#0176D3]"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">{opt}</span>
              </label>
            ))}
          </div>
        )

      case 'number':
        return (
          <input
            type="number"
            value={(value as number) || ''}
            onChange={(e) =>
              handleParameterChange(param.key, e.target.value ? Number(e.target.value) : null)
            }
            className={cn(
              'w-full px-3 py-2 text-sm border rounded-md',
              'border-[#DDDBDA] dark:border-gray-600',
              'bg-white dark:bg-gray-800',
              'text-gray-900 dark:text-gray-100',
              'focus:outline-none focus:ring-2 focus:ring-[#0176D3]/20 focus:border-[#0176D3]'
            )}
          />
        )

      default:
        return (
          <input
            type="text"
            value={(value as string) || ''}
            onChange={(e) => handleParameterChange(param.key, e.target.value || null)}
            className={cn(
              'w-full px-3 py-2 text-sm border rounded-md',
              'border-[#DDDBDA] dark:border-gray-600',
              'bg-white dark:bg-gray-800',
              'text-gray-900 dark:text-gray-100',
              'focus:outline-none focus:ring-2 focus:ring-[#0176D3]/20 focus:border-[#0176D3]'
            )}
          />
        )
    }
  }

  if (templateLoading) {
    return (
      <PageLayout title="Loading..." breadcrumbs={[{ label: 'Reports', href: '/reports' }]}>
        <div className="flex items-center justify-center h-64">
          <ArrowPathIcon className="w-8 h-8 animate-spin text-gray-400" />
        </div>
      </PageLayout>
    )
  }

  if (!template) {
    return (
      <PageLayout
        title="Report Not Found"
        breadcrumbs={[{ label: 'Reports', href: '/reports' }, { label: 'Not Found' }]}
      >
        <div className="text-center py-12">
          <DocumentTextIcon className="w-12 h-12 mx-auto text-gray-400" />
          <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-white">
            Report template not found
          </h3>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            The requested report template does not exist.
          </p>
          <Button variant="primary" className="mt-4" onClick={() => navigate('/reports')}>
            Back to Reports
          </Button>
        </div>
      </PageLayout>
    )
  }

  return (
    <PageLayout
      title={template.name}
      subtitle={template.description}
      breadcrumbs={[
        { label: 'Reports', href: '/reports' },
        { label: template.name },
      ]}
      actions={
        <Button
          variant="ghost"
          size="sm"
          leftIcon={<ArrowLeftIcon className="w-4 h-4" />}
          onClick={() => navigate('/reports')}
        >
          Back
        </Button>
      }
    >
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left Panel: Parameters */}
        <div className="lg:col-span-1">
          <div className="bg-white dark:bg-gray-900 rounded-lg border border-[#DDDBDA] dark:border-gray-700 sticky top-4">
            <div className="p-4 border-b border-[#DDDBDA] dark:border-gray-700">
              <h2 className="text-base font-semibold text-gray-900 dark:text-white">
                Report Parameters
              </h2>
            </div>

            <div className="p-4 space-y-4">
              {/* Parameters */}
              {template.parameters.map((param) => (
                <div key={param.key}>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    {param.label}
                    {param.required && <span className="text-red-500 ml-1">*</span>}
                  </label>
                  {renderParameterInput(param)}
                </div>
              ))}

              {/* Output Format */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Output Format
                </label>
                <select
                  value={selectedFormat}
                  onChange={(e) => setSelectedFormat(e.target.value as ReportFormat)}
                  className={cn(
                    'w-full px-3 py-2 text-sm border rounded-md',
                    'border-[#DDDBDA] dark:border-gray-600',
                    'bg-white dark:bg-gray-800',
                    'text-gray-900 dark:text-gray-100',
                    'focus:outline-none focus:ring-2 focus:ring-[#0176D3]/20 focus:border-[#0176D3]'
                  )}
                >
                  {template.output_formats.map((format) => (
                    <option key={format} value={format}>
                      {format.toUpperCase()}
                    </option>
                  ))}
                </select>
              </div>

              {/* Generate Button */}
              <Button
                variant="primary"
                className="w-full"
                onClick={handleGenerate}
                disabled={!canGenerate || generateMutation.isPending}
                isLoading={generateMutation.isPending}
                leftIcon={<ArrowPathIcon className="w-4 h-4" />}
              >
                {generateMutation.isPending ? 'Generating...' : 'Generate Report'}
              </Button>

              {/* Save Configuration */}
              <Button
                variant="ghost"
                className="w-full"
                onClick={() => setSaveModalOpen(true)}
                leftIcon={<BookmarkIcon className="w-4 h-4" />}
              >
                Save Configuration
              </Button>
            </div>
          </div>
        </div>

        {/* Right Panel: Results */}
        <div className="lg:col-span-3">
          {reportResult ? (
            <div className="bg-white dark:bg-gray-900 rounded-lg border border-[#DDDBDA] dark:border-gray-700">
              {/* Results Header */}
              <div className="p-4 border-b border-[#DDDBDA] dark:border-gray-700 flex items-center justify-between">
                <div>
                  <h2 className="text-base font-semibold text-gray-900 dark:text-white">
                    Report Results
                  </h2>
                  <p className="text-sm text-gray-500 mt-0.5">
                    Generated at {new Date(reportResult.generated_at).toLocaleString()}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  {/* View Mode Toggle */}
                  <div className="flex items-center bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
                    <button
                      onClick={() => setViewMode('table')}
                      className={cn(
                        'p-1.5 rounded-md transition-all',
                        viewMode === 'table'
                          ? 'bg-white dark:bg-gray-700 shadow-sm'
                          : 'text-gray-500 hover:text-gray-700'
                      )}
                      title="Table View"
                    >
                      <TableCellsIcon className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setViewMode('chart')}
                      className={cn(
                        'p-1.5 rounded-md transition-all',
                        viewMode === 'chart'
                          ? 'bg-white dark:bg-gray-700 shadow-sm'
                          : 'text-gray-500 hover:text-gray-700'
                      )}
                      title="Chart View"
                    >
                      <ChartBarIcon className="w-4 h-4" />
                    </button>
                  </div>

                  {/* Actions */}
                  <Button
                    variant="ghost"
                    size="sm"
                    leftIcon={<PrinterIcon className="w-4 h-4" />}
                    onClick={handlePrint}
                  >
                    Print
                  </Button>

                  <div className="relative group">
                    <Button
                      variant="secondary"
                      size="sm"
                      leftIcon={<ArrowDownTrayIcon className="w-4 h-4" />}
                    >
                      Export
                    </Button>
                    <div className="absolute right-0 top-full mt-1 bg-white dark:bg-gray-800 border border-[#DDDBDA] dark:border-gray-600 rounded-md shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10 min-w-[120px]">
                      {template.output_formats.map((format) => (
                        <button
                          key={format}
                          onClick={() => handleExport(format)}
                          className="block w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                        >
                          {format.toUpperCase()}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Report Viewer */}
              <ReportViewer
                result={reportResult}
                viewMode={viewMode}
                onViewModeChange={setViewMode}
              />
            </div>
          ) : (
            <div className="bg-white dark:bg-gray-900 rounded-lg border border-[#DDDBDA] dark:border-gray-700 p-12 text-center">
              <DocumentTextIcon className="w-16 h-16 mx-auto text-gray-300 dark:text-gray-600" />
              <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-white">
                No Report Generated
              </h3>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400 max-w-md mx-auto">
                Configure the report parameters on the left and click "Generate Report" to view
                results.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Save Report Modal */}
      <Modal
        isOpen={saveModalOpen}
        onClose={() => setSaveModalOpen(false)}
        title="Save Report Configuration"
        size="sm"
        footer={
          <>
            <Button variant="ghost" onClick={() => setSaveModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleSaveReport}
              disabled={!reportName.trim()}
            >
              Save
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Save this report configuration for quick access later.
          </p>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Report Name
            </label>
            <input
              type="text"
              value={reportName}
              onChange={(e) => setReportName(e.target.value)}
              placeholder="Enter a name for this report..."
              className={cn(
                'w-full px-3 py-2 text-sm border rounded-md',
                'border-[#DDDBDA] dark:border-gray-600',
                'bg-white dark:bg-gray-800',
                'text-gray-900 dark:text-gray-100',
                'focus:outline-none focus:ring-2 focus:ring-[#0176D3]/20 focus:border-[#0176D3]'
              )}
            />
          </div>
        </div>
      </Modal>
    </PageLayout>
  )
}

export default GenerateReportPage
