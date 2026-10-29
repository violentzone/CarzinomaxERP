import { useState } from 'react'
import { Boxes, Search, Package } from 'lucide-react'
import PageHeader from '../../components/ui/PageHeader'
import ResourceSection from '../../components/ResourceSection'
import { Input } from '../../components/ui/Field'
import { scmApi } from '../../api/scm'
import { num, currency, dateTime } from '../../lib/format'

/** Purchases: the catalog of applications the unit sells, with price and margin. */
export default function ScmPage() {
  const [query, setQuery] = useState('')

  const summary = (rows) => {
    const price = rows.reduce((s, r) => s + num(r.application_price), 0)
    const margins = rows.filter((r) => r.margin !== null && r.margin !== undefined)
    const margin = margins.length ? margins.reduce((s, r) => s + num(r.margin), 0) : null
    return (
      <div className="summary-row">
        <div className="summary-tile accent">
          <span className="sum-k">Catalog items</span>
          <span className="sum-v">{rows.length}</span>
        </div>
        <div className="summary-tile">
          <span className="sum-k">Total price value</span>
          <span className="sum-v">{currency(price)}</span>
          <span className="sum-hint">one of each application</span>
        </div>
        <div className="summary-tile">
          <span className="sum-k">Total margin</span>
          <span className="sum-v">{margin === null ? '—' : currency(margin)}</span>
          <span className="sum-hint">sum of stored margins</span>
        </div>
      </div>
    )
  }

  return (
    <div className="module-page">
      <PageHeader
        title="Purchases"
        subtitle="Applications with SKU, price and margin."
        icon={Boxes}
      />

      <div className="tab-panel">
        <ResourceSection
          title="Product catalog"
          subtitle="Every application the unit sells."
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
          emptyHint="Add the first application."
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
            { key: 'application_price', header: 'Price', align: 'right', render: (r) => <span className="cell-num">{currency(r.application_price)}</span> },
            {
              key: 'margin',
              header: 'Margin',
              align: 'right',
              render: (r) => {
                if (r.margin === null || r.margin === undefined) return <span className="muted">—</span>
                const m = num(r.margin)
                return (
                  <span className="cell-num" style={{ color: m < 0 ? 'var(--danger)' : m > 0 ? 'var(--success)' : 'inherit' }}>
                    {currency(m)}
                  </span>
                )
              },
            },
            { key: 'updated_at', header: 'Updated', render: (r) => <span className="muted">{dateTime(r.updated_at)}</span> },
          ]}
          fields={[
            { key: 'sku', label: 'SKU', required: true, placeholder: 'APP-001' },
            { key: 'name', label: 'Name', required: true, placeholder: 'Invoice scanner' },
            { key: 'application_price', label: 'Price', type: 'number', step: '0.01', min: 0, default: 0, hint: 'What the application is sold at.' },
            { key: 'margin', label: 'Margin', type: 'number', step: '0.01', default: 0, hint: 'Margin as an amount; may be negative.' },
            { key: 'description', label: 'Description', type: 'textarea', full: true, nullable: true },
          ]}
        />
      </div>
    </div>
  )
}
