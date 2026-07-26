import { useState } from 'react'
import { Wallet, Pencil, Trash2, X } from 'lucide-react'
import { hrApi } from '../../api/hr'
import { useList } from '../../lib/useList'
import { useToast } from '../../context/ToastContext'
import { num, currency, date as fmtDate, today } from '../../lib/format'
import Card from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import Badge from '../../components/ui/Badge'
import AccessDenied from '../../components/ui/AccessDenied'
import ConfirmDialog from '../../components/ui/ConfirmDialog'
import SessionList from '../../components/ui/SessionList'
import { SchemaForm } from '../../components/SchemaForm'

const STATUSES = [
  { value: 'draft', label: 'Draft' },
  { value: 'paid', label: 'Paid' },
]

/** Paychecks are POST-only — created rows are shown in a session list. */
export default function PaychecksSection() {
  const toast = useToast()
  const { rows: employees, denied } = useList(() => hrApi.listEmployees())
  const [values, setValues] = useState({ pay_period_start: today(), pay_period_end: today(), payment_date: today(), status: 'draft' })
  const [created, setCreated] = useState([])
  const [saving, setSaving] = useState(false)
  const [editingId, setEditingId] = useState(null) // paycheck being edited, null = create
  const [pendingRemove, setPendingRemove] = useState(null)
  const [removing, setRemoving] = useState(false)

  if (denied) return <AccessDenied module="People & HR" />

  const empMap = Object.fromEntries(
    (employees || []).map((e) => [String(e.id), `${e.first_name} ${e.last_name}`]),
  )
  const employeeOptions = (employees || []).map((e) => ({ value: String(e.id), label: `${e.first_name} ${e.last_name}` }))

  const netPay = num(values.base_salary) + num(values.allowances) - num(values.deductions)

  const fields = [
    { key: 'employee_id', label: 'Employee', type: 'select', required: true, options: employeeOptions, placeholder: employeeOptions.length ? 'Select employee…' : 'No employees — add one first', full: true },
    { key: 'pay_period_start', label: 'Period start', type: 'date', required: true, default: today() },
    { key: 'pay_period_end', label: 'Period end', type: 'date', required: true, default: today() },
    { key: 'base_salary', label: 'Base salary', type: 'number', step: '0.01', min: 0, required: true },
    { key: 'allowances', label: 'Allowances', type: 'number', step: '0.01', min: 0 },
    { key: 'deductions', label: 'Deductions', type: 'number', step: '0.01', min: 0 },
    { key: 'payment_date', label: 'Payment date', type: 'date', default: today() },
    { key: 'status', label: 'Status', type: 'select', options: STATUSES, default: 'draft' },
  ]

  const handleSetField = (k, v) => {
    setValues((s) => {
      const next = { ...s, [k]: v }
      if (k === 'employee_id' && v) {
        const selectedEmp = (employees || []).find((e) => String(e.id) === String(v))
        if (selectedEmp && selectedEmp.salary) {
          next.base_salary = selectedEmp.salary
        }
      }
      return next
    })
  }

  const resetForm = () => {
    setEditingId(null)
    setValues({ pay_period_start: today(), pay_period_end: today(), payment_date: today(), status: 'draft' })
  }

  const submit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const payload = {
        employee_id: num(values.employee_id),
        pay_period_start: values.pay_period_start,
        pay_period_end: values.pay_period_end,
        base_salary: num(values.base_salary),
        allowances: num(values.allowances),
        deductions: num(values.deductions),
        payment_date: values.payment_date || (editingId ? null : undefined),
        status: values.status || 'draft',
      }
      if (editingId) {
        const paycheck = await hrApi.updatePaycheck(editingId, payload)
        setCreated((c) => c.map((p) => (p.id === editingId ? { ...paycheck } : p)))
        toast.success('Paycheck updated')
      } else {
        const paycheck = await hrApi.createPaycheck(payload)
        setCreated((c) => [{ ...paycheck }, ...c])
        toast.success('Paycheck generated')
      }
      resetForm()
    } catch (err) {
      toast.error(err?.detail || (editingId ? 'Could not update paycheck' : 'Could not generate paycheck'))
    } finally {
      setSaving(false)
    }
  }

  const startEdit = (row) => {
    setEditingId(row.id)
    setValues({
      employee_id: String(row.employee_id),
      pay_period_start: row.pay_period_start,
      pay_period_end: row.pay_period_end,
      base_salary: row.base_salary,
      allowances: row.allowances,
      deductions: row.deductions,
      payment_date: row.payment_date || '',
      status: row.status || 'draft',
    })
  }

  const confirmRemove = async () => {
    setRemoving(true)
    try {
      await hrApi.deletePaycheck(pendingRemove.id)
      setCreated((c) => c.filter((p) => p.id !== pendingRemove.id))
      if (pendingRemove.id === editingId) resetForm()
      toast.success('Paycheck deleted')
      setPendingRemove(null)
    } catch (err) {
      toast.error(err?.detail || 'Could not delete paycheck')
    } finally {
      setRemoving(false)
    }
  }

  return (
    <div>
      <div className="section-toolbar">
        <div>
          <h2>{editingId ? `Edit paycheck #${editingId}` : 'Generate paycheck'}</h2>
          <div className="muted">Net pay is base salary plus allowances, less deductions.</div>
        </div>
        {editingId && (
          <Button variant="outline" icon={X} onClick={resetForm}>
            Cancel edit
          </Button>
        )}
      </div>

      <Card className="card-pad" style={{ maxWidth: 640 }}>
        <form onSubmit={submit} className="col gap-4">
          <SchemaForm fields={fields} values={values} setField={handleSetField} />

          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '12px 16px',
              borderRadius: 12,
              background: 'var(--surface-2)',
              border: '1px solid var(--accent-border, rgba(170, 59, 255, 0.35))',
            }}
          >
            <span className="sum-k">Net pay</span>
            <span className="sum-v" style={{ fontSize: '1.05rem' }}>{currency(netPay)}</span>
          </div>

          <div className="row" style={{ justifyContent: 'flex-end' }}>
            <Button type="submit" icon={editingId ? Pencil : Wallet} loading={saving}>
              {editingId ? 'Save changes' : 'Generate paycheck'}
            </Button>
          </div>
        </form>
      </Card>

      <SessionList
        items={created}
        title="Paychecks generated this session"
        columns={[
          { key: 'employee', header: 'Employee', render: (r) => empMap[String(r.employee_id)] || `#${r.employee_id}` },
          { key: 'pay_period_start', header: 'Period start', render: (r) => fmtDate(r.pay_period_start) },
          { key: 'pay_period_end', header: 'Period end', render: (r) => fmtDate(r.pay_period_end) },
          { key: 'base_salary', header: 'Base', align: 'right', render: (r) => <span className="cell-num">{currency(r.base_salary)}</span> },
          { key: 'net_pay', header: 'Net pay', align: 'right', render: (r) => <span className="cell-num">{currency(r.net_pay)}</span> },
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
                  aria-label="Edit paycheck"
                >
                  <Pencil size={15} />
                </button>
                <button
                  type="button"
                  className="icon-btn line-remove"
                  onClick={() => setPendingRemove(r)}
                  aria-label="Delete paycheck"
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
        title="Delete paycheck"
        message="This will permanently delete this paycheck."
        hint={pendingRemove ? `${empMap[String(pendingRemove.employee_id)] || `#${pendingRemove.employee_id}`} · net pay ${currency(pendingRemove.net_pay)}` : undefined}
      />
    </div>
  )
}
