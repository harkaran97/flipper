/** Formatting utilities for currency, time, and fault display values. */

/** £1,200 from 120000 pence */
export const formatPrice = (pence: number): string =>
  `£${(pence / 100).toLocaleString('en-GB', { minimumFractionDigits: 0 })}`

/** +£1,790 — always show + for profit */
export const formatProfit = (pence: number): string =>
  `+${formatPrice(pence)}`

/** 2.5 days / 1.0 day */
export const formatDays = (days: number): string =>
  `${days} ${days === 1 ? 'day' : 'days'}`

/** fault_type → display: "timing_chain_failure" → "Timing chain" */
export const formatFaultType = (ft: string): string =>
  ft.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
    .replace(' Failure', '').replace(' Fault', '')

/** faults array → summary string for card: "Timing chain, DPF" */
export const formatFaultSummary = (faults: string[]): string =>
  faults.map(formatFaultType).slice(0, 3).join(', ') +
  (faults.length > 3 ? ` +${faults.length - 3}` : '')
