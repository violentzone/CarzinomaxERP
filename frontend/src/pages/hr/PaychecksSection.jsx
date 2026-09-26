import { useState } from 'react'
import { Wallet, CheckCircle2 } from 'lucide-react'
import { hrApi } from '../../api/hr'
import { useUsers } from '../../lib/useUsers'
import { num, currency, date as fmtDate, today, monthBounds, monthKey, parseDate } from '../../lib/format'
import Badge from '../../components/ui/Badge'
import ResourceSection from '../../components/ResourceSection'
import { Select } from '../../components/ui/Field'

const STATUSES = [
  { value: 'draft', label: 'Draft' },
  { value: 'paid', label: 'Paid' },
]

/**
 * Paychecks — one record per member per pay period. Net pay is base +
 * allowances − deductions; the backend computes it when omitted on create, and
 * we recompute it on edit unless a value was typed explicitly.
 */
export default function PaychecksSection() {
  const { userOptions, nameOf } = useUsers()
  const [statusFilter, setStatusFilter] = useState('')
  const [personFilter, setPersonFilter] = useState('')

  const fields = [
    {
      key: 'user_id',
      label: 'Member',
      type: 'select',
      numeric: true,
      required: true,
      full: true,
      options: userOptions,
      placeholder: userOptions.length ? 'Select a member…' : 'No users — create one first',
    },
    { key: 'pay_period_start', label: 'Period start', type: 'date', required: true, default: monthBounds().start },
    { key: 'pay_period_end', label: 'Period end', type: 'date', required: true, default: monthBounds().end },
    { key: 'base_salary', label: 'Base salary', type: 'number', step: '0.01', min: 0, required: true },
    { key: 'allowances', label: 'Allowances', type: 'number', step: '0.01', min: 0, default: 0 },
    { key: 'deductions', label: 'Deductions', type: 'number', step: '0.01', min: 0, default: 0 },
    { key: 'net_pay', label: 'Net pay', type: 'number', step: '0.01', hint: 'Leave blank to compute base + allowances − deductions.' },
    { key: 'payment_date', label: 'Payment date', type: 'date', required: true, default: today() },
    { key: 'status', label: 'Status', type: 'select', options: STATUSES, default: 'draft' },
  ]

  /** Keep net_pay consistent when the amounts change and no override was typed. */
  const preparePayload = (payload, editing, values) => {
    const typed = values.net_pay !== '' && values.net_pay !== undefined && values.net_pay !== null
    const base = payload.base_salary ?? num(editing?.base_salary)
    const allow = payload.allowances ?? num(editing?.allowances)
    const ded = payload.deductions ?? num(editing?.deductions)
    if (!typed) payload.net_pay = Math.round((base + allow - ded) * 100) / 100
    return payload
  }

  const rowsTransform = (rows) =>
    [...rows]
      .filter((r) => !statusFilter || r.status === statusFilter)
      .filter((r) => !personFilter || String(r.user_id) === personFilter)
      .sort((a, b) => (parseDate(b.payment_date) ?? 0) - (parseDate(a.payment_date) ?? 0) || b.id - a.id)

  const summary = (rows) => {
    const paid = rows.filter((r) => r.status === 'paid')
    const draft = rows.filter((r) => r.status !== 'paid')
    const thisMonth = monthKey(today())
    const monthTotal = rows
      .filter((r) => monthKey(r.payment_date) === thisMonth)
      .reduce((s, r) => s + num(r.net_pay), 0)
    return (
      <div className="summary-row">
        <div className="summary-tile accent">
          <span className="sum-k">Paid out</span>
          <span className="sum-v">{currency(paid.reduce((s, r) => s + num(r.net_pay), 0))}</span>
          <span className="sum-hint">{paid.length} paycheck{paid.length === 1 ? '' : 's'}</span>
        </div>
        <div className="summary-tile">
          <span className="sum-k">Awaiting payment</span>
          <span className="sum-v">{currency(draft.reduce((s, r) => s + num(r.net_pay), 0))}</span>
          <span className="sum-hint">{draft.length} draft{draft.length === 1 ? '' : 's'}</span>
        </div>
        <div className="summary-tile">
          <span className="sum-k">This month</span>
          <span className="sum-v">{currency(monthTotal)}</span>
          <span className="sum-hint">by payment date</span>
        </div>
        <div className="summary-tile">
          <span className="sum-k">People paid</span>
          <span className="sum-v">{new Set(rows.map((r) => r.user_id)).size}</span>
          <span className="sum-hint">distinct members</span>
        </div>
      </div>
    )
  }

  return (
    <ResourceSection
      title="Paychecks"
      subtitle="Every payment made to an individual member, by pay period."
      moduleName="People & Payroll"
      fetcher={() => hrApi.listPaychecks()}
      create={hrApi.createPaycheck}
      createLabel="New paycheck"
      createTitle="New paycheck"
      update={(row, payload) => hrApi.updatePaycheck(row.id, payload)}
      updateTitle="Edit paycheck"
      remove={(row) => hrApi.deletePaycheck(row.id)}
      removeLabel="paycheck"
      removeHint={(r) => `${nameOf(r.user_id)} · ${fmtDate(r.payment_date)} · net ${currency(r.net_pay)}`}
      emptyHint="Record the first payment to a team member."
      emptyIcon={Wallet}
      fields={fields}
      preparePayload={preparePayload}
      rowsTransform={rowsTransform}
      summary={summary}
      toolbarExtra={
        <>
          <Select value={personFilter} onChange={(e) => setPersonFilter(e.target.value)} aria-label="Filter by member">
            <option value="">All members</option>
            {userOptions.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </Select>
          <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} aria-label="Filter by status">
            <option value="">All statuses</option>
            {STATUSES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </Select>
        </>
      }
      rowActions={(r, { reload, toast }) =>
        r.status !== 'paid' ? (
          <button
            type="button"
            className="icon-btn"
            title="Mark as paid"
            aria-label="Mark as paid"
            onClick={async () => {
              try {
                await hrApi.updatePaycheck(r.id, { status: 'paid' })
                toast.success(`Paycheck for ${nameOf(r.user_id)} marked paid`)
                reload()
              } catch (err) {
                toast.error(err?.detail || 'Could not update paycheck')
              }
            }}
          >
            <CheckCircle2 size={15} color="var(--success)" />
          </button>
        ) : null
      }
      columns={[
        { key: 'user_id', header: 'Member', render: (r) => <span className="cell-strong">{nameOf(r.user_id)}</span> },
        {
          key: 'period',
          header: 'Pay period',
          render: (r) => (
            <span className="muted" style={{ whiteSpace: 'nowrap' }}>
              {fmtDate(r.pay_period_start)} – {fmtDate(r.pay_period_end)}
            </span>
          ),
        },
        { key: 'base_salary', header: 'Base', align: 'right', render: (r) => <span className="cell-num">{currency(r.base_salary)}</span> },
        { key: 'allowances', header: 'Allowances', align: 'right', render: (r) => <span className="cell-num muted">{currency(r.allowances)}</span> },
        { key: 'deductions', header: 'Deductions', align: 'right', render: (r) => <span className="cell-num muted">{num(r.deductions) ? `−${currency(r.deductions)}` : '—'}</span> },
        { key: 'net_pay', header: 'Net pay', align: 'right', render: (r) => <span className="cell-num cell-strong">{currency(r.net_pay)}</span> },
        { key: 'payment_date', header: 'Paid on', className: 'nowrap', render: (r) => fmtDate(r.payment_date) },
        { key: 'status', header: 'Status', render: (r) => <Badge status={r.status} /> },
      ]}
    />
  )
}
