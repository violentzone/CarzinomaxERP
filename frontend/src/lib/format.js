/**
 * Formatting helpers. Backend Numeric/Decimal fields may arrive as numbers OR
 * strings (jsonable_encoder), so every numeric helper coerces with `num()` first.
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

export function compactNumber(v) {
  return new Intl.NumberFormat(undefined, { notation: 'compact', maximumFractionDigits: 1 }).format(num(v))
}

/** Format an ISO date / datetime string as e.g. "Jul 6, 2026". */
export function date(v) {
  if (!v) return '—'
  const d = parseDate(v)
  if (!d) return String(v)
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

export function time(v) {
  if (!v) return '—'
  const d = new Date(v)
  if (Number.isNaN(d.getTime())) return String(v)
  return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
}

/**
 * Parse a date. Bare `YYYY-MM-DD` strings are treated as *local* dates (the
 * Date constructor would read them as UTC and shift them a day in the west).
 */
export function parseDate(v) {
  if (!v) return null
  if (v instanceof Date) return v
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(v))
  const d = m ? new Date(+m[1], +m[2] - 1, +m[3]) : new Date(v)
  return Number.isNaN(d.getTime()) ? null : d
}

/** Today's date as a local ISO `YYYY-MM-DD` string — handy default for date inputs. */
export function today() {
  return toDateInput(new Date())
}

/** Local `YYYY-MM-DD` for a Date. */
export function toDateInput(d) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/** First / last day of the month containing `d` (default: now), as date-input strings. */
export function monthBounds(d = new Date()) {
  const start = new Date(d.getFullYear(), d.getMonth(), 1)
  const end = new Date(d.getFullYear(), d.getMonth() + 1, 0)
  return { start: toDateInput(start), end: toDateInput(end) }
}

/** `YYYY-MM` bucket for a date-ish value (for monthly charts). */
export function monthKey(v) {
  const d = parseDate(v)
  if (!d) return ''
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

/** "Jul 2026" label for a `YYYY-MM` key. */
export function monthLabel(key) {
  if (!key) return ''
  const [y, m] = key.split('-').map(Number)
  return new Date(y, m - 1, 1).toLocaleDateString(undefined, { month: 'short', year: 'numeric' })
}

/** ISO datetime → value for an `<input type="datetime-local">` (local time). */
export function toLocalInput(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** `<input type="datetime-local">` value → ISO string (UTC) for the API. */
export function fromLocalInput(v) {
  if (!v) return null
  const d = new Date(v)
  return Number.isNaN(d.getTime()) ? null : d.toISOString()
}

/** Hours between two ISO datetimes, rounded to 2 dp; null if either is missing. */
export function hoursBetween(a, b) {
  if (!a || !b) return null
  const ms = new Date(b) - new Date(a)
  if (!Number.isFinite(ms) || ms < 0) return null
  return Math.round((ms / 36e5) * 100) / 100
}

/** Inclusive number of calendar days between two `YYYY-MM-DD` values. */
export function daysBetween(a, b) {
  const da = parseDate(a)
  const db = parseDate(b)
  if (!da || !db) return 0
  return Math.round((db - da) / 864e5) + 1
}

/** Turn a snake/lower status token into a Title Case label. */
export function titleize(s) {
  if (!s) return ''
  return String(s)
    .replace(/[_-]/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

/** First 8 chars of a UUID for compact display. */
export function shortId(id) {
  if (!id) return '—'
  return String(id).slice(0, 8)
}

/** Display name for a user record. */
export function userName(u) {
  if (!u) return '—'
  return u.full_name || u.email || `#${u.id}`
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
