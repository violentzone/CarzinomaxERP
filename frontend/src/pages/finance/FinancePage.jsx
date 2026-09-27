import { useState } from 'react'
import { Wallet, BookOpen, PieChart as PieIcon } from 'lucide-react'
import PageHeader from '../../components/ui/PageHeader'
import Tabs from '../../components/ui/Tabs'
import Badge from '../../components/ui/Badge'
import ResourceSection from '../../components/ResourceSection'
import { Select } from '../../components/ui/Field'
import { financeApi, EXPENSE_TYPES } from '../../api/finance'
import { dateTime, shortId, titleize } from '../../lib/format'
import FinanceOverview from './FinanceOverview'

const TABS = [
  { key: 'overview', label: 'Overview', icon: PieIcon },
  { key: 'ledger', label: 'Expense ledger', icon: BookOpen },
]

const TYPE_OPTIONS = EXPENSE_TYPES.map((v) => ({ value: v, label: titleize(v) }))

const TYPE_HINTS = {
  paycheck: 'Salary or contractor payment to a member',
  petty_cash: 'Small day-to-day purchase',
  investment: 'Cloud, licences, hardware or consulting for a project',
  other: 'Anything else',
}

/** Finance: where the unit's money goes — overview across modules plus the typed expense ledger. */
export default function FinancePage() {
  const [tab, setTab] = useState('overview')

  return (
    <div className="module-page">
      <PageHeader
        title="Finance"
        subtitle="Payroll, project investments and purchases in one place, plus the expense ledger."
        icon={Wallet}
      />
      <Tabs tabs={TABS} active={tab} onChange={setTab} idBase="finance" />

      <div className="tab-panel">
        {tab === 'overview' && <FinanceOverview />}
        {tab === 'ledger' && <LedgerSection />}
      </div>
    </div>
  )
}

function LedgerSection() {
  const [typeFilter, setTypeFilter] = useState('')

  const summary = (rows) => (
    <div className="summary-row">
      {EXPENSE_TYPES.map((t) => {
        const n = rows.filter((r) => r.expense_type === t).length
        return (
          <div key={t} className={`summary-tile ${n ? '' : ''}`} style={{ opacity: n ? 1 : 0.6 }}>
            <span className="sum-k">{titleize(t)}</span>
            <span className="sum-v">{n}</span>
            <span className="sum-hint">{TYPE_HINTS[t]}</span>
          </div>
        )
      })}
    </div>
  )

  return (
    <ResourceSection
      title="Expense ledger"
      subtitle="Every recorded expense, classified by type."
      moduleName="Finance"
      fetcher={() => financeApi.listExpenses()}
      create={financeApi.createExpense}
      createLabel="Record expense"
      createTitle="Record an expense"
      update={(row, payload) => financeApi.updateExpense(row.id, payload)}
      updateTitle="Edit expense"
      remove={(row) => financeApi.deleteExpense(row.id)}
      removeLabel="expense"
      removeHint={(r) => `${titleize(r.expense_type)} · ${shortId(r.id)} · ${dateTime(r.created_at)}`}
      emptyHint="Record your first expense to start the ledger."
      emptyIcon={BookOpen}
      modalSize="sm"
      summary={summary}
      rowsTransform={(rows) =>
        [...rows]
          .filter((r) => !typeFilter || r.expense_type === typeFilter)
          .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
      }
      toolbarExtra={
        <Select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} aria-label="Filter by type">
          <option value="">All types</option>
          {TYPE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </Select>
      }
      columns={[
        { key: 'id', header: 'Ref', render: (r) => <span className="mono muted" title={r.id}>{shortId(r.id)}</span> },
        { key: 'expense_type', header: 'Type', render: (r) => <Badge status={r.expense_type} /> },
        { key: 'hint', header: 'Meaning', render: (r) => <span className="cell-sub">{TYPE_HINTS[r.expense_type] || '—'}</span> },
        { key: 'created_at', header: 'Recorded', render: (r) => dateTime(r.created_at) },
        { key: 'updated_at', header: 'Updated', render: (r) => <span className="muted">{dateTime(r.updated_at)}</span> },
      ]}
      fields={[
        {
          key: 'expense_type',
          label: 'Expense type',
          type: 'select',
          required: true,
          full: true,
          options: TYPE_OPTIONS,
          default: 'other',
          hint: 'The ledger classifies each expense; amounts live with the paycheck or investment it refers to.',
        },
      ]}
    />
  )
}
