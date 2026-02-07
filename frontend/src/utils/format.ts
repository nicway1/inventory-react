/**
 * Number and Currency Formatting Utilities
 */

/**
 * Format a number as currency (SGD by default)
 */
export function formatCurrency(
  amount: number,
  currency: string = 'SGD',
  locale: string = 'en-SG'
): string {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)
}

/**
 * Format a number with thousand separators
 */
export function formatNumber(
  value: number,
  options?: Intl.NumberFormatOptions
): string {
  return new Intl.NumberFormat('en-SG', options).format(value)
}
