import { useState } from 'react'
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'
import { AppWindow, Search, Package, BarChart3 } from 'lucide-react'
import PageHeader from '../../components/ui/PageHeader'
import ResourceSection from '../../components/ResourceSection'
import Card from '../../components/ui/Card'
import { Input } from '../../components/ui/Field'
import { scmApi } from '../../api/scm'
import { num, currency, number, compactNumber, dateTime, CHART_COLORS } from '../../lib/format'

/** Products: the software products the company sells, with price, margin and copies sold. */
export default function ProductPage() {
  const [query, setQuery] = useState('')

  // Totals and the chart cover the whole catalog, not just the rows the search leaves
  const summary = (shown, all) => {
    const copies = all.reduce((s, r) => s + num(r.copy_sold), 0)
    const sales = all.reduce((s, r) => s + num(r.application_price) * num(r.copy_sold), 0)
    const margins = all.filter((r) => r.margin !== null && r.margin !== undefined)
    const margin = margins.length ? margins.reduce((s, r) => s + num(r.margin) * num(r.copy_sold), 0) : null
    const tiles = [
      { k: 'Products', v: all.length, accent: true },
      { k: 'Copies sold', v: number(copies) },
      { k: 'Sales value', v: currency(sales), hint: 'price × copies sold' },
      { k: 'Total margin', v: margin === null ? '—' : currency(margin), hint: 'margin × copies sold' },
    ]
    const top = all
      .filter((r) => num(r.copy_sold) > 0)
      .sort((a, b) => num(b.copy_sold) - num(a.copy_sold) || String(a.sku).localeCompare(String(b.sku)))
      .slice(0, 8)
      .map((r) => ({ id: r.id, name: r.name || r.sku, copies: num(r.copy_sold) }))
    return (
      <>
        <div className="summary-row">
          {tiles.map((t) => (
            <div key={t.k} className={`summary-tile ${t.accent ? 'accent' : ''}`}>
              <span className="sum-k">{t.k}</span>
              <span className="sum-v">{t.v}</span>
              {t.hint && <span className="sum-hint">{t.hint}</span>}
            </div>
          ))}
        </div>
        {top.length > 0 && (
          <Card className="chart-card">
            <div className="row spread">
              <h3>
                <BarChart3 size={15} style={{ verticalAlign: -2, marginRight: 6 }} />
                Copies sold per product
              </h3>
              {all.length > top.length && (
                <span className="muted" style={{ fontSize: 13 }}>
                  Top {top.length} of {all.length} products
                </span>
              )}
            </div>
            <ResponsiveContainer width="100%" height={top.length * 34 + 40}>
              <BarChart data={top} layout="vertical" margin={{ left: 6, right: 16, top: 6 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
                <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11, fill: 'var(--text-dim)' }} tickLine={false} axisLine={false} tickFormatter={compactNumber} />
                <YAxis type="category" dataKey="name" width={140} tick={{ fontSize: 11, fill: 'var(--text-dim)' }} tickLine={false} axisLine={false} tickFormatter={(v) => (String(v).length > 20 ? `${String(v).slice(0, 19)}…` : v)} />
                <Tooltip formatter={(v) => number(v)} />
                <Bar dataKey="copies" name="Copies sold" fill={CHART_COLORS[0]} radius={[0, 8, 8, 0]} maxBarSize={22} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        )}
      </>
    )
  }

  return (
    <div className="module-page">
      <PageHeader
        title="Products"
        subtitle="The software products the company sells."
        icon={AppWindow}
      />

      <div className="tab-panel">
        <ResourceSection
          title="Product catalog"
          subtitle="Every product with its price, margin and copies sold."
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
          emptyHint="Add the first product."
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
            { key: 'copy_sold', header: 'Copies sold', align: 'right', render: (r) => <span className="cell-num">{number(r.copy_sold)}</span> },
            { key: 'updated_at', header: 'Updated', render: (r) => <span className="muted">{dateTime(r.updated_at)}</span> },
          ]}
          fields={[
            { key: 'sku', label: 'SKU', required: true, placeholder: 'APP-001' },
            { key: 'name', label: 'Name', required: true, placeholder: 'Invoice scanner' },
            { key: 'application_price', label: 'Price', type: 'number', step: '0.01', min: 0, default: 0, hint: 'What the application is sold at.' },
            { key: 'margin', label: 'Margin', type: 'number', step: '0.01', default: 0, hint: 'Margin as an amount; may be negative.' },
            { key: 'copy_sold', label: 'Copies sold', type: 'number', step: '1', min: 0, default: 0, hint: 'How many copies have been sold so far.' },
            { key: 'description', label: 'Description', type: 'textarea', full: true, nullable: true },
          ]}
        />
      </div>
    </div>
  )
}
