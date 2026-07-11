import { useState } from 'react'
import { LogIn, LogOut, Pencil, Trash2 } from 'lucide-react'
import { hrApi } from '../../api/hr'
import { useList } from '../../lib/useList'
import { useToast } from '../../context/ToastContext'
import { num, date as fmtDate, dateTime, number } from '../../lib/format'
import Card from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import AccessDenied from '../../components/ui/AccessDenied'
import ConfirmDialog from '../../components/ui/ConfirmDialog'
import Modal from '../../components/ui/Modal'
import SessionList from '../../components/ui/SessionList'
import { Field, Input, Select } from '../../components/ui/Field'

const toLocalInput = (iso) => {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** Attendance clock in / out — POST-only, logs shown in a session list. */
export default function AttendanceSection() {
  const toast = useToast()
  const { rows: employees, denied } = useList(() => hrApi.listEmployees())
  const [selectedEmployee, setSelectedEmployee] = useState('')
  const [created, setCreated] = useState([])
  const [busy, setBusy] = useState(null)
  const [editing, setEditing] = useState(null)
  const [clockIn, setClockIn] = useState('')
  const [clockOut, setClockOut] = useState('')
  const [saving, setSaving] = useState(false)
  const [pendingRemove, setPendingRemove] = useState(null)
  const [removing, setRemoving] = useState(false)

  if (denied) return <AccessDenied module="People & HR" />

  const empMap = Object.fromEntries(
    (employees || []).map((e) => [String(e.id), `${e.first_name} ${e.last_name}`]),
  )

  const punch = async (kind) => {
    if (!selectedEmployee) {
      toast.error('Select an employee first')
      return
    }
    setBusy(kind)
    try {
      const id = num(selectedEmployee)
      const log = kind === 'in' ? await hrApi.clockIn(id) : await hrApi.clockOut(id)
      setCreated((c) => [log, ...c])
      toast.success(kind === 'in' ? 'Clocked in' : 'Clocked out')
    } catch (err) {
      toast.error(err?.detail || 'Could not record attendance')
    } finally {
      setBusy(null)
    }
  }

  const startEdit = (row) => {
    setEditing(row)
    setClockIn(toLocalInput(row.clock_in))
    setClockOut(toLocalInput(row.clock_out))
  }

  const saveEdit = async () => {
    if (!clockIn) {
      toast.error('Clock in is required')
      return
    }
    setSaving(true)
    try {
      const log = await hrApi.updateAttendance(editing.id, {
        clock_in: new Date(clockIn).toISOString(),
        clock_out: clockOut ? new Date(clockOut).toISOString() : null,
      })
      setCreated((c) => c.map((r) => (r.id === editing.id ? { ...log } : r)))
      toast.success('Attendance updated')
      setEditing(null)
    } catch (err) {
      toast.error(err?.detail || 'Could not update attendance')
    } finally {
      setSaving(false)
    }
  }

  const confirmRemove = async () => {
    setRemoving(true)
    try {
      await hrApi.deleteAttendance(pendingRemove.id)
      setCreated((c) => c.filter((r) => r.id !== pendingRemove.id))
      toast.success('Attendance log deleted')
      setPendingRemove(null)
    } catch (err) {
      toast.error(err?.detail || 'Could not delete attendance log')
    } finally {
      setRemoving(false)
    }
  }

  return (
    <div>
      <div className="section-toolbar">
        <div>
          <h2>Attendance</h2>
          <div className="muted">Clock team members in and out for the day.</div>
        </div>
      </div>

      <Card className="card-pad" style={{ maxWidth: 640 }}>
        <div className="col gap-4">
          <Field label="Employee" required>
            <Select value={selectedEmployee} onChange={(e) => setSelectedEmployee(e.target.value)}>
              <option value="">
                {employees && employees.length ? 'Select employee…' : 'No employees — add one first'}
              </option>
              {(employees || []).map((e) => (
                <option key={e.id} value={String(e.id)}>
                  {`${e.first_name} ${e.last_name}`}
                </option>
              ))}
            </Select>
          </Field>
          <div className="row" style={{ justifyContent: 'flex-end', gap: 8 }}>
            <Button variant="outline" icon={LogIn} loading={busy === 'in'} onClick={() => punch('in')}>
              Clock in
            </Button>
            <Button icon={LogOut} loading={busy === 'out'} onClick={() => punch('out')}>
              Clock out
            </Button>
          </div>
        </div>
      </Card>

      <SessionList
        items={created}
        title="Attendance recorded this session"
        columns={[
          { key: 'employee', header: 'Employee', render: (r) => empMap[String(r.employee_id)] || `#${r.employee_id}` },
          { key: 'date', header: 'Date', render: (r) => fmtDate(r.date) },
          { key: 'clock_in', header: 'Clock in', render: (r) => dateTime(r.clock_in) },
          { key: 'clock_out', header: 'Clock out', render: (r) => (r.clock_out ? dateTime(r.clock_out) : '—') },
          { key: 'total_hours', header: 'Hours', align: 'right', render: (r) => (r.total_hours == null ? '—' : number(r.total_hours)) },
          {
            key: 'actions',
            header: '',
            align: 'right',
            render: (r) => (
              <span className="row-actions">
                <button
                  type="button"
                  className="icon-btn"
                  onClick={() => startEdit(r)}
                  aria-label="Edit attendance"
                >
                  <Pencil size={15} />
                </button>
                <button
                  type="button"
                  className="icon-btn line-remove"
                  onClick={() => setPendingRemove(r)}
                  aria-label="Delete attendance"
                >
                  <Trash2 size={15} />
                </button>
              </span>
            ),
          },
        ]}
      />

      <Modal
        open={!!editing}
        onClose={saving ? undefined : () => setEditing(null)}
        title="Edit attendance"
        subtitle={editing ? empMap[String(editing.employee_id)] || `#${editing.employee_id}` : undefined}
        footer={
          <>
            <Button variant="ghost" onClick={() => setEditing(null)} disabled={saving}>
              Cancel
            </Button>
            <Button onClick={saveEdit} loading={saving}>
              Save
            </Button>
          </>
        }
      >
        <div className="col gap-4">
          <Field label="Clock in" required>
            <Input type="datetime-local" value={clockIn} onChange={(e) => setClockIn(e.target.value)} />
          </Field>
          <Field label="Clock out">
            <Input type="datetime-local" value={clockOut} onChange={(e) => setClockOut(e.target.value)} />
          </Field>
        </div>
      </Modal>

      <ConfirmDialog
        open={!!pendingRemove}
        onClose={() => setPendingRemove(null)}
        onConfirm={confirmRemove}
        loading={removing}
        title="Delete attendance log"
        message="This will permanently delete this attendance log."
        hint={pendingRemove ? `${empMap[String(pendingRemove.employee_id)] || `#${pendingRemove.employee_id}`} · ${fmtDate(pendingRemove.date)}` : undefined}
      />
    </div>
  )
}
