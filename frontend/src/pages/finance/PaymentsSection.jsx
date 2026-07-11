import { useState } from 'react'
import { HandCoins, Pencil, Trash2, X } from 'lucide-react'
import { financeApi } from '../../api/finance'
import { hrApi } from '../../api/hr'
import { useList } from '../../lib/useList'
import { useToast } from '../../context/ToastContext'
import { num, currency, date as fmtDate, today, titleize } from '../../lib/format'
import Card from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import Badge from '../../components/ui/Badge'
import Table from '../../components/ui/Table'
import AccessDenied from '../../components/ui/AccessDenied'
import ConfirmDialog from '../../components/ui/ConfirmDialog'
import { Select } from '../../components/ui/Field'
import { SchemaForm } from '../../components/SchemaForm'

const METHODS = ['bank_transfer', 'cash', 'card', 'cheque'].map((v) => ({ value: v, label: titleize(v) }))
const CATEGORIES = [
  'procurement', 'salary', 'rent', 'utilities', 'tax',
  'subscription', 'travel', 'loan_repayment', 'other',
].map((v) => ({ value: v, label: titleize(v) }))
const REFERENCE_PLACEHOLDERS = {
  utilities: 'Utility account / bill no.',
  tax: 'Tax reference no.',
  subscription: 'Subscription / plan ID',
  travel: 'Trip / expense report no.',
  loan_repayment: 'Loan account no.',
}

/**
 * Categorized company payments: create/edit form plus a persistent, filterable
 * history. Each category carries its own reference — procurement an optional
 * invoice, salary an employee, rent a contract number; the rest use the
 * free-text reference field.
 */
export default function PaymentsSection() {
  const toast = useToast()
  const { rows: invoices, denied } = useList(() => financeApi.listInvoices())
  // `denied` deliberately not read here: finance-only users get 403 from
  // /hr/employees; the employee picker degrades to a plain ID input instead
  // of blanking the whole Payments tab.
  const { rows: employees } = useList(() => hrApi.listEmployees())
  const [catFilter, setCatFilter] = useState('')
  const { rows: payments, loading, reload } = useList(
    () => financeApi.listPayments(catFilter ? { category: catFilter } : undefined),
    [catFilter],
  )
  const [values, setValues] = useState({ category: 'procurement', payment_date: today(), payment_method: 'bank_transfer' })
  const [saving, setSaving] = useState(false)
  const [editingId, setEditingId] = useState(null) // payment being edited, null = create
  const [pendingRemove, setPendingRemove] = useState(null)
  const [removing, setRemoving] = useState(false)

  if (denied) return <AccessDenied module="Finance" />

  const invoiceOptions = (invoices || []).map((i) => ({
    value: String(i.id),
    label: `${i.invoice_number} · ${i.partner_name} · ${currency(i.total_amount)} (${i.status})`,
  }))
  const empMap = Object.fromEntries(
    (employees || []).map((e) => [String(e.id), `${e.first_name} ${e.last_name}`]),
  )
  const employeeOptions = (employees || []).map((e) => ({ value: String(e.id), label: `${e.first_name} ${e.last_name}` }))

  const category = values.category || 'procurement'

  const fields = [
    { key: 'category', label: 'Category', type: 'select', required: true, options: CATEGORIES, default: 'procurement', full: true, disabled: !!editingId },
    ...(category === 'procurement'
      ? [{ key: 'invoice_id', label: 'Invoice (optional)', type: 'select', options: invoiceOptions, placeholder: invoiceOptions.length ? 'No invoice / select invoice…' : 'No invoices yet', full: true, disabled: !!editingId }]
      : []),
    ...(category === 'salary'
      ? employeeOptions.length
        ? [{ key: 'employee_id', label: 'Employee', type: 'select', required: true, options: employeeOptions, placeholder: 'Select employee…', full: true }]
        : [{ key: 'employee_id', label: 'Employee ID', type: 'number', min: 1, required: true, full: true, hint: 'Employee directory not available for your role — enter the employee ID.' }]
      : []),
    ...(category === 'rent'
      ? [{ key: 'contract_number', label: 'Contract number', required: true, placeholder: 'e.g. RENT-2026-001', full: true }]
      : []),
    { key: 'payment_date', label: 'Payment date', type: 'date', required: true, default: today() },
    { key: 'amount', label: 'Amount', type: 'number', step: '0.01', required: true },
    { key: 'payment_method', label: 'Method', type: 'select', options: METHODS, default: 'bank_transfer' },
    { key: 'reference', label: 'Reference', placeholder: REFERENCE_PLACEHOLDERS[category] || 'TXN / cheque no.' },
  ]

  // Switching category clears its reference fields so stale values never ride along
  const setField = (k, v) =>
    setValues((s) => (k === 'category'
      ? { ...s, category: v, invoice_id: '', employee_id: '', contract_number: '' }
      : { ...s, [k]: v }))

  const resetForm = () => {
    setEditingId(null)
    setValues({ category: 'procurement', payment_date: today(), payment_method: 'bank_transfer' })
  }

  const submit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      if (editingId) {
        // category and invoice are immutable on update — never sent
        const payload = {
          payment_date: values.payment_date,
          amount: num(values.amount),
          payment_method: values.payment_method || 'bank_transfer',
          reference: values.reference || null,
        }
        if (category === 'salary') payload.employee_id = num(values.employee_id)
        if (category === 'rent') payload.contract_number = values.contract_number
        await financeApi.updatePayment(editingId, payload)
        toast.success('Payment updated')
      } else {
        const payload = {
          category,
          payment_date: values.payment_date,
          amount: num(values.amount),
          payment_method: values.payment_method || 'bank_transfer',
          reference: values.reference || undefined,
        }
        if (category === 'procurement' && values.invoice_id) payload.invoice_id = num(values.invoice_id)
        if (category === 'salary') payload.employee_id = num(values.employee_id)
        if (category === 'rent') payload.contract_number = values.contract_number
        await financeApi.createPayment(payload)
        toast.success('Payment recorded')
      }
      resetForm()
      reload()
    } catch (err) {
      toast.error(err?.detail || (editingId ? 'Could not update payment' : 'Could not record payment'))
    } finally {
      setSaving(false)
    }
  }

  const startEdit = (row) => {
    setEditingId(row.id)
    setValues({
      category: row.category || 'procurement',
      invoice_id: row.invoice_id ? String(row.invoice_id) : '',
      employee_id: row.employee_id ? String(row.employee_id) : '',
      contract_number: row.contract_number || '',
      payment_date: row.payment_date,
      amount: row.amount,
      payment_method: row.payment_method || 'bank_transfer',
      reference: row.reference || '',
    })
  }

  const confirmRemove = async () => {
    setRemoving(true)
    try {
      await financeApi.deletePayment(pendingRemove.id)
      if (pendingRemove.id === editingId) resetForm()
      toast.success('Payment deleted')
      setPendingRemove(null)
      reload()
    } catch (err) {
      toast.error(err?.detail || 'Could not delete payment')
    } finally {
      setRemoving(false)
    }
  }

  const linkedTo = (r) => {
    if (r.category === 'salary') return r.employee_id ? empMap[String(r.employee_id)] || `#${r.employee_id}` : '—'
    if (r.category === 'rent') return r.contract_number || '—'
    return r.invoice_id ? <span className="mono">#{r.invoice_id}</span> : '—'
  }

  return (
    <div>
      <div className="section-toolbar">
        <div>
          <h2>{editingId ? `Edit payment #${editingId}` : 'Record a payment'}</h2>
          <div className="muted">Record company payments by category; invoice-linked payments update the invoice status automatically.</div>
        </div>
        {editingId && (
          <Button variant="outline" icon={X} onClick={resetForm}>
            Cancel edit
          </Button>
        )}
      </div>

      <Card className="card-pad" style={{ maxWidth: 640 }}>
        <form onSubmit={submit} className="col gap-4">
          <SchemaForm fields={fields} values={values} setField={setField} />
          <div className="row" style={{ justifyContent: 'flex-end' }}>
            <Button type="submit" icon={editingId ? Pencil : HandCoins} loading={saving}>
              {editingId ? 'Save changes' : 'Record payment'}
            </Button>
          </div>
        </form>
      </Card>

      <div className="section-toolbar" style={{ marginTop: 24 }}>
        <div>
          <h2>Payment history</h2>
          <div className="muted">All recorded payments, newest first.</div>
        </div>
        <div className="filter-row">
          <Select value={catFilter} onChange={(e) => setCatFilter(e.target.value)} style={{ width: 180 }}>
            <option value="">All categories</option>
            {CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </Select>
        </div>
      </div>

      <Table
        columns={[
          { key: 'payment_date', header: 'Date', render: (r) => fmtDate(r.payment_date) },
          { key: 'category', header: 'Category', render: (r) => <Badge tone="info">{titleize(r.category)}</Badge> },
          { key: 'linked', header: 'Linked to', render: linkedTo },
          { key: 'amount', header: 'Amount', align: 'right', render: (r) => <span className="cell-num">{currency(r.amount)}</span> },
          { key: 'payment_method', header: 'Method', render: (r) => titleize(r.payment_method) },
          { key: 'reference', header: 'Reference', render: (r) => r.reference || '—' },
          {
            key: 'actions',
            header: '',
            align: 'right',
            width: 80,
            render: (r) => (
              <span className="row-actions">
                <button
                  type="button"
                  className="icon-btn"
                  onClick={() => startEdit(r)}
                  aria-label="Edit payment"
                >
                  <Pencil size={15} />
                </button>
                <button
                  type="button"
                  className="icon-btn line-remove"
                  onClick={() => setPendingRemove(r)}
                  aria-label="Delete payment"
                >
                  <Trash2 size={15} />
                </button>
              </span>
            ),
          },
        ]}
        rows={payments}
        loading={loading}
        empty={{ title: 'No payments yet', hint: 'Record your first payment above.', icon: HandCoins }}
      />

      <ConfirmDialog
        open={!!pendingRemove}
        onClose={() => setPendingRemove(null)}
        onConfirm={confirmRemove}
        loading={removing}
        title="Delete payment"
        message="This will permanently delete this payment."
        hint={pendingRemove?.invoice_id ? 'The invoice’s paid status will be recalculated.' : undefined}
      />
    </div>
  )
}
