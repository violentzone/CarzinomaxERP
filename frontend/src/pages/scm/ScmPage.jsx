import { useState } from 'react'
import { Boxes, Search, Package } from 'lucide-react'
import PageHeader from '../../components/ui/PageHeader'
import ResourceSection from '../../components/ResourceSection'
import { Input } from '../../components/ui/Field'
import { scmApi } from '../../api/scm'
import { num, currency, dateTime } from '../../lib/format'

/** Purchases: the catalog of things the unit buys or sells, with cost vs list price. */
export default function ScmPage() {
  const [query, setQuery] = useState('')

  const margin = (r) => {
    const price = num(r.unit_price)
    const cost = num(r.cost)
    if (!price) return null
    return ((price - cost) / price) * 100
  }

  const summary = (rows) => {
    const cost = rows.reduce((s, r) => s + num(r.cost), 0)
    const list = rows.reduce((s, r) => s + num(r.unit_price), 0)
    const margins = rows.map(margin).filter((m) => m !== null)
    const avg = margins.length ? margins.reduce((s, m) => s + m, 0) / margins.length : null
    return (
      <div className="summary-row">
        <div className="summary-tile accent">
          <span className="sum-k">Catalog items</span>
          <span className="sum-v">{rows.length}</span>
        </div>
        <div className="summary-tile">
          <span className="sum-k">Total unit cost</span>
          <span className="sum-v">{currency(cost)}</span>
          <span className="sum-hint">one of each item</span>
        </div>
        <div className="summary-tile">
          <span className="sum-k">Total list value</span>
          <span className="sum-v">{currency(list)}</span>
        </div>
        <div className="summary-tile">
          <span className="sum-k">Avg. margin</span>
          <span className="sum-v">{avg === null ? '—' : `${avg.toFixed(1)}%`}</span>
          <span className="sum-hint">(price − cost) / price</span>
        </div>
      </div>
    )
  }

  return (
    <div className="module-page">
      <PageHeader
        title="Purchases"
        subtitle="Products and purchase items with SKU, cost and list price."
        icon={Boxes}
      />

      <div className="tab-panel">
        <ResourceSection
          title="Product catalog"
          subtitle="Everything the unit buys or sells."
          moduleName="Purchases"
          fetcher={() => scmApi.listProducts()}
          create={scmApi.createProduct}
          createLabel="New product"
          createTitle="New product"
          update={(row, payload) => scmApi.updateProduct(row.id, payload)}
          updateTitle="Edit product"
          remove={(row) => scmApi.deleteProduct(row.id)}
          removeLabel="product"
          removeHint={(r) => `${r.sku} · ${r.name}`}
          emptyHint="Add the first product or purchase item."
          emptyIcon={Package}
          summary={summary}
          rowsTransform={(rows) => {
            const q = query.trim().toLowerCase()
            return [...rows]
              .filter((r) => !q || [r.sku, r.name, r.description].some((v) => String(v || '').toLowerCase().includes(q)))
              .sort((a, b) => String(a.sku).localeCompare(String(b.sku)))
          }}
          toolbarExtra={
            <div className="search-box">
              <Search size={15} />
              <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search SKU or name…" aria-label="Search products" />
            </div>
          }
          columns={[
            { key: 'sku', header: 'SKU', render: (r) => <span className="mono cell-strong">{r.sku}</span> },
            {
              key: 'name',
              header: 'Product',
              render: (r) => (
                <div className="col">
                  <span className="cell-strong">{r.name}</span>
                  {r.description && <span className="cell-sub">{r.description}</span>}
                </div>
              ),
            },
            { key: 'cost', header: 'Cost', align: 'right', render: (r) => <span className="cell-num">{currency(r.cost)}</span> },
            { key: 'unit_price', header: 'List price', align: 'right', render: (r) => <span className="cell-num">{currency(r.unit_price)}</span> },
            {
              key: 'margin',
              header: 'Margin',
              align: 'right',
              render: (r) => {
                const m = margin(r)
                if (m === null) return <span className="muted">—</span>
                return (
                  <span className="cell-num" style={{ color: m < 0 ? 'var(--danger)' : m > 0 ? 'var(--success)' : 'inherit' }}>
                    {m.toFixed(1)}%
                  </span>
                )
              },
            },
            { key: 'updated_at', header: 'Updated', render: (r) => <span className="muted">{dateTime(r.updated_at)}</span> },
          ]}
          fields={[
            { key: 'sku', label: 'SKU', required: true, placeholder: 'LAP-001' },
            { key: 'name', label: 'Name', required: true, placeholder: 'Laptop, 16"' },
            { key: 'cost', label: 'Unit cost', type: 'number', step: '0.01', min: 0, default: 0, hint: 'What the unit pays.' },
            { key: 'unit_price', label: 'List price', type: 'number', step: '0.01', min: 0, default: 0, hint: 'What it is sold or valued at.' },
            { key: 'description', label: 'Description', type: 'textarea', full: true, nullable: true },
          ]}
        />
      </div>
    </div>
  )
}
