/**
 * DataTable Component
 *
 * A fully-featured data table with sorting, selection, pagination,
 * loading states, and responsive design.
 */

import React, { useCallback, useMemo } from 'react'
import {
  ChevronUpIcon,
  ChevronDownIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ChevronDoubleLeftIcon,
  ChevronDoubleRightIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils/cn'

// Column definition for the table
export interface ColumnDef<T> {
  /** Unique identifier for the column */
  id: string
  /** Header text or render function */
  header: string | (() => React.ReactNode)
  /** Accessor key or render function for cell content */
  accessorKey?: keyof T
  /** Custom cell render function */
  cell?: (row: T) => React.ReactNode
  /** Whether the column is sortable */
  sortable?: boolean
  /** Column width (CSS value) */
  width?: string
  /** Minimum column width */
  minWidth?: string
  /** Text alignment */
  align?: 'left' | 'center' | 'right'
  /** Custom header class name */
  headerClassName?: string
  /** Custom cell class name */
  cellClassName?: string
}

// Props for the DataTable component
export interface DataTableProps<T> {
  /** Array of data items to display */
  data: T[]
  /** Column definitions */
  columns: ColumnDef<T>[]
  /** Whether data is loading */
  isLoading?: boolean
  /** Pagination configuration */
  pagination?: {
    page: number
    pageSize: number
    total: number
    onPageChange: (page: number) => void
  }
  /** Sorting configuration */
  sorting?: {
    sortBy: string
    sortOrder: 'asc' | 'desc'
    onSort: (column: string) => void
  }
  /** Row selection configuration */
  selection?: {
    selected: string[]
    onSelect: (ids: string[]) => void
  }
  /** Callback when a row is clicked */
  onRowClick?: (row: T) => void
  /** Message to display when table is empty */
  emptyMessage?: string
  /** Key extractor for row identification */
  getRowId?: (row: T) => string
  /** Custom row class name function */
  rowClassName?: (row: T) => string
  /** Additional class name for the table wrapper */
  className?: string
}

// Skeleton row for loading state
function SkeletonRow({ columns }: { columns: number }) {
  return (
    <tr className="animate-pulse">
      {Array.from({ length: columns }).map((_, index) => (
        <td key={index} className="px-4 py-3">
          <div className="h-4 bg-gray-200 rounded w-3/4" />
        </td>
      ))}
    </tr>
  )
}

// Empty state component
function EmptyState({ message }: { message: string }) {
  return (
    <tr>
      <td colSpan={100} className="px-4 py-12 text-center">
        <div className="flex flex-col items-center justify-center text-gray-500">
          <svg
            className="w-12 h-12 mb-4 text-gray-300"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
            />
          </svg>
          <p className="text-sm font-medium">{message}</p>
        </div>
      </td>
    </tr>
  )
}

// Sort indicator component
function SortIndicator({
  active,
  direction,
}: {
  active: boolean
  direction?: 'asc' | 'desc'
}) {
  return (
    <span className="ml-1.5 inline-flex flex-col">
      <ChevronUpIcon
        className={cn(
          'w-3 h-3 -mb-1',
          active && direction === 'asc'
            ? 'text-blue-600'
            : 'text-gray-300'
        )}
      />
      <ChevronDownIcon
        className={cn(
          'w-3 h-3',
          active && direction === 'desc'
            ? 'text-blue-600'
            : 'text-gray-300'
        )}
      />
    </span>
  )
}

// Pagination component
function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
}: {
  page: number
  pageSize: number
  total: number
  onPageChange: (page: number) => void
}) {
  const totalPages = Math.ceil(total / pageSize)
  const startItem = (page - 1) * pageSize + 1
  const endItem = Math.min(page * pageSize, total)

  const canGoPrevious = page > 1
  const canGoNext = page < totalPages

  return (
    <div className="flex items-center justify-between px-4 py-3 bg-white border-t border-[#DDDBDA] sm:px-6">
      <div className="flex-1 hidden sm:flex sm:items-center sm:justify-between">
        <div>
          <p className="text-sm text-gray-700">
            Showing <span className="font-medium">{startItem}</span> to{' '}
            <span className="font-medium">{endItem}</span> of{' '}
            <span className="font-medium">{total}</span> results
          </p>
        </div>
        <div>
          <nav
            className="inline-flex -space-x-px rounded-md shadow-sm isolate"
            aria-label="Pagination"
          >
            <button
              onClick={() => onPageChange(1)}
              disabled={!canGoPrevious}
              className={cn(
                'relative inline-flex items-center rounded-l-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300',
                canGoPrevious
                  ? 'hover:bg-gray-50 focus:z-20 focus:outline-offset-0'
                  : 'cursor-not-allowed opacity-50'
              )}
              aria-label="First page"
            >
              <ChevronDoubleLeftIcon className="w-5 h-5" />
            </button>
            <button
              onClick={() => onPageChange(page - 1)}
              disabled={!canGoPrevious}
              className={cn(
                'relative inline-flex items-center px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300',
                canGoPrevious
                  ? 'hover:bg-gray-50 focus:z-20 focus:outline-offset-0'
                  : 'cursor-not-allowed opacity-50'
              )}
              aria-label="Previous page"
            >
              <ChevronLeftIcon className="w-5 h-5" />
            </button>
            <span className="relative inline-flex items-center px-4 py-2 text-sm font-semibold text-gray-900 ring-1 ring-inset ring-gray-300">
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={!canGoNext}
              className={cn(
                'relative inline-flex items-center px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300',
                canGoNext
                  ? 'hover:bg-gray-50 focus:z-20 focus:outline-offset-0'
                  : 'cursor-not-allowed opacity-50'
              )}
              aria-label="Next page"
            >
              <ChevronRightIcon className="w-5 h-5" />
            </button>
            <button
              onClick={() => onPageChange(totalPages)}
              disabled={!canGoNext}
              className={cn(
                'relative inline-flex items-center rounded-r-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300',
                canGoNext
                  ? 'hover:bg-gray-50 focus:z-20 focus:outline-offset-0'
                  : 'cursor-not-allowed opacity-50'
              )}
              aria-label="Last page"
            >
              <ChevronDoubleRightIcon className="w-5 h-5" />
            </button>
          </nav>
        </div>
      </div>
      {/* Mobile pagination */}
      <div className="flex justify-between flex-1 sm:hidden">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={!canGoPrevious}
          className={cn(
            'relative inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700',
            canGoPrevious ? 'hover:bg-gray-50' : 'cursor-not-allowed opacity-50'
          )}
        >
          Previous
        </button>
        <span className="inline-flex items-center text-sm text-gray-700">
          {page} / {totalPages}
        </span>
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={!canGoNext}
          className={cn(
            'relative inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700',
            canGoNext ? 'hover:bg-gray-50' : 'cursor-not-allowed opacity-50'
          )}
        >
          Next
        </button>
      </div>
    </div>
  )
}

export function DataTable<T extends Record<string, unknown>>({
  data,
  columns,
  isLoading = false,
  pagination,
  sorting,
  selection,
  onRowClick,
  emptyMessage = 'No data available',
  getRowId = (row) => String(row.id ?? ''),
  rowClassName,
  className,
}: DataTableProps<T>) {
  // Determine if all rows are selected
  const allSelected = useMemo(() => {
    if (!selection || data.length === 0) return false
    return data.every((row) => selection.selected.includes(getRowId(row)))
  }, [selection, data, getRowId])

  // Handle header checkbox toggle
  const handleSelectAll = useCallback(() => {
    if (!selection) return

    if (allSelected) {
      // Deselect all current page items
      const currentPageIds = data.map(getRowId)
      selection.onSelect(
        selection.selected.filter((id) => !currentPageIds.includes(id))
      )
    } else {
      // Select all current page items
      const currentPageIds = data.map(getRowId)
      const newSelected = [...new Set([...selection.selected, ...currentPageIds])]
      selection.onSelect(newSelected)
    }
  }, [selection, allSelected, data, getRowId])

  // Handle individual row selection
  const handleSelectRow = useCallback(
    (row: T) => {
      if (!selection) return

      const rowId = getRowId(row)
      if (selection.selected.includes(rowId)) {
        selection.onSelect(selection.selected.filter((id) => id !== rowId))
      } else {
        selection.onSelect([...selection.selected, rowId])
      }
    },
    [selection, getRowId]
  )

  // Handle column sort
  const handleSort = useCallback(
    (columnId: string) => {
      if (!sorting) return
      sorting.onSort(columnId)
    },
    [sorting]
  )

  // Get cell value
  const getCellValue = useCallback(
    (row: T, column: ColumnDef<T>): React.ReactNode => {
      if (column.cell) {
        return column.cell(row)
      }
      if (column.accessorKey) {
        return row[column.accessorKey] as React.ReactNode
      }
      return null
    },
    []
  )

  // Calculate total columns (including selection checkbox)
  const totalColumns = columns.length + (selection ? 1 : 0)

  return (
    <div
      className={cn(
        'overflow-hidden bg-white border border-[#DDDBDA] rounded shadow-[0_2px_4px_rgba(0,0,0,0.1)]',
        className
      )}
    >
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-[#DDDBDA]">
          <thead className="bg-[#F3F3F3]">
            <tr>
              {/* Selection header */}
              {selection && (
                <th scope="col" className="w-12 px-4 py-3">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={handleSelectAll}
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                    aria-label="Select all rows"
                  />
                </th>
              )}
              {/* Column headers */}
              {columns.map((column) => {
                const isSorted = sorting?.sortBy === column.id
                const canSort = column.sortable && sorting

                return (
                  <th
                    key={column.id}
                    scope="col"
                    style={{
                      width: column.width,
                      minWidth: column.minWidth,
                    }}
                    className={cn(
                      'px-4 py-3 text-xs font-bold tracking-wider text-[#706E6B] uppercase',
                      column.align === 'center' && 'text-center',
                      column.align === 'right' && 'text-right',
                      column.align !== 'center' &&
                        column.align !== 'right' &&
                        'text-left',
                      canSort && 'cursor-pointer select-none hover:bg-[#E5E5E5]',
                      column.headerClassName
                    )}
                    onClick={() => canSort && handleSort(column.id)}
                  >
                    <div
                      className={cn(
                        'inline-flex items-center',
                        column.align === 'right' && 'flex-row-reverse'
                      )}
                    >
                      {typeof column.header === 'function'
                        ? column.header()
                        : column.header}
                      {canSort && (
                        <SortIndicator
                          active={isSorted}
                          direction={isSorted ? sorting.sortOrder : undefined}
                        />
                      )}
                    </div>
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-[#DDDBDA]">
            {/* Loading state */}
            {isLoading &&
              Array.from({ length: 5 }).map((_, index) => (
                <SkeletonRow key={`skeleton-${index}`} columns={totalColumns} />
              ))}

            {/* Empty state */}
            {!isLoading && data.length === 0 && (
              <EmptyState message={emptyMessage} />
            )}

            {/* Data rows */}
            {!isLoading &&
              data.map((row) => {
                const rowId = getRowId(row)
                const isSelected = selection?.selected.includes(rowId)

                return (
                  <tr
                    key={rowId}
                    className={cn(
                      'transition-colors',
                      isSelected && 'bg-[#0176D3]/10',
                      onRowClick && 'cursor-pointer hover:bg-[#F4F6F9]',
                      !isSelected && !onRowClick && 'hover:bg-[#F4F6F9]',
                      'odd:bg-white even:bg-[#FAFAFA]',
                      rowClassName?.(row)
                    )}
                    onClick={() => onRowClick?.(row)}
                  >
                    {/* Selection checkbox */}
                    {selection && (
                      <td
                        className="w-12 px-4 py-3"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => handleSelectRow(row)}
                          className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                          aria-label={`Select row ${rowId}`}
                        />
                      </td>
                    )}
                    {/* Data cells */}
                    {columns.map((column) => (
                      <td
                        key={column.id}
                        className={cn(
                          'px-4 py-3 text-sm text-gray-900 whitespace-nowrap',
                          column.align === 'center' && 'text-center',
                          column.align === 'right' && 'text-right',
                          column.cellClassName
                        )}
                      >
                        {getCellValue(row, column)}
                      </td>
                    ))}
                  </tr>
                )
              })}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {pagination && !isLoading && data.length > 0 && (
        <Pagination
          page={pagination.page}
          pageSize={pagination.pageSize}
          total={pagination.total}
          onPageChange={pagination.onPageChange}
        />
      )}
    </div>
  )
}

export default DataTable
