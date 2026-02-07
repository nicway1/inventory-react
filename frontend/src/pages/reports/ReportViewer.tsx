/**
 * ReportViewer Component
 *
 * Displays generated report data with:
 * - Summary statistics section
 * - Data table with sorting
 * - Chart visualizations
 * - Print-friendly layout
 */

import { useState, useMemo, useCallback } from 'react'
import {
  ChevronUpIcon,
  ChevronDownIcon,
  ChevronUpDownIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils/cn'
import type { ReportResult, ReportChartData } from '@/types/reports'

interface ReportViewerProps {
  result: ReportResult
  viewMode: 'table' | 'chart'
  onViewModeChange: (mode: 'table' | 'chart') => void
}

// Simple pie chart component using CSS
function SimplePieChart({ data }: { data: ReportChartData }) {
  const total = data.data.values?.reduce((sum, val) => sum + val, 0) || 0
  if (total === 0) return null

  const colors = [
    '#0176D3', '#9333EA', '#22C55E', '#F59E0B', '#EF4444',
    '#06B6D4', '#8B5CF6', '#10B981', '#F97316', '#EC4899',
  ]

  let cumulativePercent = 0

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-48 h-48">
        <svg viewBox="0 0 36 36" className="w-full h-full">
          {data.data.values?.map((value, index) => {
            const percent = (value / total) * 100
            const startAngle = cumulativePercent * 3.6
            cumulativePercent += percent
            const endAngle = cumulativePercent * 3.6

            // Calculate arc path
            const startRadians = (startAngle - 90) * (Math.PI / 180)
            const endRadians = (endAngle - 90) * (Math.PI / 180)
            const x1 = 18 + 15 * Math.cos(startRadians)
            const y1 = 18 + 15 * Math.sin(startRadians)
            const x2 = 18 + 15 * Math.cos(endRadians)
            const y2 = 18 + 15 * Math.sin(endRadians)
            const largeArc = percent > 50 ? 1 : 0

            return (
              <path
                key={index}
                d={`M 18 18 L ${x1} ${y1} A 15 15 0 ${largeArc} 1 ${x2} ${y2} Z`}
                fill={colors[index % colors.length]}
              />
            )
          })}
        </svg>
      </div>
      <div className="mt-4 flex flex-wrap justify-center gap-3">
        {data.data.labels.map((label, index) => (
          <div key={index} className="flex items-center gap-2 text-sm">
            <div
              className="w-3 h-3 rounded-sm"
              style={{ backgroundColor: colors[index % colors.length] }}
            />
            <span className="text-gray-600 dark:text-gray-400">
              {label}: {data.data.values?.[index] || 0}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

// Simple bar chart component using CSS
function SimpleBarChart({ data }: { data: ReportChartData }) {
  const values = data.data.values || data.data.datasets?.[0]?.values || []
  const maxValue = Math.max(...values, 1)

  const colors = ['#0176D3', '#9333EA']

  return (
    <div className="space-y-3">
      {data.data.labels.map((label, index) => {
        if (data.data.datasets) {
          // Multi-dataset bar chart
          return (
            <div key={index} className="space-y-1">
              <div className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate">
                {label}
              </div>
              {data.data.datasets.map((dataset, dsIndex) => (
                <div key={dsIndex} className="flex items-center gap-2">
                  <div className="w-16 text-xs text-gray-500">{dataset.label}</div>
                  <div className="flex-1 h-5 bg-gray-100 dark:bg-gray-700 rounded overflow-hidden">
                    <div
                      className="h-full rounded transition-all duration-300"
                      style={{
                        width: `${(dataset.values[index] / maxValue) * 100}%`,
                        backgroundColor: colors[dsIndex % colors.length],
                      }}
                    />
                  </div>
                  <div className="w-12 text-right text-sm text-gray-600 dark:text-gray-400">
                    {dataset.values[index]}
                  </div>
                </div>
              ))}
            </div>
          )
        }

        // Single value bar chart
        const value = values[index]
        const width = (value / maxValue) * 100

        return (
          <div key={index} className="flex items-center gap-2">
            <div className="w-24 text-sm text-gray-700 dark:text-gray-300 truncate" title={label}>
              {label}
            </div>
            <div className="flex-1 h-6 bg-gray-100 dark:bg-gray-700 rounded overflow-hidden">
              <div
                className="h-full bg-[#0176D3] rounded transition-all duration-300"
                style={{ width: `${width}%` }}
              />
            </div>
            <div className="w-16 text-right text-sm font-medium text-gray-900 dark:text-white">
              {value}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// Chart renderer
function ChartRenderer({ chart }: { chart: ReportChartData }) {
  switch (chart.type) {
    case 'pie':
    case 'donut':
      return <SimplePieChart data={chart} />
    case 'bar':
    case 'line':
      return <SimpleBarChart data={chart} />
    default:
      return <SimpleBarChart data={chart} />
  }
}

export function ReportViewer({ result, viewMode }: ReportViewerProps) {
  // Sorting state
  const [sortColumn, setSortColumn] = useState<string | null>(null)
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')

  // Get columns from data
  const columns = useMemo(() => {
    if (result.data.length === 0) return []
    return Object.keys(result.data[0])
  }, [result.data])

  // Sort data
  const sortedData = useMemo(() => {
    if (!sortColumn) return result.data

    return [...result.data].sort((a, b) => {
      const aVal = a[sortColumn]
      const bVal = b[sortColumn]

      if (aVal === null || aVal === undefined) return sortOrder === 'asc' ? 1 : -1
      if (bVal === null || bVal === undefined) return sortOrder === 'asc' ? -1 : 1

      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortOrder === 'asc' ? aVal - bVal : bVal - aVal
      }

      const aStr = String(aVal).toLowerCase()
      const bStr = String(bVal).toLowerCase()
      return sortOrder === 'asc' ? aStr.localeCompare(bStr) : bStr.localeCompare(aStr)
    })
  }, [result.data, sortColumn, sortOrder])

  // Handle sort
  const handleSort = useCallback((column: string) => {
    if (sortColumn === column) {
      setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortColumn(column)
      setSortOrder('asc')
    }
  }, [sortColumn])

  // Format column header
  const formatHeader = (key: string) => {
    return key
      .replace(/_/g, ' ')
      .replace(/([a-z])([A-Z])/g, '$1 $2')
      .replace(/\b\w/g, (l) => l.toUpperCase())
  }

  // Format cell value
  const formatValue = (value: string | number | null | undefined) => {
    if (value === null || value === undefined) return '-'
    if (typeof value === 'number') {
      if (Number.isInteger(value)) return value.toLocaleString()
      return value.toFixed(2)
    }
    return String(value)
  }

  return (
    <div className="print:bg-white">
      {/* Summary Section */}
      {Object.keys(result.summary).length > 0 && (
        <div className="p-4 border-b border-[#DDDBDA] dark:border-gray-700 print:border-gray-300">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-3">
            Summary
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {Object.entries(result.summary).map(([key, value]) => {
              // Skip nested objects for now
              if (typeof value === 'object' && value !== null) return null

              return (
                <div
                  key={key}
                  className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 print:bg-gray-100"
                >
                  <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    {formatHeader(key)}
                  </div>
                  <div className="mt-1 text-xl font-bold text-gray-900 dark:text-white">
                    {formatValue(value as string | number)}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Content based on view mode */}
      {viewMode === 'chart' && result.charts.length > 0 ? (
        /* Charts View */
        <div className="p-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {result.charts.map((chart, index) => (
              <div
                key={index}
                className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 print:bg-gray-100"
              >
                <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">
                  {chart.title}
                </h4>
                <ChartRenderer chart={chart} />
              </div>
            ))}
          </div>
        </div>
      ) : (
        /* Table View */
        <div className="overflow-x-auto print:overflow-visible">
          {result.data.length === 0 ? (
            <div className="p-8 text-center text-gray-500 dark:text-gray-400">
              No data available for this report.
            </div>
          ) : (
            <table className="w-full min-w-[600px] print:min-w-0">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-800 print:bg-gray-100">
                  {columns.map((column) => (
                    <th
                      key={column}
                      onClick={() => handleSort(column)}
                      className={cn(
                        'px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider',
                        'text-gray-600 dark:text-gray-400',
                        'border-b border-[#DDDBDA] dark:border-gray-700',
                        'cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors',
                        'print:border-gray-300'
                      )}
                    >
                      <div className="flex items-center gap-1">
                        {formatHeader(column)}
                        {sortColumn === column ? (
                          sortOrder === 'asc' ? (
                            <ChevronUpIcon className="w-4 h-4" />
                          ) : (
                            <ChevronDownIcon className="w-4 h-4" />
                          )
                        ) : (
                          <ChevronUpDownIcon className="w-4 h-4 opacity-50" />
                        )}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[#DDDBDA] dark:divide-gray-700 print:divide-gray-300">
                {sortedData.map((row, rowIndex) => (
                  <tr
                    key={rowIndex}
                    className="hover:bg-gray-50 dark:hover:bg-gray-800/50 print:hover:bg-transparent"
                  >
                    {columns.map((column) => (
                      <td
                        key={column}
                        className="px-4 py-3 text-sm text-gray-900 dark:text-gray-100"
                      >
                        {column === 'percentage' || column.includes('percentage') ? (
                          <span className="font-medium">{formatValue(row[column])}%</span>
                        ) : column === 'count' || column.includes('count') ? (
                          <span className="font-semibold text-[#0176D3]">
                            {formatValue(row[column])}
                          </span>
                        ) : (
                          formatValue(row[column])
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Charts shown below table if in table view */}
      {viewMode === 'table' && result.charts.length > 0 && (
        <div className="p-4 border-t border-[#DDDBDA] dark:border-gray-700 print:border-gray-300">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-4">
            Visualizations
          </h3>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {result.charts.map((chart, index) => (
              <div
                key={index}
                className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 print:bg-gray-100"
              >
                <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">
                  {chart.title}
                </h4>
                <ChartRenderer chart={chart} />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="p-4 border-t border-[#DDDBDA] dark:border-gray-700 text-xs text-gray-500 dark:text-gray-400 print:border-gray-300">
        <div className="flex items-center justify-between">
          <span>Report ID: {result.report_id}</span>
          <span>{result.data.length} row(s)</span>
        </div>
      </div>
    </div>
  )
}

export default ReportViewer
