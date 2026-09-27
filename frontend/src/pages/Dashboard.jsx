import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
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
  Legend,
} from 'recharts'
import { FolderKanban, Cloud, HandCoins, Users, Download, CalendarDays, Boxes, BookOpen, TrendingDown, ArrowRight } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { devApi } from '../api/devTracking'
import { hrApi } from '../api/hr'
import { financeApi } from '../api/finance'
import { scmApi } from '../api/scm'
import { projectStats, downloadSeries } from '../lib/devStats'
import { num, currency, compactCurrency, number, compactNumber, date as fmtDate, monthKey, monthLabel, titleize, userName, daysBetween, CHART_COLORS } from '../lib/format'
import { staggerContainer } from '../lib/motion'
import { modulesFor, MODULE_LABELS } from '../lib/roles'
import StatCard from '../components/ui/StatCard'
import Card from '../components/ui/Card'
import Badge from '../components/ui/Badge'
import Table from '../components/ui/Table'
import Spinner from '../components/ui/Spinner'

/** Try a fetch; resolve to `fallback` on any error (e.g. 403 for this user). */
async function safe(promise, fallback = null) {
  try {
    return await promise
  } catch {
    return fallback
  }
}

export default function Dashboard() {
  const { user, can } = useAuth()
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState({})

  useEffect(() => {
    let alive = true
    const want = (mod, fn) => (can(mod) ? safe(fn(), null) : Promise.resolve(null))
    ;(async () => {
      const [projects, investments, downloads, users, paychecks, leaves, expenses, products] = await Promise.all([
        want('dev', devApi.listProjects),
        want('dev', devApi.listInvestments),
        want('dev', devApi.listDownloads),
        want('hr', hrApi.listUsers),
        want('hr', hrApi.listPaychecks),
        want('hr', hrApi.listLeaves),
        want('finance', financeApi.listExpenses),
        want('scm', scmApi.listProducts),
      ])
      if (!alive) return
      setData({ projects, investments, downloads, users, paychecks, leaves, expenses, products })
      setLoading(false)
    })()
    return () => {
      alive = false
    }
  }, [can])

  if (loading) {
    return (
      <div className="table-loading">
        <Spinner /> <span className="muted">Gathering your metrics…</span>
      </div>
    )
  }

  const { projects, investments, downloads, users, paychecks, leaves, expenses, products } = data
  const modules = modulesFor(user)

  // --- derive KPIs ---
  const devSpend = (investments || []).reduce((s, i) => s + num(i.amount), 0)
  const payrollPaid = (paychecks || []).filter((p) => p.status === 'paid').reduce((s, p) => s + num(p.net_pay), 0)
  const payrollDraft = (paychecks || []).filter((p) => p.status !== 'paid').reduce((s, p) => s + num(p.net_pay), 0)
  const activeUsers = (users || []).filter((u) => u.is_active).length
  const pendingLeaves = (leaves || []).filter((l) => l.status === 'pending')
  const userMap = Object.fromEntries((users || []).map((u) => [String(u.id), u]))

  const stats = [
    projects && { label: 'Projects', value: projects.length, icon: FolderKanban, hint: 'programs in development' },
    investments && { label: 'Invested in dev', value: devSpend, format: compactCurrency, icon: Cloud, hint: `${investments.length} entries` },
    paychecks && { label: 'Payroll paid', value: payrollPaid, format: compactCurrency, icon: HandCoins, hint: payrollDraft ? `${compactCurrency(payrollDraft)} in draft` : `${paychecks.length} paychecks` },
    users && { label: 'Team', value: activeUsers, icon: Users, hint: users.length !== activeUsers ? `${users.length - activeUsers} inactive` : 'active members' },
    expenses && !users && { label: 'Ledger entries', value: expenses.length, icon: BookOpen, hint: 'typed expenses' },
    products && !investments && { label: 'Catalog items', value: products.length, icon: Boxes, hint: 'purchase items' },
  ]
    .filter(Boolean)
    .slice(0, 4)

  // downloads trend (all projects, by snapshot date)
  const dlSeries = downloadSeries(downloads || []).map((d) => ({ ...d, label: fmtDate(d.date) }))

  // monthly outflow (payroll + investments)
  const months = {}
  const bucket = (k) => (months[k] = months[k] || { payroll: 0, investments: 0 })
  for (const p of paychecks || []) bucket(monthKey(p.payment_date)).payroll += num(p.net_pay)
  for (const i of investments || []) bucket(monthKey(i.date)).investments += num(i.amount)
  const outflow = Object.keys(months)
    .filter(Boolean)
    .sort()
    .slice(-8)
    .map((k) => ({ month: monthLabel(k), ...months[k] }))

  // investment by category
  const byCat = {}
  for (const i of investments || []) byCat[i.category] = (byCat[i.category] || 0) + num(i.amount)
  const catData = Object.entries(byCat).map(([name, value]) => ({ name: titleize(name), value }))

  // project traction table
  const stats_ = projects ? projectStats(projects, investments || [], downloads || []) : {}
  const traction = (projects || [])
    .map((p) => ({ ...p, ...stats_[String(p.project_id)] }))
    .sort((a, b) => b.downloads - a.downloads || b.spend - a.spend)
    .slice(0, 6)

  const firstName = (user?.full_name || user?.email || '').split(/[\s@]/)[0] || 'there'

  return (
    <div className="module-page">
      <motion.div
        className="dash-hero"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: 'spring', stiffness: 160, damping: 22 }}
      >
        <h1>Hi {firstName} 👋</h1>
        <p>
          {modules.length
            ? `You have access to ${modules.map((m) => MODULE_LABELS[m]).join(', ')}. Here's the state of things today.`
            : 'Your account has no module access yet. Ask someone with People & Payroll access to grant you some.'}
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
        {projects && (
          <Card className="chart-card">
            <div className="row spread">
              <h3>
                <FolderKanban size={15} style={{ verticalAlign: -2, marginRight: 6 }} />
                Project status
              </h3>
              <Link to="/dev-tracking" className="muted row gap-1" style={{ fontSize: 13 }}>
                All projects <ArrowRight size={13} />
              </Link>
            </div>
            {traction.length ? (
              <Table
                columns={[
                  { key: 'project_name', header: 'Project', render: (r) => <span className="cell-strong">{r.project_name}</span> },
                  { key: 'spend', header: 'Invested', align: 'right', render: (r) => <span className="cell-num">{r.investmentCount ? compactCurrency(r.spend) : '—'}</span> },
                  { key: 'downloads', header: 'Downloads', align: 'right', render: (r) => <span className="cell-num">{r.snapshotCount ? compactNumber(r.downloads) : '—'}</span> },
                  { key: 'stars', header: 'Stars', align: 'right', render: (r) => <span className="cell-num">{r.stars ? compactNumber(r.stars) : '—'}</span> },
                ]}
                rows={traction}
                rowKey={(r) => r.project_id}
              />
            ) : (
              <div className="chart-empty">No projects yet — add one in Dev Tracking</div>
            )}
          </Card>
        )}

        {downloads && (
          <Card className="chart-card">
            <h3>
              <Download size={15} style={{ verticalAlign: -2, marginRight: 6 }} />
              Downloads over time
            </h3>
            {dlSeries.length > 1 ? (
              <ResponsiveContainer width="100%" height={240}>
                <AreaChart data={dlSeries} margin={{ left: -18, right: 6, top: 6 }}>
                  <defs>
                    <linearGradient id="dash-dl" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#aa3bff" stopOpacity={0.55} />
                      <stop offset="100%" stopColor="#aa3bff" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="label" tick={{ fontSize: 11, fill: 'var(--text-dim)' }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: 'var(--text-dim)' }} tickLine={false} axisLine={false} tickFormatter={compactNumber} />
                  <Tooltip formatter={(v) => number(v)} />
                  <Area type="monotone" dataKey="downloads" name="Downloads" stroke="#aa3bff" strokeWidth={2.5} fill="url(#dash-dl)" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="chart-empty">Record download snapshots to see a trend</div>
            )}
          </Card>
        )}

        {(paychecks || investments) && (
          <Card className="chart-card">
            <h3>
              <TrendingDown size={15} style={{ verticalAlign: -2, marginRight: 6 }} />
              Monthly outflow
            </h3>
            {outflow.length ? (
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={outflow} margin={{ left: -12, right: 6, top: 6 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="month" tick={{ fontSize: 11, fill: 'var(--text-dim)' }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: 'var(--text-dim)' }} tickLine={false} axisLine={false} tickFormatter={compactCurrency} />
                  <Tooltip formatter={(v) => currency(v)} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  {paychecks && <Bar dataKey="payroll" name="Payroll" stackId="a" fill="#aa3bff" maxBarSize={48} />}
                  {investments && <Bar dataKey="investments" name="Investments" stackId="a" fill="#22d3ee" radius={[8, 8, 0, 0]} maxBarSize={48} />}
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="chart-empty">No payments recorded yet</div>
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
                <ResponsiveContainer width="100%" height={210}>
                  <PieChart>
                    <Pie data={catData} dataKey="value" nameKey="name" innerRadius={52} outerRadius={80} paddingAngle={3}>
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

        {leaves && (
          <Card className="chart-card">
            <div className="row spread">
              <h3>
                <CalendarDays size={15} style={{ verticalAlign: -2, marginRight: 6 }} />
                Leave awaiting approval
              </h3>
              <Link to="/hr" className="muted row gap-1" style={{ fontSize: 13 }}>
                People &amp; Payroll <ArrowRight size={13} />
              </Link>
            </div>
            {pendingLeaves.length ? (
              <Table
                columns={[
                  { key: 'user_id', header: 'Member', render: (r) => <span className="cell-strong">{userName(userMap[String(r.user_id)]) || `#${r.user_id}`}</span> },
                  { key: 'leave_type', header: 'Type', render: (r) => <Badge status={r.leave_type} /> },
                  { key: 'dates', header: 'Dates', render: (r) => <span style={{ whiteSpace: 'nowrap' }}>{fmtDate(r.start_date)} – {fmtDate(r.end_date)}</span> },
                  { key: 'days', header: 'Days', align: 'right', render: (r) => <span className="cell-num">{daysBetween(r.start_date, r.end_date)}</span> },
                ]}
                rows={pendingLeaves.slice(0, 6)}
              />
            ) : (
              <div className="chart-empty">Nothing pending — all caught up</div>
            )}
          </Card>
        )}

        {expenses && (
          <Card className="chart-card">
            <div className="row spread">
              <h3>
                <BookOpen size={15} style={{ verticalAlign: -2, marginRight: 6 }} />
                Expense ledger
              </h3>
              <Link to="/finance" className="muted row gap-1" style={{ fontSize: 13 }}>
                Finance <ArrowRight size={13} />
              </Link>
            </div>
            <div className="summary-row" style={{ marginTop: 'var(--s-3)' }}>
              {['paycheck', 'petty_cash', 'investment', 'other'].map((t) => {
                const n = expenses.filter((e) => e.expense_type === t).length
                return (
                  <div key={t} className="summary-tile" style={{ opacity: n ? 1 : 0.6 }}>
                    <span className="sum-k">{titleize(t)}</span>
                    <span className="sum-v">{n}</span>
                  </div>
                )
              })}
            </div>
          </Card>
        )}
      </div>
    </div>
  )
}
