import { useState } from 'react'
import { LogIn, LogOut } from 'lucide-react'
import { hrApi } from '../../api/hr'
import { useList } from '../../lib/useList'
import { useToast } from '../../context/ToastContext'
import { num, date as fmtDate, dateTime, number } from '../../lib/format'
import Card from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import AccessDenied from '../../components/ui/AccessDenied'
import SessionList from '../../components/ui/SessionList'
import { Field, Select } from '../../components/ui/Field'

/** Attendance clock in / out — POST-only, logs shown in a session list. */
export default function AttendanceSection() {
  const toast = useToast()
  const { rows: employees, denied } = useList(() => hrApi.listEmployees())
  const [selectedEmployee, setSelectedEmployee] = useState('')
  const [created, setCreated] = useState([])
  const [busy, setBusy] = useState(null)

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
        ]}
      />
    </div>
  )
}
