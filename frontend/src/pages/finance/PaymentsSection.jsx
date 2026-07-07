import { useState } from 'react'
import { HandCoins } from 'lucide-react'
import { financeApi } from '../../api/finance'
import { useList } from '../../lib/useList'
import { useToast } from '../../context/ToastContext'
import { num, currency, date as fmtDate, today, titleize } from '../../lib/format'
import Card from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import AccessDenied from '../../components/ui/AccessDenied'
import SessionList from '../../components/ui/SessionList'
import { SchemaForm } from '../../components/SchemaForm'

const METHODS = ['bank_transfer', 'cash', 'card', 'cheque'].map((v) => ({ value: v, label: titleize(v) }))

/** Payments are POST-only — created rows are shown in a session list. */
export default function PaymentsSection() {
  const toast = useToast()
  const { rows: invoices, denied } = useList(() => financeApi.listInvoices())
  const [values, setValues] = useState({ payment_date: today(), payment_method: 'bank_transfer' })
  const [created, setCreated] = useState([])
  const [saving, setSaving] = useState(false)

  if (denied) return <AccessDenied module="Finance" />

  const invoiceOptions = (invoices || []).map((i) => ({
    value: String(i.id),
    label: `${i.invoice_number} · ${i.partner_name} · ${currency(i.total_amount)} (${i.status})`,
  }))

  const fields = [
    { key: 'invoice_id', label: 'Invoice', type: 'select', required: true, options: invoiceOptions, placeholder: invoiceOptions.length ? 'Select invoice…' : 'No invoices — create one first', full: true },
    { key: 'payment_date', label: 'Payment date', type: 'date', required: true, default: today() },
    { key: 'amount', label: 'Amount', type: 'number', step: '0.01', required: true },
    { key: 'payment_method', label: 'Method', type: 'select', options: METHODS, default: 'bank_transfer' },
    { key: 'reference', label: 'Reference', placeholder: 'TXN / cheque no.' },
  ]

  const submit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const payment = await financeApi.createPayment({
        invoice_id: num(values.invoice_id),
        payment_date: values.payment_date,
        amount: num(values.amount),
        payment_method: values.payment_method || 'bank_transfer',
        reference: values.reference || undefined,
      })
      setCreated((c) => [{ ...payment }, ...c])
      toast.success('Payment recorded')
      setValues({ payment_date: today(), payment_method: 'bank_transfer' })
    } catch (err) {
      toast.error(err?.detail || 'Could not record payment')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <div className="section-toolbar">
        <div>
          <h2>Record a payment</h2>
          <div className="muted">Applies against an invoice and updates its status automatically.</div>
        </div>
      </div>

      <Card className="card-pad" style={{ maxWidth: 640 }}>
        <form onSubmit={submit} className="col gap-4">
          <SchemaForm fields={fields} values={values} setField={(k, v) => setValues((s) => ({ ...s, [k]: v }))} />
          <div className="row" style={{ justifyContent: 'flex-end' }}>
            <Button type="submit" icon={HandCoins} loading={saving}>
              Record payment
            </Button>
          </div>
        </form>
      </Card>

      <SessionList
        items={created}
        title="Payments recorded this session"
        columns={[
          { key: 'id', header: '#', render: (r) => <span className="mono">{r.id}</span> },
          { key: 'invoice_id', header: 'Invoice', render: (r) => <span className="mono">#{r.invoice_id}</span> },
          { key: 'payment_date', header: 'Date', render: (r) => fmtDate(r.payment_date) },
          { key: 'amount', header: 'Amount', align: 'right', render: (r) => <span className="cell-num">{currency(r.amount)}</span> },
          { key: 'payment_method', header: 'Method', render: (r) => titleize(r.payment_method) },
          { key: 'reference', header: 'Reference', render: (r) => r.reference || '—' },
        ]}
      />
    </div>
  )
}
