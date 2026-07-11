import { useState } from 'react'
import {
  BookOpen,
  FileText,
  HandCoins,
  Landmark,
  Scale,
  Wallet,
} from 'lucide-react'
import PageHeader from '../../components/ui/PageHeader'
import Tabs from '../../components/ui/Tabs'
import ResourceSection from '../../components/ResourceSection'
import Badge from '../../components/ui/Badge'
import { financeApi } from '../../api/finance'
import { currency, titleize } from '../../lib/format'
import InvoicesSection from './InvoicesSection'
import PaymentsSection from './PaymentsSection'
import JournalSection from './JournalSection'

const TABS = [
  { key: 'accounts', label: 'GL Accounts', icon: BookOpen },
  { key: 'invoices', label: 'Invoices', icon: FileText },
  { key: 'payments', label: 'Payments', icon: HandCoins },
  { key: 'assets', label: 'Fixed Assets', icon: Landmark },
  { key: 'journal', label: 'Journal', icon: Scale },
]

const ACCOUNT_TYPES = ['asset', 'liability', 'equity', 'revenue', 'expense'].map((v) => ({
  value: v,
  label: titleize(v),
}))

export default function FinancePage() {
  const [tab, setTab] = useState('accounts')

  return (
    <div className="module-page">
      <PageHeader
        title="Finance & Accounting"
        subtitle="General ledger, invoicing, payments, assets and journals."
        icon={Wallet}
      />
      <Tabs tabs={TABS} active={tab} onChange={setTab} idBase="finance" />

      <div className="tab-panel">
        {tab === 'accounts' && (
          <ResourceSection
            title="GL Accounts"
            subtitle="Chart of accounts for the general ledger."
            moduleName="Finance"
            fetcher={() => financeApi.listAccounts()}
            create={financeApi.createAccount}
            createLabel="New account"
            createTitle="New GL account"
            update={(row, payload) => financeApi.updateAccount(row.id, payload)}
            updateTitle="Edit GL account"
            remove={(row) => financeApi.deleteAccount(row.id)}
            removeLabel="GL account"
            removeHint="Accounts used by journal entries cannot be deleted."
            columns={[
              { key: 'code', header: 'Code', render: (r) => <span className="mono cell-strong">{r.code}</span> },
              { key: 'name', header: 'Name', render: (r) => <span className="cell-strong">{r.name}</span> },
              { key: 'type', header: 'Type', render: (r) => <Badge tone="info">{titleize(r.type)}</Badge> },
              { key: 'description', header: 'Description', render: (r) => <span className="muted">{r.description || '—'}</span> },
            ]}
            fields={[
              { key: 'code', label: 'Account code', required: true, placeholder: '1000' },
              { key: 'name', label: 'Name', required: true, placeholder: 'Cash & equivalents' },
              { key: 'type', label: 'Type', type: 'select', required: true, options: ACCOUNT_TYPES },
              { key: 'description', label: 'Description', type: 'textarea', full: true, nullable: true },
            ]}
          />
        )}

        {tab === 'invoices' && <InvoicesSection />}
        {tab === 'payments' && <PaymentsSection />}

        {tab === 'assets' && (
          <ResourceSection
            title="Fixed Assets"
            subtitle="Track equipment cost, depreciation and lifecycle."
            moduleName="Finance"
            fetcher={() => financeApi.listFixedAssets()}
            create={financeApi.createFixedAsset}
            createLabel="New asset"
            createTitle="Register fixed asset"
            update={(row, payload) => financeApi.updateFixedAsset(row.id, payload)}
            updateTitle="Edit fixed asset"
            remove={(row) => financeApi.deleteFixedAsset(row.id)}
            removeLabel="fixed asset"
            columns={[
              { key: 'asset_code', header: 'Code', render: (r) => <span className="mono cell-strong">{r.asset_code}</span> },
              { key: 'name', header: 'Name', render: (r) => <span className="cell-strong">{r.name}</span> },
              { key: 'category', header: 'Category', render: (r) => titleize(r.category) },
              { key: 'cost', header: 'Cost', align: 'right', render: (r) => <span className="cell-num">{currency(r.cost)}</span> },
              { key: 'current_value', header: 'Value', align: 'right', render: (r) => <span className="cell-num">{currency(r.current_value)}</span> },
              { key: 'status', header: 'Status', render: (r) => <Badge status={r.status} /> },
            ]}
            fields={[
              { key: 'name', label: 'Asset name', required: true, placeholder: 'MacBook Pro 16"' },
              { key: 'asset_code', label: 'Asset code', required: true, placeholder: 'FA-001' },
              { key: 'category', label: 'Category', required: true, placeholder: 'IT Equipment' },
              { key: 'acquisition_date', label: 'Acquired on', type: 'date', required: true },
              { key: 'cost', label: 'Cost', type: 'number', step: '0.01', required: true },
              { key: 'current_value', label: 'Current value', type: 'number', step: '0.01', required: true },
              {
                key: 'depreciation_method',
                label: 'Depreciation',
                type: 'select',
                default: 'straight_line',
                options: [
                  { value: 'straight_line', label: 'Straight line' },
                  { value: 'declining_balance', label: 'Declining balance' },
                ],
              },
              {
                key: 'status',
                label: 'Status',
                type: 'select',
                default: 'active',
                options: [
                  { value: 'active', label: 'Active' },
                  { value: 'disposed', label: 'Disposed' },
                ],
              },
            ]}
          />
        )}

        {tab === 'journal' && <JournalSection />}
      </div>
    </div>
  )
}
