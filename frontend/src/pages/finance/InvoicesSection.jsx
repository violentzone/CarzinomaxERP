import { useState } from 'react'
import { Plus, Pencil, Trash2 } from 'lucide-react'
import { financeApi } from '../../api/finance'
import { useList } from '../../lib/useList'
import { useToast } from '../../context/ToastContext'
import { num, currency, date as fmtDate, today, titleize } from '../../lib/format'
import Table from '../../components/ui/Table'
import Button from '../../components/ui/Button'
import Modal from '../../components/ui/Modal'
import Badge from '../../components/ui/Badge'
import AccessDenied from '../../components/ui/AccessDenied'
import ConfirmDialog from '../../components/ui/ConfirmDialog'
import { Select } from '../../components/ui/Field'
import { SchemaForm } from '../../components/SchemaForm'
import LineItemsEditor from '../../components/ui/LineItemsEditor'

let seq = 0
const blankLine = () => ({ _key: ++seq, description: '', quantity: 1, unit_price: 0, tax_rate: 0 })
const lineTotal = (l) => num(l.quantity) * num(l.unit_price) * (1 + num(l.tax_rate) / 100)

const HEADER_FIELDS = [
  { key: 'invoice_number', label: 'Invoice #', required: true, placeholder: 'INV-1001' },
  { key: 'partner_name', label: 'Partner', required: true, placeholder: 'Acme Corp' },
  {
    key: 'invoice_type',
    label: 'Type',
    type: 'select',
    required: true,
    default: 'customer',
    options: [
      { value: 'customer', label: 'Customer (AR)' },
      { value: 'vendor', label: 'Vendor (AP)' },
    ],
  },
  {
    key: 'status',
    label: 'Status',
    type: 'select',
    default: 'draft',
    options: ['draft', 'sent', 'paid'].map((v) => ({ value: v, label: titleize(v) })),
  },
  { key: 'issue_date', label: 'Issue date', type: 'date', required: true, default: today() },
  { key: 'due_date', label: 'Due date', type: 'date', required: true, default: today() },
]

export default function InvoicesSection() {
  const toast = useToast()
  const [filter, setFilter] = useState('')
  const { rows, loading, denied, reload } = useList(
    () => financeApi.listInvoices(filter ? { invoice_type: filter } : undefined),
    [filter],
  )

  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState(null) // invoice being edited, null = create
  const [header, setHeader] = useState({ invoice_type: 'customer', status: 'draft', issue_date: today(), due_date: today() })
  const [lines, setLines] = useState([blankLine()])
  const [saving, setSaving] = useState(false)
  const [pendingRemove, setPendingRemove] = useState(null)
  const [removing, setRemoving] = useState(false)

  if (denied) return <AccessDenied module="Finance" />

  const subtotal = lines.reduce((s, l) => s + num(l.quantity) * num(l.unit_price), 0)
  const tax = lines.reduce((s, l) => s + num(l.quantity) * num(l.unit_price) * (num(l.tax_rate) / 100), 0)
  const total = subtotal + tax

  const openModal = () => {
    setEditing(null)
    setHeader({ invoice_type: 'customer', status: 'draft', issue_date: today(), due_date: today() })
    setLines([blankLine()])
    setOpen(true)
  }

  const openEdit = (row) => {
    setEditing(row)
    setHeader({
      invoice_number: row.invoice_number,
      partner_name: row.partner_name,
      invoice_type: row.invoice_type,
      status: row.status || 'draft',
      issue_date: row.issue_date,
      due_date: row.due_date,
    })
    setLines(
      (row.lines || []).map((l) => ({
        _key: ++seq,
        description: l.description,
        quantity: l.quantity,
        unit_price: l.unit_price,
        tax_rate: l.tax_rate,
      })),
    )
    setOpen(true)
  }

  const submit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const payload = {
        invoice_number: header.invoice_number,
        partner_name: header.partner_name,
        invoice_type: header.invoice_type,
        status: header.status || 'draft',
        issue_date: header.issue_date,
        due_date: header.due_date,
        lines: lines.map((l) => ({
          description: l.description,
          quantity: num(l.quantity),
          unit_price: num(l.unit_price),
          tax_rate: num(l.tax_rate),
        })),
      }
      if (editing) {
        await financeApi.updateInvoice(editing.id, payload)
        toast.success(`Invoice ${header.invoice_number} updated`)
      } else {
        await financeApi.createInvoice(payload)
        toast.success(`Invoice ${header.invoice_number} created`)
      }
      setOpen(false)
      reload()
    } catch (err) {
      toast.error(err?.detail || (editing ? 'Could not update invoice' : 'Could not create invoice'))
    } finally {
      setSaving(false)
    }
  }

  const confirmRemove = async () => {
    setRemoving(true)
    try {
      await financeApi.deleteInvoice(pendingRemove.id)
      toast.success(`Invoice ${pendingRemove.invoice_number} deleted`)
      setPendingRemove(null)
      reload()
    } catch (err) {
      toast.error(err?.detail || 'Could not delete invoice')
    } finally {
      setRemoving(false)
    }
  }

  return (
    <div>
      <div className="section-toolbar">
        <div>
          <h2>Invoices</h2>
          <div className="muted">Customer receivables and vendor payables.</div>
        </div>
        <div className="filter-row">
          <Select value={filter} onChange={(e) => setFilter(e.target.value)} style={{ width: 160 }}>
            <option value="">All types</option>
            <option value="customer">Customer (AR)</option>
            <option value="vendor">Vendor (AP)</option>
          </Select>
          <Button icon={Plus} onClick={openModal}>
            New invoice
          </Button>
        </div>
      </div>

      <Table
        columns={[
          { key: 'invoice_number', header: 'Number', render: (r) => <span className="mono cell-strong">{r.invoice_number}</span> },
          { key: 'partner_name', header: 'Partner' },
          { key: 'invoice_type', header: 'Type', render: (r) => <Badge tone={r.invoice_type === 'customer' ? 'info' : 'warning'}>{r.invoice_type === 'customer' ? 'Receivable' : 'Payable'}</Badge> },
          { key: 'issue_date', header: 'Issued', render: (r) => fmtDate(r.issue_date) },
          { key: 'due_date', header: 'Due', render: (r) => fmtDate(r.due_date) },
          { key: 'total_amount', header: 'Total', align: 'right', render: (r) => <span className="cell-num">{currency(r.total_amount)}</span> },
          { key: 'status', header: 'Status', render: (r) => <Badge status={r.status} /> },
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
                  onClick={() => openEdit(r)}
                  aria-label="Edit invoice"
                >
                  <Pencil size={15} />
                </button>
                <button
                  type="button"
                  className="icon-btn line-remove"
                  onClick={() => setPendingRemove(r)}
                  aria-label="Delete invoice"
                >
                  <Trash2 size={15} />
                </button>
              </span>
            ),
          },
        ]}
        rows={rows}
        loading={loading}
        empty={{ title: 'No invoices yet', hint: 'Create your first invoice to get started.', action: <Button icon={Plus} variant="outline" onClick={openModal}>New invoice</Button> }}
      />

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title={editing ? 'Edit invoice' : 'New invoice'}
        subtitle="Tax and totals are computed from the lines below."
        size="lg"
        footer={
          <>
            <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" form="invoice-form" loading={saving}>{editing ? 'Save changes' : 'Create invoice'}</Button>
          </>
        }
      >
        <form id="invoice-form" onSubmit={submit} className="col gap-4">
          <SchemaForm fields={HEADER_FIELDS} values={header} setField={(k, v) => setHeader((s) => ({ ...s, [k]: v }))} />
          <LineItemsEditor
            fields={[
              { key: 'description', label: 'Description', type: 'text', flex: 2.4, placeholder: 'Item or service' },
              { key: 'quantity', label: 'Qty', type: 'number', step: '0.01', min: 0 },
              { key: 'unit_price', label: 'Unit price', type: 'number', step: '0.01', min: 0 },
              { key: 'tax_rate', label: 'Tax %', type: 'number', step: '0.01', min: 0 },
            ]}
            value={lines}
            onChange={setLines}
            newRow={blankLine}
            rowExtra={(l) => currency(lineTotal(l))}
            addLabel="Add line"
            summary={() => (
              <>
                <span><span className="sum-k">Subtotal</span> <span className="sum-v">{currency(subtotal)}</span></span>
                <span><span className="sum-k">Tax</span> <span className="sum-v">{currency(tax)}</span></span>
                <span><span className="sum-k">Total</span> <span className="sum-v">{currency(total)}</span></span>
              </>
            )}
          />
        </form>
      </Modal>

      <ConfirmDialog
        open={!!pendingRemove}
        onClose={() => setPendingRemove(null)}
        onConfirm={confirmRemove}
        loading={removing}
        title="Delete invoice"
        message="This will permanently delete this invoice."
        hint="Its lines will be deleted; recorded payments are kept and unlinked."
      />
    </div>
  )
}
