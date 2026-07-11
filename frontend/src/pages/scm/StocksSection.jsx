import { useState } from 'react'
import { Boxes, Pencil, Trash2 } from 'lucide-react'
import { scmApi } from '../../api/scm'
import { useList } from '../../lib/useList'
import { useToast } from '../../context/ToastContext'
import { num, number } from '../../lib/format'
import Table from '../../components/ui/Table'
import Button from '../../components/ui/Button'
import Modal from '../../components/ui/Modal'
import ConfirmDialog from '../../components/ui/ConfirmDialog'
import AccessDenied from '../../components/ui/AccessDenied'
import { Field, Input, Select } from '../../components/ui/Field'

/**
 * Stock levels. Two selects filter by warehouse and/or product; the filters
 * drive the list fetch. Warehouse/product ids are resolved to names via lookup
 * maps built from the loaded reference data. Quantities can be adjusted (logged
 * as a manual-adjustment movement) or the record deleted.
 */
export default function StocksSection() {
  const toast = useToast()
  const { rows: warehouses } = useList(() => scmApi.listWarehouses())
  const { rows: products } = useList(() => scmApi.listProducts())
  const [wh, setWh] = useState('')
  const [prod, setProd] = useState('')
  const { rows, loading, denied, reload } = useList(
    () => scmApi.listStocks({ warehouse_id: wh, product_id: prod }),
    [wh, prod],
  )
  const [adjusting, setAdjusting] = useState(null)
  const [quantity, setQuantity] = useState('')
  const [saving, setSaving] = useState(false)
  const [pendingRemove, setPendingRemove] = useState(null)
  const [removing, setRemoving] = useState(false)

  if (denied) return <AccessDenied module="Supply Chain" />

  const whName = new Map((warehouses || []).map((w) => [String(w.id), w.name]))
  const prodName = new Map((products || []).map((p) => [String(p.id), p.name]))

  const startAdjust = (row) => {
    setAdjusting(row)
    setQuantity(row.quantity)
  }

  const saveAdjust = async () => {
    setSaving(true)
    try {
      await scmApi.updateStock(adjusting.id, { quantity: num(quantity) })
      toast.success('Stock adjusted')
      setAdjusting(null)
      reload()
    } catch (err) {
      toast.error(err?.detail || 'Could not adjust stock')
    } finally {
      setSaving(false)
    }
  }

  const confirmRemove = async () => {
    setRemoving(true)
    try {
      await scmApi.deleteStock(pendingRemove.id)
      toast.success('Stock record deleted')
      setPendingRemove(null)
      reload()
    } catch (err) {
      toast.error(err?.detail || 'Could not delete stock record')
    } finally {
      setRemoving(false)
    }
  }

  return (
    <div>
      <div className="section-toolbar">
        <div>
          <h2>Stock levels</h2>
          <div className="muted">On-hand quantity per product and warehouse.</div>
        </div>
        <div className="filter-row">
          <Select value={wh} onChange={(e) => setWh(e.target.value)} style={{ width: 180 }}>
            <option value="">All warehouses</option>
            {(warehouses || []).map((w) => (
              <option key={w.id} value={String(w.id)}>{w.name}</option>
            ))}
          </Select>
          <Select value={prod} onChange={(e) => setProd(e.target.value)} style={{ width: 180 }}>
            <option value="">All products</option>
            {(products || []).map((p) => (
              <option key={p.id} value={String(p.id)}>{p.name}</option>
            ))}
          </Select>
        </div>
      </div>

      <Table
        columns={[
          { key: 'product', header: 'Product', render: (r) => <span className="cell-strong">{prodName.get(String(r.product_id)) || `#${r.product_id}`}</span> },
          { key: 'warehouse', header: 'Warehouse', render: (r) => whName.get(String(r.warehouse_id)) || `#${r.warehouse_id}` },
          { key: 'quantity', header: 'Quantity', align: 'right', render: (r) => <span className="cell-num">{number(r.quantity)}</span> },
          {
            key: 'actions',
            header: '',
            align: 'right',
            render: (r) => (
              <span className="row-actions">
                <button
                  type="button"
                  className="icon-btn"
                  onClick={() => startAdjust(r)}
                  aria-label="Adjust stock"
                >
                  <Pencil size={15} />
                </button>
                <button
                  type="button"
                  className="icon-btn line-remove"
                  onClick={() => setPendingRemove(r)}
                  aria-label="Delete stock record"
                >
                  <Trash2 size={15} />
                </button>
              </span>
            ),
          },
        ]}
        rows={rows}
        loading={loading}
        empty={{ title: 'No stock records', hint: 'Stock appears once purchase orders are received into a warehouse.', icon: Boxes }}
      />

      <Modal
        open={!!adjusting}
        onClose={() => setAdjusting(null)}
        title="Adjust stock"
        size="sm"
        footer={
          <>
            <Button variant="ghost" onClick={() => setAdjusting(null)}>
              Cancel
            </Button>
            <Button onClick={saveAdjust} loading={saving}>
              Save
            </Button>
          </>
        }
      >
        <div className="col gap-2">
          <Field label="Quantity">
            <Input
              type="number"
              step="0.01"
              min={0}
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
            />
          </Field>
          <p className="muted">The change is logged as a manual-adjustment stock movement.</p>
        </div>
      </Modal>

      <ConfirmDialog
        open={!!pendingRemove}
        onClose={() => setPendingRemove(null)}
        onConfirm={confirmRemove}
        loading={removing}
        title="Delete stock record"
        message="This will permanently delete this stock record."
        hint="Past stock movements are kept for audit."
      />
    </div>
  )
}
