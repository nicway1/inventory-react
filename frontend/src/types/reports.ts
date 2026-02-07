/**
 * Reports Types
 *
 * Type definitions for the reports module including templates,
 * generation requests, and report results.
 */

import type { BaseEntity } from './common'

// Report Category
export type ReportCategory = 'tickets' | 'inventory' | 'users' | 'analytics'

// Report Output Format
export type ReportFormat = 'json' | 'csv' | 'pdf' | 'xlsx'

// Report Parameter Types
export type ReportParameterType = 'date' | 'select' | 'multi_select' | 'number' | 'text'

// Report Parameter Definition
export interface ReportParameter {
  key: string
  type: ReportParameterType
  label: string
  required?: boolean
  default?: string | number | string[]
  options?: string[]
  options_endpoint?: string
}

// Report Template
export interface ReportTemplate {
  id: string
  name: string
  description: string
  category: ReportCategory
  icon: string
  parameters: ReportParameter[]
  output_formats: ReportFormat[]
  permissions?: string[]
}

// Report Category Info
export interface ReportCategoryInfo {
  id: ReportCategory
  name: string
}

// Report Templates Response
export interface ReportTemplatesResponse {
  data: ReportTemplate[]
  meta: {
    categories: ReportCategoryInfo[]
    total_templates: number
  }
  message: string
}

// Generate Report Request
export interface GenerateReportRequest {
  template_id: string
  parameters: Record<string, string | number | string[] | null>
  format: ReportFormat
}

// Chart Data
export interface ReportChartData {
  type: 'pie' | 'bar' | 'donut' | 'line'
  title: string
  data: {
    labels: string[]
    values?: number[]
    datasets?: Array<{
      label: string
      values: number[]
    }>
  }
}

// Report Summary (varies by report type)
export interface ReportSummary {
  [key: string]: string | number | Record<string, number> | undefined
}

// Report Data Row (varies by report type)
export interface ReportDataRow {
  [key: string]: string | number | null | undefined
}

// Report Result
export interface ReportResult {
  report_id: string
  template: string
  template_name: string
  generated_at: string
  parameters: Record<string, string | number | string[] | null>
  format: ReportFormat
  summary: ReportSummary
  data: ReportDataRow[]
  charts: ReportChartData[]
  csv_data?: string
}

// Generate Report Response
export interface GenerateReportResponse {
  success: boolean
  data: ReportResult
  message: string
}

// Report History Entry
export interface ReportHistoryEntry extends BaseEntity {
  report_id: string
  template_id: string
  template_name: string
  generated_by: string
  generated_at: string
  parameters: Record<string, string | number | string[] | null>
  format: ReportFormat
}

// Report History Response
export interface ReportHistoryResponse {
  data: ReportHistoryEntry[]
  meta: {
    total: number
    page: number
    per_page: number
  }
}

// Saved Report (client-side storage)
export interface SavedReport {
  id: string
  name: string
  template_id: string
  template_name: string
  parameters: Record<string, string | number | string[] | null>
  savedAt: string
  lastRun?: string
  reportType?: string
}

// Report Filter State
export interface ReportFilters {
  category: ReportCategory | 'all'
  search: string
}

// Icon mapping for report templates
export const REPORT_ICON_MAP: Record<string, string> = {
  'file-text': 'DocumentTextIcon',
  'clock': 'ClockIcon',
  'laptop': 'ComputerDesktopIcon',
  'pie-chart': 'ChartPieIcon',
  'calendar': 'CalendarIcon',
  'users': 'UsersIcon',
  'bar-chart-2': 'ChartBarIcon',
}

// Category display configuration
export const CATEGORY_CONFIG: Record<ReportCategory, { label: string; color: string; bgColor: string }> = {
  tickets: {
    label: 'Ticket Reports',
    color: 'text-purple-700',
    bgColor: 'bg-purple-100',
  },
  inventory: {
    label: 'Inventory Reports',
    color: 'text-green-700',
    bgColor: 'bg-green-100',
  },
  users: {
    label: 'User Reports',
    color: 'text-blue-700',
    bgColor: 'bg-blue-100',
  },
  analytics: {
    label: 'Analytics',
    color: 'text-orange-700',
    bgColor: 'bg-orange-100',
  },
}
