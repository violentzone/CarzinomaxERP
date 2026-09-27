import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  ResponsiveContainer,
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
import { HandCoins, Cloud, Boxes, BookOpen, Lock, TrendingDown } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { financeApi } from '../../api/finance'
import { hrApi } from '../../api/hr'
import { devApi } from '../../api/devTracking'
import { scmApi } from '../../api/scm'
import { num, currency, compactCurrency, date as fmtDate, monthKey, monthLabel, titleize, userName, CHART_COLORS, parseDate } from '../../lib/format'
import { staggerContainer } from '../../lib/motion'
import { MODULE_LABELS } from '../../lib/roles'
import StatCard from '../../components/ui/StatCard'
import Card from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'
import Table from '../../components/ui/Table'
import Spinner from '../../components/ui/Spinner'
import AccessDenied from '../../components/ui/AccessDenied'

async function safe(promise, fallback = null) {
  try {
    return await promise
  } catch {
    return fallback
  }
}

/**
 * Money out, across modules: payroll (HR), project investments (dev tracking)
 * and the purchase catalog (SCM), alongside the finance ledger itself. Each
 * source is only loaded when the signed-in user holds that module's flag.
 */
export default function FinanceOverview() {
  const { can } = useAuth()
  const [state, setState] = useState({ loading: true })

  useEffect(() => {
    let alive = true
    const want = (mod, fn) => (can(mod) ? safe(fn(), null) : Promise.resolve(null))
    ;(async () => {
      const [expenses, paychecks, users, investments, projects, products] = await Promise.all([
        can('finance') ? financeApi.listExpenses().catch((e) => ({ __error: e })) : Promise.resolve(null),
        want('hr', hrApi.listPaychecks),
        want('hr', hrApi.listUsers),
        want('dev', devApi.listInvestments),
        want('dev', devApi.listProjects),
        want('scm', scmApi.listProducts),
      ])
      if (!alive) return
      setState({ loading: false, expenses, paychecks, users, investments, projects, products })
    })()
    return () => {
      alive = false
    }
  }, [can])

  if (!can('finance')) return <AccessDenied module="Finance" />
  if (state.loading) {
    return (
      <div className="table-loading">
        <Spinner /> <span className="muted">Adding things up…</span>
      </div>
    )
  }
  if (state.expenses?.__error?.status === 403) return <AccessDenied module="Finance" />

  const { expenses, paychecks, users, investments, projects, products } = state
  const userMap = Object.fromEntries((users || []).map((u) => [String(u.id), u]))
  const projectMap = Object.fromEntries((projects || []).map((p) => [String(p.project_id), p]))

  const payrollPaid = (paychecks || []).filter((p) => p.status === 'paid').reduce((s, p) => s + num(p.net_pay), 0)
  const payrollDraft = (paychecks || []).filter((p) => p.status !== 'paid').reduce((s, p) => s + num(p.net_pay), 0)
  const devSpend = (investments || []).reduce((s, i) => s + num(i.amount), 0)
  const catalogCost = (products || []).reduce((s, p) => s + num(p.cost), 0)

  // Monthly outflow: payroll (by payment date) + investments (by date), last 12 months with data.
  const months = {}
  const bucket = (k) => (months[k] = months[k] || { payroll: 0, investments: 0 })
  for (const p of paychecks || []) bucket(monthKey(p.payment_date)).payroll += num(p.net_pay)
  for (const i of investments || []) bucket(monthKey(i.date)).investments += num(i.amount)
  const outflow = Object.keys(months)
    .filter(Boolean)
    .sort()
    .slice(-12)
    .map((k) => ({ month: monthLabel(k), ...months[k] }))

  // Ledger by type
  const byType = {}
  for (const e of expenses || []) byType[e.expense_type] = (byType[e.expense_type] || 0) + 1
  const typeData = Object.entries(byType).map(([name, value]) => ({ name: titleize(name), value }))

  // Recent transactions: unify paychecks + investments
  const tx = [
    ...(paychecks || []).map((p) => ({
      id: `p${p.id}`,
      date: p.payment_date,
      kind: 'paycheck',
      party: userName(userMap[String(p.user_id)]) || `#${p.user_id}`,
      note: p.status === 'paid' ? 'Paid' : 'Draft',
      amount: num(p.net_pay),
    })),
    ...(investments || []).map((i) => ({
      id: `i${i.id}`,
      date: i.date,
      kind: 'investment',
      party: i.vendor,
      note: projectMap[String(i.project_id)]?.project_name || `Project #${i.project_id}`,
      amount: num(i.amount),
    })),
  ]
    .sort((a, b) => (parseDate(b.date) ?? 0) - (parseDate(a.date) ?? 0))
    .slice(0, 12)

  const stats = [
    paychecks && { label: 'Payroll paid', value: payrollPaid, format: compactCurrency, icon: HandCoins, hint: payrollDraft ? `${currency(payrollDraft)} still in draft` : `${paychecks.length} paychecks` },
    investments && { label: 'Project investments', value: devSpend, format: compactCurrency, icon: Cloud, hint: `${investments.length} entries` },
    products && { label: 'Purchase catalog cost', value: catalogCost, format: compactCurrency, icon: Boxes, hint: `${products.length} items` },
    expenses && { label: 'Ledger entries', value: expenses.length, icon: BookOpen, hint: 'typed expense records' },
  ].filter(Boolean)

  const locked = [
    !paychecks && 'hr',
    !investments && 'dev',
    !products && 'scm',
  ].filter(Boolean)

  return (
    <div className="col gap-5">
      <motion.div className="grid cols-4" variants={staggerContainer} initial="hidden" animate="show">
        {stats.map((s, i) => (
          <StatCard key={s.label} {...s} accent={i} />
        ))}
      </motion.div>

      {locked.length > 0 && (
        <div className="note-box">
          <Lock size={14} />
          <span>
            Figures from {locked.map((m) => MODULE_LABELS[m]).join(', ')} are hidden — your account doesn’t have
            access to {locked.length === 1 ? 'that module' : 'those modules'}.
          </span>
        </div>
      )}

      <div className="grid cols-2">
        {(paychecks || investments) && (
          <Card className="chart-card">
            <h3>
              <TrendingDown size={15} style={{ verticalAlign: -2, marginRight: 6 }} />
              Monthly outflow
            </h3>
            {outflow.length ? (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={outflow} margin={{ left: -12, right: 6, top: 6 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="month" tick={{ fontSize: 11, fill: 'var(--text-dim)' }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: 'var(--text-dim)' }} tickLine={false} axisLine={false} tickFormatter={compactCurrency} />
                  <Tooltip formatter={(v) => currency(v)} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  {paychecks && <Bar dataKey="payroll" name="Payroll" stackId="a" fill="#aa3bff" radius={[0, 0, 0, 0]} maxBarSize={48} />}
                  {investments && <Bar dataKey="investments" name="Investments" stackId="a" fill="#22d3ee" radius={[8, 8, 0, 0]} maxBarSize={48} />}
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="chart-empty">Nothing paid out yet</div>
            )}
          </Card>
        )}

        <Card className="chart-card">
          <h3>
            <BookOpen size={15} style={{ verticalAlign: -2, marginRight: 6 }} />
            Ledger by type
          </h3>
          {typeData.length ? (
            <>
              <ResponsiveContainer width="100%" height={210}>
                <PieChart>
                  <Pie data={typeData} dataKey="value" nameKey="name" innerRadius={52} outerRadius={80} paddingAngle={3}>
                    {typeData.map((d, i) => (
                      <Cell key={d.name} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
              <div className="legend-row">
                {typeData.map((d, i) => (
                  <span key={d.name} className="legend-item">
                    <span className="legend-swatch" style={{ background: CHART_COLORS[i % CHART_COLORS.length] }} />
                    {d.name} · {d.value}
                  </span>
                ))}
              </div>
            </>
          ) : (
            <div className="chart-empty">No ledger entries yet</div>
          )}
        </Card>
      </div>

      {(paychecks || investments) && (
        <Card className="card-pad col gap-3">
          <div>
            <h3>Recent outgoing payments</h3>
            <p className="muted">Paychecks and project investments, newest first.</p>
          </div>
          <Table
            columns={[
              { key: 'date', header: 'Date', render: (r) => fmtDate(r.date) },
              { key: 'kind', header: 'Kind', render: (r) => <Badge status={r.kind} /> },
              { key: 'party', header: 'Paid to', render: (r) => <span className="cell-strong">{r.party}</span> },
              { key: 'note', header: 'Detail', render: (r) => <span className="muted">{r.note}</span> },
              { key: 'amount', header: 'Amount', align: 'right', render: (r) => <span className="cell-num">{currency(r.amount)}</span> },
            ]}
            rows={tx}
            empty={{ title: 'No payments yet', hint: 'Paychecks and investments will show up here.' }}
          />
        </Card>
      )}
    </div>
  )
}
