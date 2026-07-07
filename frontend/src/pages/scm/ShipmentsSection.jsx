import { useState } from 'react'
import { Truck } from 'lucide-react'
import { scmApi } from '../../api/scm'
import { useList } from '../../lib/useList'
import { useToast } from '../../context/ToastContext'
import { num, titleize } from '../../lib/format'
import Card from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import Badge from '../../components/ui/Badge'
import AccessDenied from '../../components/ui/AccessDenied'
import SessionList from '../../components/ui/SessionList'
import { SchemaForm } from '../../components/SchemaForm'
import LineItemsEditor from '../../components/ui/LineItemsEditor'

let seq = 0
const blankItem = () => ({ _key: ++seq, product_id: '', quantity: 1 })

const STATUSES = ['pending', 'in_transit', 'delivered'].map((v) => ({ value: v, label: titleize(v) }))

/** Shipments are POST-only — created shipments are shown in a session list. */
export default function ShipmentsSection() {
  const toast = useToast()
  const { rows: products, denied } = useList(() => scmApi.listProducts())
  const [header, setHeader] = useState({ status: 'pending' })
  const [items, setItems] = useState([blankItem()])
  const [created, setCreated] = useState([])
  const [saving, setSaving] = useState(false)

  if (denied) return <AccessDenied module="Supply Chain" />

  const productOptions = (products || []).map((p) => ({ value: String(p.id), label: `${p.sku} · ${p.name}` }))
  const allProducts = items.every((i) => i.product_id)

  const submit = async (e) => {
    e.preventDefault()
    if (!allProducts) {
      toast.error('Select a product on every item.')
      return
    }
    setSaving(true)
    try {
      const shipment = await scmApi.createShipment({
        shipment_number: header.shipment_number,
        order_reference: header.order_reference,
        carrier: header.carrier || undefined,
        tracking_number: header.tracking_number || undefined,
        status: header.status || 'pending',
        shipped_date: header.shipped_date || undefined,
        estimated_delivery_date: header.estimated_delivery_date || undefined,
        items: items.map((i) => ({ product_id: num(i.product_id), quantity: num(i.quantity) })),
      })
      setCreated((c) => [{ ...shipment }, ...c])
      toast.success(`Shipment ${header.shipment_number} created`)
      setHeader({ status: 'pending', shipment_number: '', order_reference: '', carrier: '', tracking_number: '', shipped_date: '', estimated_delivery_date: '' })
      setItems([blankItem()])
    } catch (err) {
      toast.error(err?.detail || 'Could not create shipment')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <div className="section-toolbar">
        <div>
          <h2>New shipment</h2>
          <div className="muted">Track outbound logistics from dispatch to delivery.</div>
        </div>
      </div>

      <Card className="card-pad">
        <form onSubmit={submit} className="col gap-4">
          <SchemaForm
            fields={[
              { key: 'shipment_number', label: 'Shipment #', required: true, placeholder: 'SHP-1001' },
              { key: 'order_reference', label: 'Order reference', required: true, placeholder: 'PO-1001 / SO-42' },
              { key: 'carrier', label: 'Carrier', placeholder: 'DHL' },
              { key: 'tracking_number', label: 'Tracking #', placeholder: '1Z…' },
              { key: 'status', label: 'Status', type: 'select', default: 'pending', options: STATUSES },
              { key: 'shipped_date', label: 'Shipped date', type: 'date' },
              { key: 'estimated_delivery_date', label: 'Est. delivery', type: 'date' },
            ]}
            values={header}
            setField={(k, v) => setHeader((s) => ({ ...s, [k]: v }))}
          />

          <LineItemsEditor
            fields={[
              { key: 'product_id', label: 'Product', type: 'select', flex: 2.2, options: productOptions, placeholder: productOptions.length ? 'Select product…' : 'Create products first' },
              { key: 'quantity', label: 'Qty', type: 'number', step: '0.01', min: 0 },
            ]}
            value={items}
            onChange={setItems}
            newRow={blankItem}
            addLabel="Add item"
          />

          <div className="row" style={{ justifyContent: 'flex-end' }}>
            <Button type="submit" icon={Truck} loading={saving} disabled={!allProducts}>
              Create shipment
            </Button>
          </div>
        </form>
      </Card>

      <SessionList
        items={created}
        title="Shipments this session"
        columns={[
          { key: 'shipment_number', header: 'Shipment #', render: (r) => <span className="mono cell-strong">{r.shipment_number}</span> },
          { key: 'order_reference', header: 'Reference' },
          { key: 'carrier', header: 'Carrier', render: (r) => r.carrier || '—' },
          { key: 'status', header: 'Status', render: (r) => <Badge status={r.status} /> },
          { key: 'items', header: 'Items', align: 'right', render: (r) => r.items?.length ?? '—' },
        ]}
      />
    </div>
  )
}
