/**
 * Formatting helpers. Backend Decimal fields may arrive as numbers OR strings
 * (pydantic v2 JSON mode), so every numeric helper coerces with `num()` first.
 */

/** Coerce a possibly-string / possibly-null value to a finite number. */
export function num(v) {
  if (v === null || v === undefined || v === '') return 0
  const n = typeof v === 'number' ? v : parseFloat(v)
  return Number.isFinite(n) ? n : 0
}

const money = new Intl.NumberFormat(undefined, {
  style: 'currency',
  currency: 'USD',
  // plain "$" — without this, non-US locales render "US$"
  currencyDisplay: 'narrowSymbol',
  maximumFractionDigits: 2,
})

export function currency(v) {
  return money.format(num(v))
}

export function compactCurrency(v) {
  const n = num(v)
  if (Math.abs(n) >= 1000) {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency: 'USD',
      currencyDisplay: 'narrowSymbol',
      notation: 'compact',
      maximumFractionDigits: 1,
    }).format(n)
  }
  return money.format(n)
}

export function number(v) {
  return new Intl.NumberFormat().format(num(v))
}

/** Format an ISO date / datetime string as e.g. "Jul 6, 2026". */
export function date(v) {
  if (!v) return '—'
  const d = new Date(v)
  if (Number.isNaN(d.getTime())) return String(v)
  return d.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export function dateTime(v) {
  if (!v) return '—'
  const d = new Date(v)
  if (Number.isNaN(d.getTime())) return String(v)
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Today's date as an ISO `YYYY-MM-DD` string — handy default for date inputs. */
export function today() {
  return new Date().toISOString().slice(0, 10)
}

/** Turn a snake/lower status token into a Title Case label. */
export function titleize(s) {
  if (!s) return ''
  return String(s)
    .replace(/[_-]/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

/** Deterministic accent color for a category/label (for chips & charts). */
export const CHART_COLORS = [
  '#aa3bff',
  '#22d3ee',
  '#f472d0',
  '#7c3aed',
  '#34d399',
  '#f79009',
  '#2e90fa',
  '#fb7185',
]

export function colorFor(key, i = 0) {
  if (typeof i === 'number' && i >= 0) return CHART_COLORS[i % CHART_COLORS.length]
  let h = 0
  for (const ch of String(key)) h = (h * 31 + ch.charCodeAt(0)) & 0xffff
  return CHART_COLORS[h % CHART_COLORS.length]
}
