import { useState } from 'react'
import { LineChart, Cloud, HandCoins, Download } from 'lucide-react'
import PageHeader from '../../components/ui/PageHeader'
import Tabs from '../../components/ui/Tabs'
import ResourceSection from '../../components/ResourceSection'
import Badge from '../../components/ui/Badge'
import { devApi } from '../../api/devTracking'
import { currency, date as fmtDate, titleize, today } from '../../lib/format'
import DownloadsSection from './DownloadsSection'

const TABS = [
  { key: 'investments', label: 'Investments', icon: Cloud },
  { key: 'paychecks', label: 'Worker Paychecks', icon: HandCoins },
  { key: 'downloads', label: 'Downloads', icon: Download },
]

const CATEGORIES = ['cloud', 'tooling', 'domain', 'other'].map((v) => ({ value: v, label: titleize(v) }))

/** Development tracking: cloud spend, contributor payouts and project traction. */
export default function DevTrackingPage() {
  const [tab, setTab] = useState('investments')

  return (
    <div className="module-page">
      <PageHeader
        title="Dev Tracking"
        subtitle="Cloud spend, contributor payouts and project traction."
        icon={LineChart}
      />
      <Tabs tabs={TABS} active={tab} onChange={setTab} idBase="dev" />

      <div className="tab-panel">
        {tab === 'investments' && (
          <ResourceSection
            title="Development Investments"
            subtitle="Payments spent on cloud services and tooling."
            moduleName="Dev Tracking"
            fetcher={() => devApi.listInvestments()}
            create={devApi.createInvestment}
            createLabel="New investment"
            createTitle="Log an investment"
            emptyHint="Track your first cloud or tooling spend."
            columns={[
              { key: 'date', header: 'Date', render: (r) => fmtDate(r.date) },
              { key: 'vendor', header: 'Vendor', render: (r) => <span className="cell-strong">{r.vendor}</span> },
              { key: 'category', header: 'Category', render: (r) => <Badge tone="info">{titleize(r.category)}</Badge> },
              { key: 'amount', header: 'Amount', align: 'right', render: (r) => <span className="cell-num">{currency(r.amount)}</span> },
              { key: 'description', header: 'Description', render: (r) => <span className="muted">{r.description || '—'}</span> },
            ]}
            fields={[
              { key: 'date', label: 'Date', type: 'date', required: true, default: today() },
              { key: 'vendor', label: 'Vendor', required: true, placeholder: 'AWS' },
              { key: 'category', label: 'Category', type: 'select', default: 'cloud', options: CATEGORIES },
              { key: 'amount', label: 'Amount', type: 'number', step: '0.01', required: true },
              { key: 'description', label: 'Description', type: 'textarea', full: true },
            ]}
          />
        )}

        {tab === 'paychecks' && (
          <ResourceSection
            title="Worker Paychecks"
            subtitle="Contributor payouts and project labour cost."
            moduleName="Dev Tracking"
            fetcher={() => devApi.listWorkerPaychecks()}
            create={devApi.createWorkerPaycheck}
            createLabel="New paycheck"
            createTitle="Record a paycheck"
            emptyHint="Record your first contributor payout."
            columns={[
              { key: 'worker_name', header: 'Worker', render: (r) => <span className="cell-strong">{r.worker_name}</span> },
              { key: 'role', header: 'Role' },
              { key: 'payment_date', header: 'Paid', render: (r) => fmtDate(r.payment_date) },
              { key: 'amount', header: 'Amount', align: 'right', render: (r) => <span className="cell-num">{currency(r.amount)}</span> },
            ]}
            fields={[
              { key: 'worker_name', label: 'Worker name', required: true, placeholder: 'Jane Doe' },
              { key: 'role', label: 'Role', required: true, placeholder: 'Backend Engineer' },
              { key: 'payment_date', label: 'Payment date', type: 'date', required: true, default: today() },
              { key: 'amount', label: 'Amount', type: 'number', step: '0.01', required: true },
              { key: 'description', label: 'Description', type: 'textarea', full: true },
            ]}
          />
        )}

        {tab === 'downloads' && <DownloadsSection />}
      </div>
    </div>
  )
}
