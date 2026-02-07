/**
 * Reports Service
 *
 * API methods for report management including templates,
 * generation, and downloads.
 */

import { apiClient } from './api'
import type {
  ReportTemplate,
  ReportTemplatesResponse,
  GenerateReportRequest,
  GenerateReportResponse,
  ReportResult,
  ReportCategory,
  ReportFormat,
  SavedReport,
} from '@/types/reports'

// Storage key for saved reports
const SAVED_REPORTS_KEY = 'truelog-saved-reports'

/**
 * Get all available report templates
 */
export async function getReportTemplates(
  category?: ReportCategory
): Promise<ReportTemplatesResponse> {
  const params = category ? `?category=${category}` : ''
  const response = await apiClient.get<ReportTemplatesResponse>(
    `/v2/reports/templates${params}`
  )
  return response.data
}

/**
 * Get a single report template by ID
 */
export async function getReportTemplate(
  templateId: string
): Promise<ReportTemplate | null> {
  const response = await getReportTemplates()
  return response.data.find((t) => t.id === templateId) || null
}

/**
 * Generate a report
 */
export async function generateReport(
  request: GenerateReportRequest
): Promise<ReportResult> {
  const response = await apiClient.post<GenerateReportResponse>(
    '/v2/reports/generate',
    request
  )
  return response.data.data
}

/**
 * Download report as CSV
 */
export function downloadReportAsCSV(
  reportResult: ReportResult,
  filename?: string
): void {
  const csvData = reportResult.csv_data
  if (!csvData) {
    // Generate CSV from data if not provided
    const headers = Object.keys(reportResult.data[0] || {})
    const rows = reportResult.data.map((row) =>
      headers.map((h) => {
        const value = row[h]
        if (value === null || value === undefined) return ''
        // Escape quotes and wrap in quotes if contains comma
        const strValue = String(value)
        if (strValue.includes(',') || strValue.includes('"')) {
          return `"${strValue.replace(/"/g, '""')}"`
        }
        return strValue
      }).join(',')
    )
    const csvContent = [headers.join(','), ...rows].join('\n')
    downloadFile(csvContent, filename || `${reportResult.template}_report.csv`, 'text/csv')
  } else {
    downloadFile(csvData, filename || `${reportResult.template}_report.csv`, 'text/csv')
  }
}

/**
 * Download report as Excel (XLSX)
 * Note: For a real implementation, you would use a library like xlsx or exceljs
 */
export function downloadReportAsExcel(
  reportResult: ReportResult,
  filename?: string
): void {
  // For now, we'll download as CSV with .xlsx extension
  // In production, use xlsx library for proper Excel format
  console.warn('Excel export not fully implemented, downloading as CSV format')
  downloadReportAsCSV(reportResult, filename?.replace('.xlsx', '.csv'))
}

/**
 * Download report as PDF
 * Note: For a real implementation, you would generate PDF server-side or use jspdf
 */
export async function downloadReportAsPDF(
  _reportResult: ReportResult,
  _filename?: string
): Promise<void> {
  // In production, this would either:
  // 1. Call a server endpoint to generate PDF
  // 2. Use jspdf client-side
  console.warn('PDF export requires server-side generation or jspdf library')

  // For now, trigger print dialog as a workaround
  window.print()
}

/**
 * Generic file download helper
 */
function downloadFile(content: string, filename: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

/**
 * Save report configuration for later use
 */
export function saveReportConfig(report: SavedReport): void {
  const saved = getSavedReports()
  const existingIndex = saved.findIndex((r) => r.id === report.id)
  if (existingIndex >= 0) {
    saved[existingIndex] = report
  } else {
    saved.push(report)
  }
  localStorage.setItem(SAVED_REPORTS_KEY, JSON.stringify(saved))
}

/**
 * Get all saved report configurations
 */
export function getSavedReports(): SavedReport[] {
  try {
    const saved = localStorage.getItem(SAVED_REPORTS_KEY)
    return saved ? JSON.parse(saved) : []
  } catch {
    return []
  }
}

/**
 * Get a saved report by ID
 */
export function getSavedReport(id: string): SavedReport | null {
  const saved = getSavedReports()
  return saved.find((r) => r.id === id) || null
}

/**
 * Delete a saved report configuration
 */
export function deleteSavedReport(id: string): void {
  const saved = getSavedReports()
  const filtered = saved.filter((r) => r.id !== id)
  localStorage.setItem(SAVED_REPORTS_KEY, JSON.stringify(filtered))
}

/**
 * Export data for download in specified format
 */
export function exportReportData(
  reportResult: ReportResult,
  format: ReportFormat,
  filename?: string
): void {
  const baseFilename = filename || `${reportResult.template_name.replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}`

  switch (format) {
    case 'csv':
      downloadReportAsCSV(reportResult, `${baseFilename}.csv`)
      break
    case 'xlsx':
      downloadReportAsExcel(reportResult, `${baseFilename}.xlsx`)
      break
    case 'pdf':
      downloadReportAsPDF(reportResult, `${baseFilename}.pdf`)
      break
    case 'json':
      downloadFile(
        JSON.stringify(reportResult, null, 2),
        `${baseFilename}.json`,
        'application/json'
      )
      break
  }
}

// Service object for consistent exports
export const reportsService = {
  getReportTemplates,
  getReportTemplate,
  generateReport,
  downloadReportAsCSV,
  downloadReportAsExcel,
  downloadReportAsPDF,
  exportReportData,
  saveReportConfig,
  getSavedReports,
  getSavedReport,
  deleteSavedReport,
}

export default reportsService
