import { useState } from 'react'
import { ShoppingCart, PackageCheck, Pencil, Trash2, X } from 'lucide-react'
import { scmApi } from '../../api/scm'
import { useList } from '../../lib/useList'
import { useToast } from '../../context/ToastContext'
import { num, currency, today, titleize } from '../../lib/format'
import Card from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import Badge from '../../components/ui/Badge'
import AccessDenied from '../../components/ui/AccessDenied'
import ConfirmDialog from '../../components/ui/ConfirmDialog'
import SessionList from '../../components/ui/SessionList'
import { Select } from '../../components/ui/Field'
import { SchemaForm } from '../../components/SchemaForm'
import LineItemsEditor from '../../components/ui/LineItemsEditor'

let seq = 0
const blankLine = () => ({ _key: ++seq, product_id: '', quantity: 1, unit_price: 0 })
const lineTotal = (l) => num(l.quantity) * num(l.unit_price)

const STATUSES = ['draft', 'ordered', 'received'].map((v) => ({ value: v, label: titleize(v) }))

/**
 * Per-row receive control: pick a warehouse and post the receipt. On success the
 * parent flips the row's status to 'received' so the control locks.
 */
function ReceiveControl({ po, warehouses, onReceived }) {
  const toast = useToast()
  const [wh, setWh] = useState('')
  const [busy, setBusy] = useState(false)
  const received = po.status === 'received'

  const receive = async () => {
    if (!wh) {
      toast.error('Select a warehouse to receive into')
      return
    }
    setBusy(true)
    try {
      const updated = await scmApi.receivePurchaseOrder(po.id, num(wh))
      onReceived(po.id, updated?.status || 'received')
      toast.success(`PO ${po.po_number} received`)
    } catch (err) {
      toast.error(err?.detail || 'Could not receive purchase order')
    } finally {
      setBusy(false)
    }
  }

  if (received) return <span className="muted">Received</span>

  return (
    <div className="row gap-2" style={{ justifyContent: 'flex-end' }}>
      <Select value={wh} onChange={(e) => setWh(e.target.value)} style={{ width: 150 }}>
        <option value="">Warehouse…</option>
        {(warehouses || []).map((w) => (
          <option key={w.id} value={String(w.id)}>{w.name}</option>
        ))}
      </Select>
      <Button size="sm" icon={PackageCheck} loading={busy} disabled={received || !wh} onClick={receive}>
        Receive
      </Button>
    </div>
  )
}

/** Purchase orders are POST-only; received into a warehouse from the session list. */
export default function PurchaseOrdersSection() {
  const toast = useToast()
  const { rows: vendors, denied } = useList(() => scmApi.listVendors())
  const { rows: products } = useList(() => scmApi.listProducts())
  const { rows: warehouses } = useList(() => scmApi.listWarehouses())
  const [header, setHeader] = useState({ order_date: today(), status: 'draft' })
  const [lines, setLines] = useState([blankLine()])
  const [created, setCreated] = useState([])
  const [saving, setSaving] = useState(false)
  const [editingId, setEditingId] = useState(null) // purchase order being edited, null = create
  const [pendingRemove, setPendingRemove] = useState(null)
  const [removing, setRemoving] = useState(false)

  if (denied) return <AccessDenied module="Supply Chain" />

  const vendorOptions = (vendors || []).map((v) => ({ value: String(v.id), label: `${v.code} · ${v.name}` }))
  const vendorName = new Map((vendors || []).map((v) => [String(v.id), v.name]))
  const productOptions = (products || []).map((p) => ({ value: String(p.id), label: `${p.sku} · ${p.name}` }))
  const total = lines.reduce((s, l) => s + lineTotal(l), 0)
  const allProducts = lines.every((l) => l.product_id)

  const resetForm = () => {
    setEditingId(null)
    setHeader({ order_date: today(), status: 'draft', vendor_id: '', po_number: '', delivery_date: '' })
    setLines([blankLine()])
  }

  const submit = async (e) => {
    e.preventDefault()
    if (!allProducts) {
      toast.error('Select a product on every line.')
      return
    }
    setSaving(true)
    try {
      const payload = {
        vendor_id: num(header.vendor_id),
        po_number: header.po_number,
        order_date: header.order_date,
        delivery_date: header.delivery_date || (editingId ? null : undefined),
        status: header.status || 'draft',
        lines: lines.map((l) => ({
          product_id: num(l.product_id),
          quantity: num(l.quantity),
          unit_price: num(l.unit_price),
        })),
      }
      if (editingId) {
        const po = await scmApi.updatePurchaseOrder(editingId, payload)
        setCreated((c) => c.map((p) => (p.id === editingId ? { ...po, _vendor: vendorName.get(String(header.vendor_id)) } : p)))
        toast.success(`Purchase order ${header.po_number} updated`)
      } else {
        const po = await scmApi.createPurchaseOrder(payload)
        setCreated((c) => [{ ...po, _vendor: vendorName.get(String(header.vendor_id)) }, ...c])
        toast.success(`Purchase order ${header.po_number} created`)
      }
      resetForm()
    } catch (err) {
      toast.error(err?.detail || (editingId ? 'Could not update purchase order' : 'Could not create purchase order'))
    } finally {
      setSaving(false)
    }
  }

  const startEdit = (row) => {
    setEditingId(row.id)
    setHeader({
      vendor_id: String(row.vendor_id),
      po_number: row.po_number,
      order_date: row.order_date,
      delivery_date: row.delivery_date || '',
      status: row.status || 'draft',
    })
    setLines((row.lines || []).map((l) => ({ _key: ++seq, product_id: String(l.product_id), quantity: l.quantity, unit_price: l.unit_price })))
  }

  const confirmRemove = async () => {
    setRemoving(true)
    try {
      await scmApi.deletePurchaseOrder(pendingRemove.id)
      setCreated((c) => c.filter((p) => p.id !== pendingRemove.id))
      if (pendingRemove.id === editingId) resetForm()
      toast.success('Purchase order deleted')
      setPendingRemove(null)
    } catch (err) {
      toast.error(err?.detail || 'Could not delete purchase order')
    } finally {
      setRemoving(false)
    }
  }

  const onReceived = (id, status) =>
    setCreated((c) => c.map((p) => (p.id === id ? { ...p, status } : p)))

  return (
    <div>
      <div className="section-toolbar">
        <div>
          <h2>{editingId ? `Edit purchase order #${editingId}` : 'New purchase order'}</h2>
          <div className="muted">Order goods from a vendor, then receive them into a warehouse.</div>
        </div>
        {editingId && (
          <Button variant="outline" icon={X} onClick={resetForm}>
            Cancel edit
          </Button>
        )}
      </div>

      <Card className="card-pad">
        <form onSubmit={submit} className="col gap-4">
          <SchemaForm
            fields={[
              { key: 'vendor_id', label: 'Vendor', type: 'select', required: true, options: vendorOptions, placeholder: vendorOptions.length ? 'Select vendor…' : 'Create a vendor first' },
              { key: 'po_number', label: 'PO number', required: true, placeholder: 'PO-1001' },
              { key: 'order_date', label: 'Order date', type: 'date', required: true, default: today() },
              { key: 'delivery_date', label: 'Delivery date', type: 'date' },
              { key: 'status', label: 'Status', type: 'select', default: 'draft', options: editingId ? STATUSES.filter((s) => s.value !== 'received') : STATUSES },
            ]}
            values={header}
            setField={(k, v) => setHeader((s) => ({ ...s, [k]: v }))}
          />

          <LineItemsEditor
            fields={[
              { key: 'product_id', label: 'Product', type: 'select', flex: 2.2, options: productOptions, placeholder: productOptions.length ? 'Select product…' : 'Create products first' },
              { key: 'quantity', label: 'Qty', type: 'number', step: '0.01', min: 0 },
              { key: 'unit_price', label: 'Unit price', type: 'number', step: '0.01', min: 0 },
            ]}
            value={lines}
            onChange={setLines}
            newRow={blankLine}
            rowExtra={(l) => currency(lineTotal(l))}
            addLabel="Add line"
            summary={() => (
              <span><span className="sum-k">Total</span> <span className="sum-v">{currency(total)}</span></span>
            )}
          />

          <div className="row" style={{ justifyContent: 'flex-end' }}>
            <Button type="submit" icon={editingId ? Pencil : ShoppingCart} loading={saving} disabled={!allProducts}>
              {editingId ? 'Save changes' : 'Create purchase order'}
            </Button>
          </div>
        </form>
      </Card>

      <SessionList
        items={created}
        title="Purchase orders this session"
        columns={[
          { key: 'po_number', header: 'PO #', render: (r) => <span className="mono cell-strong">{r.po_number}</span> },
          { key: 'vendor', header: 'Vendor', render: (r) => r._vendor || vendorName.get(String(r.vendor_id)) || `#${r.vendor_id}` },
          { key: 'total_amount', header: 'Total', align: 'right', render: (r) => <span className="cell-num">{currency(r.total_amount)}</span> },
          { key: 'status', header: 'Status', render: (r) => <Badge status={r.status} /> },
          { key: 'receive', header: 'Receive', align: 'right', render: (r) => <ReceiveControl po={r} warehouses={warehouses} onReceived={onReceived} /> },
          {
            key: 'actions',
            header: '',
            align: 'right',
            render: (r) =>
              r.status === 'received' ? null : (
                <span className="row-actions">
                  <button
                    type="button"
                    className="icon-btn"
                    onClick={() => startEdit(r)}
                    aria-label="Edit purchase order"
                  >
                    <Pencil size={15} />
                  </button>
                  <button
                    type="button"
                    className="icon-btn line-remove"
                    onClick={() => setPendingRemove(r)}
                    aria-label="Delete purchase order"
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
        title="Delete purchase order"
        message="This will permanently delete this purchase order."
        hint="Received purchase orders cannot be deleted."
      />
    </div>
  )
}
