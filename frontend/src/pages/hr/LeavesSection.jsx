import { useState } from 'react'
import { CalendarDays, Check, X } from 'lucide-react'
import { hrApi } from '../../api/hr'
import { useAuth } from '../../context/AuthContext'
import { useUsers } from '../../lib/useUsers'
import { date as fmtDate, today, titleize, daysBetween, parseDate } from '../../lib/format'
import Badge from '../../components/ui/Badge'
import ResourceSection from '../../components/ResourceSection'
import { Select } from '../../components/ui/Field'

const LEAVE_TYPES = ['annual', 'sick', 'unpaid', 'parental'].map((v) => ({ value: v, label: titleize(v) }))
const STATUSES = ['pending', 'approved', 'rejected'].map((v) => ({ value: v, label: titleize(v) }))

/** Leave requests with a one-click approve / reject that records the approver. */
export default function LeavesSection() {
  const { user: me } = useAuth()
  const { userOptions, nameOf } = useUsers()
  const [statusFilter, setStatusFilter] = useState('')

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
    { key: 'leave_type', label: 'Leave type', type: 'select', required: true, options: LEAVE_TYPES, default: 'annual' },
    { key: 'status', label: 'Status', type: 'select', options: STATUSES, default: 'pending' },
    { key: 'start_date', label: 'Start date', type: 'date', required: true, default: today() },
    { key: 'end_date', label: 'End date', type: 'date', required: true, default: today() },
    { key: 'reason', label: 'Reason', type: 'textarea', full: true, placeholder: 'Optional note for the approver' },
  ]

  const decide = async (r, status, { reload, toast }) => {
    try {
      await hrApi.updateLeave(r.id, { status, approved_by_id: me?.id })
      toast.success(`Leave ${status} for ${nameOf(r.user_id)}`)
      reload()
    } catch (err) {
      toast.error(err?.detail || 'Could not update leave request')
    }
  }

  const rowsTransform = (rows) =>
    [...rows]
      .filter((r) => !statusFilter || r.status === statusFilter)
      .sort((a, b) => (parseDate(b.start_date) ?? 0) - (parseDate(a.start_date) ?? 0) || b.id - a.id)

  const summary = (rows) => {
    const count = (s) => rows.filter((r) => r.status === s).length
    const days = rows
      .filter((r) => r.status === 'approved')
      .reduce((s, r) => s + daysBetween(r.start_date, r.end_date), 0)
    return (
      <div className="summary-row">
        <div className={`summary-tile ${count('pending') ? 'accent' : ''}`}>
          <span className="sum-k">Pending</span>
          <span className="sum-v">{count('pending')}</span>
          <span className="sum-hint">awaiting a decision</span>
        </div>
        <div className="summary-tile">
          <span className="sum-k">Approved</span>
          <span className="sum-v">{count('approved')}</span>
          <span className="sum-hint">{days} day{days === 1 ? '' : 's'} off in total</span>
        </div>
        <div className="summary-tile">
          <span className="sum-k">Rejected</span>
          <span className="sum-v">{count('rejected')}</span>
        </div>
      </div>
    )
  }

  return (
    <ResourceSection
      title="Leave requests"
      subtitle="Time off per member, and who approved it."
      moduleName="People & Payroll"
      fetcher={() => hrApi.listLeaves()}
      create={hrApi.createLeave}
      createLabel="New request"
      createTitle="New leave request"
      update={(row, payload) => hrApi.updateLeave(row.id, payload)}
      updateTitle="Edit leave request"
      remove={(row) => hrApi.deleteLeave(row.id)}
      removeLabel="leave request"
      removeHint={(r) => `${nameOf(r.user_id)} · ${titleize(r.leave_type)} · ${fmtDate(r.start_date)} – ${fmtDate(r.end_date)}`}
      emptyHint="Log the first leave request for a team member."
      emptyIcon={CalendarDays}
      fields={fields}
      rowsTransform={rowsTransform}
      summary={summary}
      toolbarExtra={
        <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} aria-label="Filter by status">
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </Select>
      }
      rowActions={(r, helpers) =>
        r.status === 'pending' ? (
          <>
            <button type="button" className="icon-btn" title="Approve" aria-label="Approve" onClick={() => decide(r, 'approved', helpers)}>
              <Check size={15} color="var(--success)" />
            </button>
            <button type="button" className="icon-btn" title="Reject" aria-label="Reject" onClick={() => decide(r, 'rejected', helpers)}>
              <X size={15} color="var(--danger)" />
            </button>
          </>
        ) : null
      }
      columns={[
        { key: 'user_id', header: 'Member', render: (r) => <span className="cell-strong">{nameOf(r.user_id)}</span> },
        { key: 'leave_type', header: 'Type', render: (r) => <Badge status={r.leave_type} /> },
        {
          key: 'dates',
          header: 'Dates',
          render: (r) => (
            <span style={{ whiteSpace: 'nowrap' }}>
              {fmtDate(r.start_date)} – {fmtDate(r.end_date)}
            </span>
          ),
        },
        { key: 'days', header: 'Days', align: 'right', render: (r) => <span className="cell-num">{daysBetween(r.start_date, r.end_date)}</span> },
        { key: 'reason', header: 'Reason', render: (r) => <span className="cell-sub">{r.reason || '—'}</span> },
        { key: 'status', header: 'Status', render: (r) => <Badge status={r.status} /> },
        { key: 'approved_by_id', header: 'Decided by', render: (r) => <span className="muted">{r.approved_by_id ? nameOf(r.approved_by_id) : '—'}</span> },
      ]}
    />
  )
}
