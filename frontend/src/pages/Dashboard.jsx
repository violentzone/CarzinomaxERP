import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts'
import { Wallet, Package, Users, Cloud, Download, Building2 } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { financeApi } from '../api/finance'
import { scmApi } from '../api/scm'
import { hrApi } from '../api/hr'
import { devApi } from '../api/devTracking'
import { num, currency, compactCurrency, date as fmtDate, CHART_COLORS, titleize } from '../lib/format'
import { staggerContainer } from '../lib/motion'
import StatCard from '../components/ui/StatCard'
import Card from '../components/ui/Card'
import Spinner from '../components/ui/Spinner'

/** Try a fetch; resolve to `fallback` on any error (e.g. 403 for this role). */
async function safe(promise, fallback = null) {
  try {
    return await promise
  } catch {
    return fallback
  }
}

export default function Dashboard() {
  const { user } = useAuth()
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState({})

  useEffect(() => {
    let alive = true
    ;(async () => {
      const [invoices, products, employees, investments, downloads, vendors] = await Promise.all([
        safe(financeApi.listInvoices(), null),
        safe(scmApi.listProducts(), null),
        safe(hrApi.listEmployees(), null),
        safe(devApi.listInvestments(), null),
        safe(devApi.listDownloads(), null),
        safe(scmApi.listVendors(), null),
      ])
      if (!alive) return
      setData({ invoices, products, employees, investments, downloads, vendors })
      setLoading(false)
    })()
    return () => {
      alive = false
    }
  }, [])

  if (loading) {
    return (
      <div className="table-loading">
        <Spinner /> <span className="muted">Gathering your metrics…</span>
      </div>
    )
  }

  const { invoices, products, employees, investments, downloads, vendors } = data

  // --- derive KPIs ---
  const ar = (invoices || []).filter((i) => i.invoice_type === 'customer').reduce((s, i) => s + num(i.total_amount), 0)
  const ap = (invoices || []).filter((i) => i.invoice_type === 'vendor').reduce((s, i) => s + num(i.total_amount), 0)
  const devSpend = (investments || []).reduce((s, i) => s + num(i.amount), 0)

  // downloads trend
  const dlSeries = [...(downloads || [])]
    .sort((a, b) => new Date(a.date) - new Date(b.date))
    .map((d) => ({ date: fmtDate(d.date), downloads: num(d.download_count), stars: num(d.star_count) }))

  // invoices AR/AP
  const arap = [
    { name: 'Receivable', amount: ar },
    { name: 'Payable', amount: ap },
  ]

  // investment by category
  const byCat = {}
  for (const i of investments || []) byCat[i.category] = (byCat[i.category] || 0) + num(i.amount)
  const catData = Object.entries(byCat).map(([name, value]) => ({ name: titleize(name), value }))

  const stats = [
    invoices && { label: 'Receivables', value: ar, format: compactCurrency, icon: Wallet, hint: `${invoices.length} invoices` },
    products && { label: 'Products', value: products.length, icon: Package, hint: 'catalog items' },
    employees && { label: 'Employees', value: employees.length, icon: Users, hint: 'headcount' },
    investments && { label: 'Dev Spend', value: devSpend, format: compactCurrency, icon: Cloud, hint: 'cloud investments' },
    vendors && !products ? { label: 'Vendors', value: vendors.length, icon: Building2 } : null,
  ].filter(Boolean)

  return (
    <div className="module-page">
      <motion.div
        className="dash-hero"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: 'spring', stiffness: 160, damping: 22 }}
      >
        <h1>
          Hi {(user?.full_name || user?.email || '').split(' ')[0] || 'there'} 👋
        </h1>
        <p>
          Here’s what’s happening across Carzinomax today. Your role has access to the modules in the
          sidebar — dive in to create records or review activity.
        </p>
      </motion.div>

      {stats.length > 0 && (
        <motion.div className="grid cols-4" variants={staggerContainer} initial="hidden" animate="show">
          {stats.map((s, i) => (
            <StatCard key={s.label} {...s} accent={i} />
          ))}
        </motion.div>
      )}

      <div className="grid cols-2">
        {downloads && (
          <Card className="chart-card">
            <div className="row spread">
              <h3>
                <Download size={15} style={{ verticalAlign: -2, marginRight: 6 }} />
                Project downloads
              </h3>
            </div>
            {dlSeries.length ? (
              <ResponsiveContainer width="100%" height={240}>
                <AreaChart data={dlSeries} margin={{ left: -18, right: 6, top: 6 }}>
                  <defs>
                    <linearGradient id="dl" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#aa3bff" stopOpacity={0.55} />
                      <stop offset="100%" stopColor="#aa3bff" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: 'var(--text-dim)' }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: 'var(--text-dim)' }} tickLine={false} axisLine={false} />
                  <Tooltip />
                  <Area type="monotone" dataKey="downloads" stroke="#aa3bff" strokeWidth={2.5} fill="url(#dl)" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="chart-empty">No download data yet</div>
            )}
          </Card>
        )}

        {invoices && (
          <Card className="chart-card">
            <h3>
              <Wallet size={15} style={{ verticalAlign: -2, marginRight: 6 }} />
              Receivable vs Payable
            </h3>
            {ar || ap ? (
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={arap} margin={{ left: -12, right: 6, top: 6 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="name" tick={{ fontSize: 12, fill: 'var(--text-dim)' }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: 'var(--text-dim)' }} tickLine={false} axisLine={false} />
                  <Tooltip formatter={(v) => currency(v)} />
                  <Bar dataKey="amount" radius={[8, 8, 0, 0]} maxBarSize={80}>
                    <Cell fill="#aa3bff" />
                    <Cell fill="#22d3ee" />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="chart-empty">No invoices yet</div>
            )}
          </Card>
        )}

        {investments && (
          <Card className="chart-card">
            <h3>
              <Cloud size={15} style={{ verticalAlign: -2, marginRight: 6 }} />
              Investment by category
            </h3>
            {catData.length ? (
              <>
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie data={catData} dataKey="value" nameKey="name" innerRadius={54} outerRadius={82} paddingAngle={3}>
                      {catData.map((d, i) => (
                        <Cell key={d.name} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(v) => currency(v)} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="legend-row">
                  {catData.map((d, i) => (
                    <span key={d.name} className="legend-item">
                      <span className="legend-swatch" style={{ background: CHART_COLORS[i % CHART_COLORS.length] }} />
                      {d.name} · {currency(d.value)}
                    </span>
                  ))}
                </div>
              </>
            ) : (
              <div className="chart-empty">No investments yet</div>
            )}
          </Card>
        )}

        {employees && (
          <Card className="chart-card">
            <h3>
              <Users size={15} style={{ verticalAlign: -2, marginRight: 6 }} />
              Team snapshot
            </h3>
            <div className="chart-empty" style={{ height: 'auto', padding: 'var(--s-4) 0' }}>
              <div style={{ textAlign: 'center' }}>
                <div className="gradient-text" style={{ fontFamily: 'var(--display)', fontSize: 46, fontWeight: 700 }}>
                  {employees.length}
                </div>
                <div className="muted">people on the team</div>
              </div>
            </div>
          </Card>
        )}
      </div>
    </div>
  )
}
