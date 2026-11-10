import { useState } from 'react'
import { ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'
import { ShoppingCart, ClipboardList, PieChart as PieIcon, Search, Tags, CalendarRange, AlertCircle } from 'lucide-react'
import PageHeader from '../../components/ui/PageHeader'
import Tabs from '../../components/ui/Tabs'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import Table from '../../components/ui/Table'
import Spinner from '../../components/ui/Spinner'
import EmptyState from '../../components/ui/EmptyState'
import AccessDenied from '../../components/ui/AccessDenied'
import ResourceSection from '../../components/ResourceSection'
import { Input, Select } from '../../components/ui/Field'
import { useList } from '../../lib/useList'
import { scmApi } from '../../api/scm'
import { num, currency, compactCurrency, number, dateTime, monthKey, monthLabel, CHART_COLORS } from '../../lib/format'

const TABS = [
  { key: 'records', label: 'Records', icon: ClipboardList },
  { key: 'breakdown', label: 'Breakdown', icon: PieIcon },
]

const UNCATEGORISED = 'Uncategorised'
const UNNAMED = 'Unnamed item'
// The donut keeps one colour per slice; categories beyond this many are folded into one slice
const MAX_SLICES = 7

/** Category label of a purchase; null, empty and blank all read as "Uncategorised". */
function categoryOf(row) {
  return String(row.category || '').trim() || UNCATEGORISED
}

/** Share of `part` in `whole` as a 0–1 fraction; 0 when there is nothing to share. */
function shareOf(part, whole) {
  return whole > 0 ? part / whole : 0
}

/** A 0–1 fraction as a whole percentage; a non-zero share never rounds down to "0%". */
function percent(fraction) {
  if (fraction > 0 && fraction < 0.005) return '<1%'
  return `${Math.round(fraction * 100)}%`
}

/** Spend per category, largest first: [{ name, spend, count, share }]. */
function byCategory(rows) {
  const groups = {}
  for (const r of rows) {
    const name = categoryOf(r)
    groups[name] = groups[name] || { name, spend: 0, count: 0 }
    groups[name].spend += num(r.total)
    groups[name].count += 1
  }
  const total = rows.reduce((s, r) => s + num(r.total), 0)
  return Object.values(groups)
    .map((g) => ({ ...g, share: shareOf(g.spend, total) }))
    .sort((a, b) => b.spend - a.spend || a.name.localeCompare(b.name))
}

/** Distinct category labels in the rows, alphabetical with "Uncategorised" last. */
function categoryNames(rows) {
  const names = [...new Set(rows.map(categoryOf))]
  return names.sort((a, b) => (a === UNCATEGORISED) - (b === UNCATEGORISED) || a.localeCompare(b))
}

/** Headline figures over a set of purchases. */
function summarize(rows) {
  const items = rows.reduce((s, r) => s + num(r.amount), 0)
  const spend = rows.reduce((s, r) => s + num(r.total), 0)
  const categories = byCategory(rows)
  return {
    count: rows.length,
    items,
    spend,
    avgUnitPrice: items > 0 ? spend / items : null,
    categoryCount: categories.length,
    topCategory: categories[0] || null,
  }
}

/** Spend per calendar month of `created_at`: the last 12 months that have data, oldest first. */
function byMonth(rows) {
  const months = {}
  for (const r of rows) {
    const key = monthKey(r.created_at)
    if (!key) continue
    months[key] = months[key] || { spend: 0, count: 0 }
    months[key].spend += num(r.total)
    months[key].count += 1
  }
  return Object.keys(months)
    .sort()
    .slice(-12)
    .map((key) => ({ key, month: monthLabel(key), ...months[key] }))
}

/** The `limit` items with the highest spend; rows are grouped by item name, ignoring case. */
function topItems(rows, limit = 10) {
  const groups = {}
  for (const r of rows) {
    const name = String(r.item_name || '').trim()
    const key = name.toLowerCase()
    groups[key] = groups[key] || { key, name, categories: new Set(), quantity: 0, spend: 0 }
    groups[key].categories.add(categoryOf(r))
    groups[key].quantity += num(r.amount)
    groups[key].spend += num(r.total)
  }
  const total = rows.reduce((s, r) => s + num(r.total), 0)
  return Object.values(groups)
    .map((g) => ({ ...g, categories: [...g.categories], share: shareOf(g.spend, total) }))
    .sort((a, b) => b.spend - a.spend || a.name.localeCompare(b.name))
    .slice(0, limit)
}

/** Donut slices: the largest categories, with everything past `MAX_SLICES` folded into one. */
function donutSlices(categories) {
  if (categories.length <= MAX_SLICES) return categories
  const tail = categories.slice(MAX_SLICES - 1)
  const other = {
    name: `${tail.length} smaller categories`,
    spend: tail.reduce((s, c) => s + c.spend, 0),
    count: tail.reduce((s, c) => s + c.count, 0),
    share: tail.reduce((s, c) => s + c.share, 0),
  }
  return [...categories.slice(0, MAX_SLICES - 1), other]
}

/** Purchases: goods the company buys — the records themselves plus where the spend goes. */
export default function PurchasePage() {
  const [tab, setTab] = useState('records')

  return (
    <div className="module-page">
      <PageHeader
        title="Purchases"
        subtitle="Goods the company buys, with quantities and spend."
        icon={ShoppingCart}
      />
      <Tabs tabs={TABS} active={tab} onChange={setTab} idBase="purchases" />

      <div className="tab-panel">
        {tab === 'records' && <RecordsSection />}
        {tab === 'breakdown' && <BreakdownSection />}
      </div>
    </div>
  )
}

/**
 * Every purchase, newest first, with search on the item name and a category filter.
 * The tiles always total all purchases; while a filter is on, their hints add what is shown.
 */
function RecordsSection() {
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('')

  // A category that no row carries any more (its last purchase was deleted or renamed) stops filtering
  const activeCategory = (rows) => (categoryNames(rows).includes(category) ? category : '')

  const summary = (shown, all) => {
    const s = summarize(all)
    const filtered = Boolean(query.trim() || activeCategory(all))
    const shownSpend = shown.reduce((sum, r) => sum + num(r.total), 0)
    const tiles = [
      { k: 'Purchases', v: number(s.count), hint: filtered ? `${number(shown.length)} shown by the filter` : `in ${s.categoryCount} ${s.categoryCount === 1 ? 'category' : 'categories'}` },
      { k: 'Items bought', v: number(s.items), hint: 'sum of quantities' },
      { k: 'Total spend', v: currency(s.spend), hint: filtered ? `${currency(shownSpend)} in the rows shown` : 'unit price × quantity', accent: true },
      { k: 'Average unit price', v: s.avgUnitPrice === null ? '—' : currency(s.avgUnitPrice), hint: 'spend ÷ items bought' },
      { k: 'Top category', v: s.topCategory ? s.topCategory.name : '—', hint: s.topCategory ? `${currency(s.topCategory.spend)} · ${percent(s.topCategory.share)} of spend` : 'no purchases yet' },
    ]
    return (
      <div className="summary-row">
        {tiles.map((t) => (
          <div key={t.k} className={`summary-tile ${t.accent ? 'accent' : ''}`}>
            <span className="sum-k">{t.k}</span>
            <span className="sum-v" title={String(t.v)}>{t.v}</span>
            <span className="sum-hint">{t.hint}</span>
          </div>
        ))}
      </div>
    )
  }

  const fields = [
    { key: 'item_name', label: 'Item name', required: true, placeholder: 'Laptop, printer paper…' },
    { key: 'category', label: 'Category', placeholder: 'Hardware, office supplies…', nullable: true },
    { key: 'unit_price', label: 'Unit price', type: 'number', step: '0.01', min: 0, required: true },
    { key: 'amount', label: 'Quantity', type: 'number', step: '0.01', min: 0, required: true, default: 1, hint: 'Total is calculated on save: unit price × quantity.' },
  ]

  return (
    <ResourceSection
      title="Purchase records"
      subtitle="Every purchase: what was bought, how many, and what it cost."
      moduleName="Purchases"
      fetcher={() => scmApi.listPurchases()}
      create={scmApi.createPurchase}
      createLabel="Record purchase"
      createTitle="New purchase"
      update={(row, payload) => scmApi.updatePurchase(row.id, payload)}
      updateTitle="Edit purchase"
      remove={(row) => scmApi.deletePurchase(row.id)}
      removeLabel="purchase"
      removeHint={(r) => `${r.item_name || UNNAMED} · ${number(r.amount)} × ${currency(r.unit_price)} · ${currency(r.total)}`}
      emptyHint={query.trim() || category ? 'No purchase matches the search or the category.' : 'Record the first purchase.'}
      emptyIcon={ShoppingCart}
      summary={summary}
      rowsTransform={(rows) => {
        const q = query.trim().toLowerCase()
        const wanted = activeCategory(rows)
        return [...rows]
          .filter((r) => !q || String(r.item_name || '').toLowerCase().includes(q))
          .filter((r) => !wanted || categoryOf(r) === wanted)
          .sort((a, b) => new Date(b.created_at) - new Date(a.created_at) || num(b.id) - num(a.id))
      }}
      toolbarExtra={({ rows }) => (
        <>
          <div className="search-box">
            <Search size={15} />
            <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search item name…" aria-label="Search purchases by item name" />
          </div>
          <Select value={activeCategory(rows)} onChange={(e) => setCategory(e.target.value)} aria-label="Filter by category">
            <option value="">All categories</option>
            {categoryNames(rows).map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </Select>
        </>
      )}
      columns={[
        { key: 'item_name', header: 'Item', render: (r) => (r.item_name ? <span className="cell-strong">{r.item_name}</span> : <span className="muted">{UNNAMED}</span>) },
        { key: 'category', header: 'Category', render: (r) => <Badge tone="neutral">{categoryOf(r)}</Badge> },
        { key: 'unit_price', header: 'Unit price', align: 'right', render: (r) => <span className="cell-num">{currency(r.unit_price)}</span> },
        { key: 'amount', header: 'Qty', align: 'right', render: (r) => <span className="cell-num">{number(r.amount)}</span> },
        { key: 'total', header: 'Total', align: 'right', render: (r) => <span className="cell-num cell-strong">{currency(r.total)}</span> },
        { key: 'created_at', header: 'Bought', render: (r) => <span className="muted">{dateTime(r.created_at)}</span> },
      ]}
      fields={fields}
    />
  )
}

/** Where the spend goes: by category, by month, and the items that cost the most. */
function BreakdownSection() {
  const { rows, loading, error, denied, reload } = useList(() => scmApi.listPurchases())

  if (denied) return <AccessDenied module="Purchases" />
  if (loading) {
    return (
      <div className="table-loading">
        <Spinner /> <span className="muted">Adding things up…</span>
      </div>
    )
  }
  if (error) {
    return (
      <div className="empty-state">
        <AlertCircle size={24} color="var(--danger)" />
        <div className="empty-title">Couldn’t load purchases</div>
        <div className="muted">{error}</div>
        <div className="empty-action">
          <Button variant="outline" onClick={reload}>
            Retry
          </Button>
        </div>
      </div>
    )
  }
  if (!rows.length) {
    return <EmptyState icon={ShoppingCart} title="No purchases yet" hint="Record the first purchase on the Records tab; the breakdown fills in from there." />
  }

  const totals = summarize(rows)
  const categories = byCategory(rows)
  const slices = donutSlices(categories)
  const months = byMonth(rows)
  const items = topItems(rows)

  return (
    <div className="col gap-5">
      <div className="grid cols-2">
        <Card className="chart-card">
          <h3>
            <Tags size={15} style={{ verticalAlign: -2, marginRight: 6 }} />
            Spend by category
          </h3>
          {totals.spend > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={210}>
                <PieChart>
                  <Pie data={slices} dataKey="spend" nameKey="name" innerRadius={58} outerRadius={84} paddingAngle={slices.length > 1 ? 3 : 0}>
                    {slices.map((d, i) => (
                      <Cell key={d.name} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v) => currency(v)} />
                  {/* The hole of the donut carries the figure the slices add up to */}
                  <text x="50%" y="50%" dy={-2} textAnchor="middle" style={{ fill: 'var(--text-h)', fontFamily: 'var(--display)', fontSize: 18, fontWeight: 700 }}>
                    {compactCurrency(totals.spend)}
                  </text>
                  <text x="50%" y="50%" dy={16} textAnchor="middle" style={{ fill: 'var(--text-dim)', fontSize: 11 }}>
                    total spend
                  </text>
                </PieChart>
              </ResponsiveContainer>
              <div className="legend-row">
                {slices.map((d, i) => (
                  <span key={d.name} className="legend-item">
                    <span className="legend-swatch" style={{ background: CHART_COLORS[i % CHART_COLORS.length] }} />
                    {d.name} · {currency(d.spend)} · {percent(d.share)}
                  </span>
                ))}
              </div>
            </>
          ) : (
            <div className="chart-empty">Every purchase so far totals {currency(0)}</div>
          )}
        </Card>

        <Card className="chart-card">
          <h3>
            <CalendarRange size={15} style={{ verticalAlign: -2, marginRight: 6 }} />
            Spend per month
          </h3>
          {months.length ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={months} margin={{ left: -12, right: 6, top: 6 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: 'var(--text-dim)' }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 11, fill: 'var(--text-dim)' }} tickLine={false} axisLine={false} tickFormatter={compactCurrency} />
                <Tooltip formatter={(v) => currency(v)} />
                <Bar dataKey="spend" name="Spend" fill={CHART_COLORS[0]} radius={[8, 8, 0, 0]} maxBarSize={48} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="chart-empty">No purchase has a date yet</div>
          )}
        </Card>
      </div>

      <Card className="card-pad col gap-3">
        <div>
          <h3>Top items by spend</h3>
          <p className="muted">
            The {items.length === 1 ? 'item' : `${items.length} items`} that cost the most, out of {currency(totals.spend)} spent on {number(totals.count)} {totals.count === 1 ? 'purchase' : 'purchases'}.
          </p>
        </div>
        <Table
          columns={[
            { key: 'name', header: 'Item', render: (r) => (r.name ? <span className="cell-strong">{r.name}</span> : <span className="muted">{UNNAMED}</span>) },
            {
              key: 'categories',
              header: 'Category',
              render: (r) => <Badge tone="neutral" title={r.categories.join(', ')}>{r.categories.length === 1 ? r.categories[0] : `${r.categories.length} categories`}</Badge>,
            },
            { key: 'quantity', header: 'Qty', align: 'right', render: (r) => <span className="cell-num">{number(r.quantity)}</span> },
            { key: 'spend', header: 'Spend', align: 'right', render: (r) => <span className="cell-num cell-strong">{currency(r.spend)}</span> },
            {
              key: 'share',
              header: 'Share of total',
              width: '22%',
              render: (r) => (
                <span className="row gap-2">
                  <span className="progress" style={{ flex: 1 }} aria-hidden="true">
                    <span style={{ width: `${Math.round(r.share * 100)}%` }} />
                  </span>
                  <span className="cell-num muted">{percent(r.share)}</span>
                </span>
              ),
            },
          ]}
          rows={items}
          rowKey={(r) => r.key}
          empty={{ title: 'No items yet', hint: 'Purchases will show up here.' }}
        />
      </Card>
    </div>
  )
}
