import { useState } from 'react'
import { CalendarDays, Pencil, Trash2, X } from 'lucide-react'
import { hrApi } from '../../api/hr'
import { useList } from '../../lib/useList'
import { useToast } from '../../context/ToastContext'
import { num, date as fmtDate, today, titleize } from '../../lib/format'
import Card from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import Badge from '../../components/ui/Badge'
import AccessDenied from '../../components/ui/AccessDenied'
import ConfirmDialog from '../../components/ui/ConfirmDialog'
import SessionList from '../../components/ui/SessionList'
import { SchemaForm } from '../../components/SchemaForm'

const LEAVE_TYPES = ['annual', 'sick', 'unpaid', 'parental'].map((v) => ({ value: v, label: titleize(v) }))
const STATUSES = ['pending', 'approved', 'rejected'].map((v) => ({ value: v, label: titleize(v) }))

/** Leave requests are POST-only — created rows are shown in a session list. */
export default function LeavesSection() {
  const toast = useToast()
  const { rows: employees, denied } = useList(() => hrApi.listEmployees())
  const [values, setValues] = useState({ leave_type: 'annual', start_date: today(), end_date: today(), status: 'pending' })
  const [created, setCreated] = useState([])
  const [saving, setSaving] = useState(false)
  const [editingId, setEditingId] = useState(null) // leave request being edited, null = create
  const [pendingRemove, setPendingRemove] = useState(null)
  const [removing, setRemoving] = useState(false)

  if (denied) return <AccessDenied module="People & HR" />

  const empMap = Object.fromEntries(
    (employees || []).map((e) => [String(e.id), `${e.first_name} ${e.last_name}`]),
  )
  const employeeOptions = (employees || []).map((e) => ({ value: String(e.id), label: `${e.first_name} ${e.last_name}` }))

  const fields = [
    { key: 'employee_id', label: 'Employee', type: 'select', required: true, options: employeeOptions, placeholder: employeeOptions.length ? 'Select employee…' : 'No employees — add one first', full: true },
    { key: 'leave_type', label: 'Leave type', type: 'select', options: LEAVE_TYPES, default: 'annual' },
    { key: 'status', label: 'Status', type: 'select', options: STATUSES, default: 'pending' },
    { key: 'start_date', label: 'Start date', type: 'date', required: true, default: today() },
    { key: 'end_date', label: 'End date', type: 'date', required: true, default: today() },
    { key: 'reason', label: 'Reason', type: 'textarea', full: true, placeholder: 'Optional note for the approver' },
  ]

  const resetForm = () => {
    setEditingId(null)
    setValues({ leave_type: 'annual', start_date: today(), end_date: today(), status: 'pending' })
  }

  const submit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const payload = {
        employee_id: num(values.employee_id),
        leave_type: values.leave_type || 'annual',
        start_date: values.start_date,
        end_date: values.end_date,
        reason: values.reason || (editingId ? null : undefined),
        status: values.status || 'pending',
      }
      if (editingId) {
        const leave = await hrApi.updateLeave(editingId, payload)
        setCreated((c) => c.map((l) => (l.id === editingId ? { ...leave } : l)))
        toast.success('Leave request updated')
      } else {
        const leave = await hrApi.createLeave(payload)
        setCreated((c) => [{ ...leave }, ...c])
        toast.success('Leave request submitted')
      }
      resetForm()
    } catch (err) {
      toast.error(err?.detail || (editingId ? 'Could not update leave request' : 'Could not submit leave request'))
    } finally {
      setSaving(false)
    }
  }

  const startEdit = (row) => {
    setEditingId(row.id)
    setValues({
      employee_id: String(row.employee_id),
      leave_type: row.leave_type,
      start_date: row.start_date,
      end_date: row.end_date,
      reason: row.reason ?? '',
      status: row.status || 'pending',
    })
  }

  const confirmRemove = async () => {
    setRemoving(true)
    try {
      await hrApi.deleteLeave(pendingRemove.id)
      setCreated((c) => c.filter((l) => l.id !== pendingRemove.id))
      if (pendingRemove.id === editingId) resetForm()
      toast.success('Leave request deleted')
      setPendingRemove(null)
    } catch (err) {
      toast.error(err?.detail || 'Could not delete leave request')
    } finally {
      setRemoving(false)
    }
  }

  return (
    <div>
      <div className="section-toolbar">
        <div>
          <h2>{editingId ? `Edit leave request #${editingId}` : 'Request leave'}</h2>
          <div className="muted">Log time off for an employee and track its approval.</div>
        </div>
        {editingId && (
          <Button variant="outline" icon={X} onClick={resetForm}>
            Cancel edit
          </Button>
        )}
      </div>

      <Card className="card-pad" style={{ maxWidth: 640 }}>
        <form onSubmit={submit} className="col gap-4">
          <SchemaForm fields={fields} values={values} setField={(k, v) => setValues((s) => ({ ...s, [k]: v }))} />
          <div className="row" style={{ justifyContent: 'flex-end' }}>
            <Button type="submit" icon={editingId ? Pencil : CalendarDays} loading={saving}>
              {editingId ? 'Save changes' : 'Submit request'}
            </Button>
          </div>
        </form>
      </Card>

      <SessionList
        items={created}
        title="Leave requests this session"
        columns={[
          { key: 'employee', header: 'Employee', render: (r) => empMap[String(r.employee_id)] || `#${r.employee_id}` },
          { key: 'leave_type', header: 'Type', render: (r) => titleize(r.leave_type) },
          { key: 'start_date', header: 'Start', render: (r) => fmtDate(r.start_date) },
          { key: 'end_date', header: 'End', render: (r) => fmtDate(r.end_date) },
          { key: 'status', header: 'Status', render: (r) => <Badge status={r.status} /> },
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
                  aria-label="Edit leave request"
                >
                  <Pencil size={15} />
                </button>
                <button
                  type="button"
                  className="icon-btn line-remove"
                  onClick={() => setPendingRemove(r)}
                  aria-label="Delete leave request"
                >
                  <Trash2 size={15} />
                </button>
              </span>
            ),
          },
        ]}
      />

      <ConfirmDialog
        open={!!pendingRemove}
        onClose={() => setPendingRemove(null)}
        onConfirm={confirmRemove}
        loading={removing}
        title="Delete leave request"
        message="This will permanently delete this leave request."
        hint={pendingRemove ? `${empMap[String(pendingRemove.employee_id)] || `#${pendingRemove.employee_id}`} · ${titleize(pendingRemove.leave_type)} · ${fmtDate(pendingRemove.start_date)} – ${fmtDate(pendingRemove.end_date)}` : undefined}
      />
    </div>
  )
}
