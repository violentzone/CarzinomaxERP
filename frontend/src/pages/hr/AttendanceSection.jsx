import { useState } from 'react'
import { Clock, LogIn, LogOut } from 'lucide-react'
import { hrApi } from '../../api/hr'
import { useUsers } from '../../lib/useUsers'
import { num, number, date as fmtDate, time as fmtTime, today, toLocalInput, hoursBetween, parseDate } from '../../lib/format'
import ResourceSection from '../../components/ResourceSection'
import Button from '../../components/ui/Button'
import { Select } from '../../components/ui/Field'

/**
 * Attendance logs. The quick punch bar clocks a member in (new log at "now")
 * or out (closes their latest open log and fills in total hours); the table
 * below is the full CRUD view of every log.
 */
export default function AttendanceSection() {
  const { userOptions, nameOf } = useUsers()
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
    { key: 'date', label: 'Date', type: 'date', required: true, default: today() },
    { key: 'total_hours', label: 'Total hours', type: 'number', step: '0.01', min: 0, hint: 'Leave blank to compute from clock in/out.' },
    { key: 'clock_in', label: 'Clock in', type: 'datetime-local', required: true, default: toLocalInput(new Date().toISOString()) },
    { key: 'clock_out', label: 'Clock out', type: 'datetime-local', nullable: true },
  ]

  const preparePayload = (payload, editing, values) => {
    const typed = values.total_hours !== '' && values.total_hours !== undefined && values.total_hours !== null
    const cin = payload.clock_in ?? editing?.clock_in
    const cout = payload.clock_out ?? editing?.clock_out
    if (!typed) {
      const h = hoursBetween(cin, cout)
      if (h !== null) payload.total_hours = h
    }
    return payload
  }

  const rowsTransform = (rows) =>
    [...rows]
      .filter((r) => !personFilter || String(r.user_id) === personFilter)
      .sort((a, b) => (parseDate(b.date) ?? 0) - (parseDate(a.date) ?? 0) || new Date(b.clock_in) - new Date(a.clock_in))

  const summary = (rows) => {
    const open = rows.filter((r) => !r.clock_out).length
    const hours = rows.reduce((s, r) => s + num(r.total_hours), 0)
    const todayRows = rows.filter((r) => r.date === today())
    return (
      <div className="summary-row">
        <div className={`summary-tile ${open ? 'accent' : ''}`}>
          <span className="sum-k">Clocked in now</span>
          <span className="sum-v">{open}</span>
          <span className="sum-hint">open logs without a clock out</span>
        </div>
        <div className="summary-tile">
          <span className="sum-k">Today</span>
          <span className="sum-v">{todayRows.length}</span>
          <span className="sum-hint">{number(todayRows.reduce((s, r) => s + num(r.total_hours), 0))} h logged</span>
        </div>
        <div className="summary-tile">
          <span className="sum-k">Total hours</span>
          <span className="sum-v">{number(hours)}</span>
          <span className="sum-hint">across {rows.length} log{rows.length === 1 ? '' : 's'}</span>
        </div>
      </div>
    )
  }

  return (
    <ResourceSection
      title="Attendance"
      subtitle="Clock members in and out, or edit any log by hand."
      moduleName="People & Payroll"
      fetcher={() => hrApi.listAttendance()}
      create={hrApi.createAttendance}
      createLabel="New log"
      createTitle="New attendance log"
      update={(row, payload) => hrApi.updateAttendance(row.id, payload)}
      updateTitle="Edit attendance log"
      remove={(row) => hrApi.deleteAttendance(row.id)}
      removeLabel="attendance log"
      removeHint={(r) => `${nameOf(r.user_id)} · ${fmtDate(r.date)}`}
      emptyHint="Use the punch bar to clock someone in, or add a log manually."
      emptyIcon={Clock}
      fields={fields}
      preparePayload={preparePayload}
      rowsTransform={rowsTransform}
      summary={summary}
      toolbarExtra={({ reload, toast }) => (
        <>
          <QuickPunch userOptions={userOptions} nameOf={nameOf} reload={reload} toast={toast} />
          <Select value={personFilter} onChange={(e) => setPersonFilter(e.target.value)} aria-label="Filter by member">
            <option value="">All members</option>
            {userOptions.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </Select>
        </>
      )}
      columns={[
        { key: 'user_id', header: 'Member', render: (r) => <span className="cell-strong">{nameOf(r.user_id)}</span> },
        { key: 'date', header: 'Date', className: 'nowrap', render: (r) => fmtDate(r.date) },
        { key: 'clock_in', header: 'In', render: (r) => fmtTime(r.clock_in) },
        {
          key: 'clock_out',
          header: 'Out',
          render: (r) => (r.clock_out ? fmtTime(r.clock_out) : <span className="badge badge-success"><span className="badge-dot" />On the clock</span>),
        },
        {
          key: 'total_hours',
          header: 'Hours',
          align: 'right',
          render: (r) => <span className="cell-num">{r.total_hours == null ? '—' : number(r.total_hours)}</span>,
        },
      ]}
    />
  )
}

function QuickPunch({ userOptions, nameOf, reload, toast }) {
  const [userId, setUserId] = useState('')
  const [busy, setBusy] = useState(null)

  const clockIn = async () => {
    if (!userId) return toast.error('Pick a member first')
    setBusy('in')
    try {
      const now = new Date()
      await hrApi.createAttendance({ user_id: num(userId), date: today(), clock_in: now.toISOString() })
      toast.success(`${nameOf(userId)} clocked in`)
      reload()
    } catch (err) {
      toast.error(err?.detail || 'Could not clock in')
    } finally {
      setBusy(null)
    }
  }

  const clockOut = async () => {
    if (!userId) return toast.error('Pick a member first')
    setBusy('out')
    try {
      const logs = await hrApi.listAttendance()
      const open = (logs || [])
        .filter((l) => String(l.user_id) === String(userId) && !l.clock_out)
        .sort((a, b) => new Date(b.clock_in) - new Date(a.clock_in))[0]
      if (!open) {
        toast.error(`${nameOf(userId)} has no open clock-in`)
        return
      }
      const now = new Date().toISOString()
      const hours = hoursBetween(open.clock_in, now)
      await hrApi.updateAttendance(open.id, hours === null ? { clock_out: now } : { clock_out: now, total_hours: hours })
      toast.success(`${nameOf(userId)} clocked out`)
      reload()
    } catch (err) {
      toast.error(err?.detail || 'Could not clock out')
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="punch-bar">
      <Select value={userId} onChange={(e) => setUserId(e.target.value)} aria-label="Member to punch">
        <option value="">{userOptions.length ? 'Punch: select member…' : 'No users yet'}</option>
        {userOptions.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </Select>
      <Button variant="outline" size="sm" icon={LogIn} loading={busy === 'in'} onClick={clockIn}>
        Clock in
      </Button>
      <Button variant="subtle" size="sm" icon={LogOut} loading={busy === 'out'} onClick={clockOut}>
        Clock out
      </Button>
    </div>
  )
}
