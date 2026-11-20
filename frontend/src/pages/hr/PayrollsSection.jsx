import { useState } from 'react'
import { Banknote } from 'lucide-react'
import { hrApi } from '../../api/hr'
import { useUsers } from '../../lib/useUsers'
import { num, currency, date as fmtDate, parseDate, monthBounds, monthKey, monthLabel } from '../../lib/format'
import ResourceSection from '../../components/ResourceSection'
import Badge from '../../components/ui/Badge'
import { Input, Select } from '../../components/ui/Field'

const AMOUNT_KEYS = ['base_salary', 'allowances', 'deductions', 'net_pay']
const MAIL_BADGE = {
  sent: { tone: 'success', label: 'Sent' },
  failed: { tone: 'danger', label: 'Failed' },
  pending: { tone: 'warning', label: 'Not confirmed' },
}

/** Money as whole cents, so amounts that arrive as numbers or strings compare exactly. */
const cents = (v) => Math.round(num(v) * 100)

/** `YYYY-MM` of a payout. `pay_time` is the server's wall clock without an offset, so it is read as text. */
const payMonth = (p) => p.pay_time.slice(0, 7)

/** First and last day of a period preset as date-input strings, '' for an open end. */
function presetSpan(preset) {
  const now = new Date()
  if (preset === 'last_month') return monthBounds(new Date(now.getFullYear(), now.getMonth() - 1, 1))
  if (preset === 'last_3_months') return { start: monthBounds(new Date(now.getFullYear(), now.getMonth() - 2, 1)).start, end: monthBounds(now).end }
  if (preset === 'all') return { start: '', end: '' }
  return monthBounds(now)
}

/**
 * The `YYYY-MM` months that get the "no payout" check: whole calendar months
 * inside the span, never a future one. Without dates the range runs from the
 * earliest payout to the current month.
 */
function monthsToCheck(from, to, payrolls) {
  const thisMonth = monthKey(new Date())
  const first = from ? from.slice(0, 7) : payrolls.map(payMonth).sort()[0] || thisMonth
  const last = to && to.slice(0, 7) < thisMonth ? to.slice(0, 7) : thisMonth
  const months = []
  let [year, month] = first.split('-').map(Number)
  while (`${year}-${String(month).padStart(2, '0')}` <= last) {
    const bounds = monthBounds(new Date(year, month - 1, 1))
    if ((!from || from <= bounds.start) && (!to || to >= bounds.end)) months.push(bounds.start.slice(0, 7))
    month += 1
    if (month > 12) {
      month = 1
      year += 1
    }
  }
  return months
}

/**
 * Turn the payout records into table rows with their checks, and add one
 * "missing" row per checked month for every active member who has a paycheck
 * from an earlier month but no payout in it. The checks compare with today's
 * paychecks and active flags, so they describe the past only as far as those
 * have not changed since.
 */
function auditRows(payrolls, paychecks, users, from, to) {
  const thisMonth = monthKey(new Date())
  const payoutRows = payrolls.map((p) => {
    const own = paychecks.filter((c) => c.user_id === p.user_id)
    const paidCount = payrolls.filter((o) => o.user_id === p.user_id && payMonth(o) === payMonth(p)).length
    return {
      ...p,
      kind: 'payout',
      month: payMonth(p),
      sortKey: p.pay_time,
      paidCount,
      paycheckCount: own.length,
      duplicate: paidCount > Math.max(1, own.length),
      differs: own.length > 0 && !own.some((c) => AMOUNT_KEYS.every((k) => cents(c[k]) === cents(p[k]))),
      noPaycheck: own.length === 0,
    }
  })

  const missingRows = []
  for (const month of monthsToCheck(from, to, payrolls)) {
    for (const user of users.filter((u) => u.is_active)) {
      // A paycheck set up during a month is expected from the following month on
      const due = paychecks.filter((c) => c.user_id === user.id && monthKey(c.created_at) < month)
      if (!due.length || payrolls.some((p) => p.user_id === user.id && payMonth(p) === month)) continue
      const row = { id: `missing-${user.id}-${month}`, kind: 'missing', user_id: user.id, month, pay_time: null, sortKey: `${month}-99`, current: month === thisMonth }
      for (const k of AMOUNT_KEYS) row[k] = due.reduce((s, c) => s + num(c[k]), 0)
      missingRows.push(row)
    }
  }
  return [...payoutRows, ...missingRows]
}

const needsAttention = (r) => r.kind === 'missing' || r.duplicate || r.differs || r.mail_status !== 'sent'

const VIEW_FILTER = {
  all: () => true,
  attention: needsAttention,
  mail_failed: (r) => r.mail_status === 'failed',
  mail_pending: (r) => r.mail_status === 'pending',
  missing: (r) => r.kind === 'missing',
  duplicate: (r) => Boolean(r.duplicate),
  differs: (r) => Boolean(r.differs),
}

/**
 * Payouts — what the monthly payroll run recorded, read-only. HR checks here
 * that every member was paid: each payout carries its payslip mail result, and
 * the checks point out members without a payout, members paid more often than
 * they have paychecks, and payouts that differ from the current paycheck.
 */
export default function PayrollsSection() {
  const { userOptions, userMap, nameOf } = useUsers()
  const [preset, setPreset] = useState('this_month')
  const [from, setFrom] = useState(() => monthBounds().start)
  const [to, setTo] = useState(() => monthBounds().end)
  // What the date inputs show; `from` / `to` only follow once the value is a whole date
  const [fromInput, setFromInput] = useState(from)
  const [toInput, setToInput] = useState(to)
  const [person, setPerson] = useState('')
  const [view, setView] = useState('all')

  const choosePreset = (value) => {
    setPreset(value)
    if (value === 'custom') return
    const span = presetSpan(value)
    setFrom(span.start)
    setTo(span.end)
    setFromInput(span.start)
    setToInput(span.end)
  }

  // A date input reports half-typed years such as 0002 or 0202 while the year is being typed, those must not reload the list
  const isWholeDate = (value) => value === '' || value >= '1900-01-01'

  // Whole months are loaded so the per-month checks see every payout of a month; inSpan narrows the rows again
  const fetcher = async () => {
    const startDate = from ? monthBounds(parseDate(from)).start : ''
    const endDate = to ? monthBounds(parseDate(to)).end : ''
    const [payrolls, paychecks, users] = await Promise.all([hrApi.listPayrolls({ start_date: startDate, end_date: endDate }), hrApi.listPaychecks(), hrApi.listUsers()])
    return auditRows(payrolls, paychecks, users, from, to)
  }

  const inSpan = (r) => r.kind === 'missing' || ((!from || r.pay_time.slice(0, 10) >= from) && (!to || r.pay_time.slice(0, 10) <= to))
  const filtered = Boolean(person) || view !== 'all'

  const rowsTransform = (rows) =>
    rows
      .filter(inSpan)
      .filter((r) => !person || String(r.user_id) === person)
      .filter(VIEW_FILTER[view])
      .sort((a, b) => b.sortKey.localeCompare(a.sortKey) || nameOf(a.user_id).localeCompare(nameOf(b.user_id)))

  const summary = (shown, all) => {
    const period = all.filter(inSpan)
    const payouts = period.filter((r) => r.kind === 'payout')
    const shownPayouts = shown.filter((r) => r.kind === 'payout')
    const missing = period.filter((r) => r.kind === 'missing')
    const failed = payouts.filter((r) => r.mail_status === 'failed')
    const pending = payouts.filter((r) => r.mail_status === 'pending')
    const duplicate = payouts.filter((r) => r.duplicate)
    const differs = payouts.filter((r) => r.differs)
    const attention = period.filter(needsAttention)
    const checked = monthsToCheck(from, to, all.filter((r) => r.kind === 'payout'))
    const paidMonths = new Set(payouts.map((r) => r.month)).size
    const net = (list) => list.reduce((s, r) => s + num(r.net_pay), 0)
    const tiles = [
      { k: 'Net paid out', v: currency(net(shownPayouts)), hint: filtered ? `${shownPayouts.length} of ${payouts.length} payouts in the period` : `${payouts.length} payout${payouts.length === 1 ? '' : 's'}` },
      { k: 'People paid', v: new Set(payouts.map((r) => r.user_id)).size, hint: `in ${paidMonths} month${paidMonths === 1 ? '' : 's'}` },
      { k: 'Payslip mail failed', v: failed.length, hint: `${pending.length} not confirmed`, accent: failed.length > 0 },
      { k: 'No payout', v: checked.length ? missing.length : '—', hint: checked.length ? `${checked.length} whole month${checked.length === 1 ? '' : 's'} checked` : 'needs a whole calendar month in the period', accent: missing.length > 0 },
      { k: 'Needs attention', v: attention.length, hint: `${missing.length} no payout · ${duplicate.length} extra · ${differs.length} differ · ${failed.length + pending.length} mail`, accent: attention.length > 0 },
    ]
    return (
      <div className="summary-row">
        {tiles.map((t) => (
          <div key={t.k} className={`summary-tile ${t.accent ? 'accent' : ''}`}>
            <span className="sum-k">{t.k}</span>
            <span className="sum-v">{t.v}</span>
            <span className="sum-hint">{t.hint}</span>
          </div>
        ))}
      </div>
    )
  }

  const amountCell = (r, key) => {
    if (key === 'deductions') return num(r.deductions) ? `−${currency(r.deductions)}` : '—'
    return currency(r[key])
  }

  return (
    <ResourceSection
      title="Payouts"
      subtitle="What the monthly payroll run recorded for each member. Read-only: check that everyone was paid and got their payslip."
      moduleName="People & Payroll"
      fetcher={fetcher}
      deps={[from, to]}
      emptyHint={filtered ? 'No payout matches these filters.' : 'No payout was recorded in this period.'}
      emptyIcon={Banknote}
      rowsTransform={rowsTransform}
      summary={summary}
      toolbarExtra={
        <>
          <Select value={preset} onChange={(e) => choosePreset(e.target.value)} aria-label="Period">
            <option value="this_month">This month</option>
            <option value="last_month">Last month</option>
            <option value="last_3_months">Last 3 months</option>
            <option value="all">All time</option>
            <option value="custom">Custom</option>
          </Select>
          <Input
            type="date"
            value={fromInput}
            max={to || undefined}
            onChange={(e) => {
              setFromInput(e.target.value)
              if (isWholeDate(e.target.value)) setFrom(e.target.value)
              setPreset('custom')
            }}
            aria-label="Paid from"
            title="Paid from"
          />
          <Input
            type="date"
            value={toInput}
            min={from || undefined}
            onChange={(e) => {
              setToInput(e.target.value)
              if (isWholeDate(e.target.value)) setTo(e.target.value)
              setPreset('custom')
            }}
            aria-label="Paid until"
            title="Paid until"
          />
          <Select value={person} onChange={(e) => setPerson(e.target.value)} aria-label="Filter by member">
            <option value="">All members</option>
            {userOptions.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </Select>
          <Select value={view} onChange={(e) => setView(e.target.value)} aria-label="Which payouts to show">
            <option value="all">All payouts</option>
            <option value="attention">Needs attention</option>
            <option value="mail_failed">Payslip mail failed</option>
            <option value="mail_pending">Payslip mail not confirmed</option>
            <option value="missing">No payout</option>
            <option value="duplicate">More payouts than paychecks</option>
            <option value="differs">Differs from current paycheck</option>
          </Select>
        </>
      }
      columns={[
        {
          key: 'pay_time',
          header: <span title="Server time">Paid on</span>,
          render: (r) =>
            r.kind === 'missing' ? (
              <span className="muted">{monthLabel(r.month)}</span>
            ) : (
              <span>
                {fmtDate(r.pay_time.slice(0, 10))}
                <span className="cell-sub">{r.pay_time.slice(11, 16)}</span>
              </span>
            ),
        },
        {
          key: 'user_id',
          header: 'Member',
          render: (r) => (
            <span className="row gap-1 wrap">
              <span className="cell-strong">{nameOf(r.user_id)}</span>
              {userMap[String(r.user_id)]?.is_active === false && <Badge tone="neutral">inactive</Badge>}
            </span>
          ),
        },
        { key: 'base_salary', header: 'Base', align: 'right', render: (r) => <span className={`cell-num ${r.kind === 'missing' ? 'muted' : ''}`}>{amountCell(r, 'base_salary')}</span> },
        { key: 'allowances', header: 'Allowances', align: 'right', render: (r) => <span className="cell-num muted">{amountCell(r, 'allowances')}</span> },
        { key: 'deductions', header: 'Deductions', align: 'right', render: (r) => <span className="cell-num muted">{amountCell(r, 'deductions')}</span> },
        {
          key: 'net_pay',
          header: 'Net pay',
          align: 'right',
          render: (r) =>
            r.kind === 'missing' ? (
              <span>
                <span className="cell-num muted">{amountCell(r, 'net_pay')}</span>
                <span className="cell-sub">expected</span>
              </span>
            ) : (
              <span className="cell-num cell-strong">{amountCell(r, 'net_pay')}</span>
            ),
        },
        {
          key: 'mail_status',
          header: 'Payslip mail',
          render: (r) => {
            if (r.kind === 'missing') return <span className="muted">—</span>
            const badge = MAIL_BADGE[r.mail_status] || { tone: 'neutral', label: r.mail_status }
            return (
              <span>
                <Badge tone={badge.tone} title={r.mail_error || undefined}>
                  {badge.label}
                </Badge>
                {r.mail_error && <span className="cell-sub">{r.mail_error}</span>}
              </span>
            )
          },
        },
        {
          key: 'checks',
          header: 'Checks',
          render: (r) => {
            if (r.kind === 'missing') return r.current ? <Badge tone="warning">No payout yet</Badge> : <Badge tone="danger">No payout</Badge>
            if (!r.duplicate && !r.differs && !r.noPaycheck) return <span className="muted">—</span>
            return (
              <span className="row gap-1 wrap">
                {r.duplicate && (
                  <Badge tone="warning" title={`${r.paycheckCount} paycheck${r.paycheckCount === 1 ? '' : 's'} on file`}>
                    {r.paidCount} payouts this month
                  </Badge>
                )}
                {r.differs && (
                  <Badge tone="info" title="The paycheck may have been edited after this payout">
                    Differs from current paycheck
                  </Badge>
                )}
                {r.noPaycheck && <Badge tone="neutral">No paycheck on file</Badge>}
              </span>
            )
          },
        },
      ]}
    />
  )
}
