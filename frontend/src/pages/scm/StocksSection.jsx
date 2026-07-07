import { useState } from 'react'
import { Boxes } from 'lucide-react'
import { scmApi } from '../../api/scm'
import { useList } from '../../lib/useList'
import { number } from '../../lib/format'
import Table from '../../components/ui/Table'
import AccessDenied from '../../components/ui/AccessDenied'
import { Select } from '../../components/ui/Field'

/**
 * Read-only stock levels. Two selects filter by warehouse and/or product; the
 * filters drive the list fetch. Warehouse/product ids are resolved to names via
 * lookup maps built from the loaded reference data.
 */
export default function StocksSection() {
  const { rows: warehouses } = useList(() => scmApi.listWarehouses())
  const { rows: products } = useList(() => scmApi.listProducts())
  const [wh, setWh] = useState('')
  const [prod, setProd] = useState('')
  const { rows, loading, denied } = useList(
    () => scmApi.listStocks({ warehouse_id: wh, product_id: prod }),
    [wh, prod],
  )

  if (denied) return <AccessDenied module="Supply Chain" />

  const whName = new Map((warehouses || []).map((w) => [String(w.id), w.name]))
  const prodName = new Map((products || []).map((p) => [String(p.id), p.name]))

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
        ]}
        rows={rows}
        loading={loading}
        empty={{ title: 'No stock records', hint: 'Stock appears once purchase orders are received into a warehouse.', icon: Boxes }}
      />
    </div>
  )
}
