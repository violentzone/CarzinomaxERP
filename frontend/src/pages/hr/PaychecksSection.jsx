import { useState } from 'react'
import { Wallet } from 'lucide-react'
import { hrApi } from '../../api/hr'
import { useUsers } from '../../lib/useUsers'
import { num, currency } from '../../lib/format'
import ResourceSection from '../../components/ResourceSection'
import { Select } from '../../components/ui/Field'

/**
 * Paychecks — the standing pay setup of each member, paid out by the monthly
 * payroll run. Net pay is base + allowances − deductions, filled in when the
 * field is left blank.
 */
export default function PaychecksSection() {
  const { userOptions, nameOf } = useUsers()
  const [personFilter, setPersonFilter] = useState('')

  const fields = [
    {
      key: 'user_id',
      label: 'Member',
      type: 'select',
      numeric: true,
      required: true,
      full: true,
      options: userOptions,
      placeholder: userOptions.length ? 'Select a member…' : 'No users — create one first',
    },
    { key: 'base_salary', label: 'Base salary', type: 'number', step: '0.01', min: 0, required: true },
    { key: 'allowances', label: 'Allowances', type: 'number', step: '0.01', min: 0, default: 0 },
    { key: 'deductions', label: 'Deductions', type: 'number', step: '0.01', min: 0, default: 0 },
    { key: 'net_pay', label: 'Net pay', type: 'number', step: '0.01', hint: 'Leave blank to compute base + allowances − deductions.' },
  ]

  /** Keep net_pay consistent when the amounts change and no override was typed. */
  const preparePayload = (payload, editing, values) => {
    const typed = values.net_pay !== '' && values.net_pay !== undefined && values.net_pay !== null
    const base = payload.base_salary ?? num(editing?.base_salary)
    const allow = payload.allowances ?? num(editing?.allowances)
    const ded = payload.deductions ?? num(editing?.deductions)
    if (!typed) payload.net_pay = Math.round((base + allow - ded) * 100) / 100
    return payload
  }

  const rowsTransform = (rows) =>
    [...rows]
      .filter((r) => !personFilter || String(r.user_id) === personFilter)
      .sort((a, b) => nameOf(a.user_id).localeCompare(nameOf(b.user_id)))

  const summary = (rows) => {
    return (
      <div className="summary-row">
        <div className="summary-tile accent">
          <span className="sum-k">Net pay total</span>
          <span className="sum-v">{currency(rows.reduce((s, r) => s + num(r.net_pay), 0))}</span>
          <span className="sum-hint">{rows.length} paycheck{rows.length === 1 ? '' : 's'}</span>
        </div>
        <div className="summary-tile">
          <span className="sum-k">Base salary</span>
          <span className="sum-v">{currency(rows.reduce((s, r) => s + num(r.base_salary), 0))}</span>
          <span className="sum-hint">before allowances and deductions</span>
        </div>
        <div className="summary-tile">
          <span className="sum-k">Deductions</span>
          <span className="sum-v">{currency(rows.reduce((s, r) => s + num(r.deductions), 0))}</span>
          <span className="sum-hint">taken off base and allowances</span>
        </div>
        <div className="summary-tile">
          <span className="sum-k">People with a paycheck</span>
          <span className="sum-v">{new Set(rows.map((r) => r.user_id)).size}</span>
          <span className="sum-hint">distinct members</span>
        </div>
      </div>
    )
  }

  return (
    <ResourceSection
      title="Paychecks"
      subtitle="The standing pay setup of each member, paid out by the monthly payroll run."
      moduleName="People & Payroll"
      fetcher={() => hrApi.listPaychecks()}
      create={hrApi.createPaycheck}
      createLabel="New paycheck"
      createTitle="New paycheck"
      update={(row, payload) => hrApi.updatePaycheck(row.id, payload)}
      updateTitle="Edit paycheck"
      remove={(row) => hrApi.deletePaycheck(row.id)}
      removeLabel="paycheck"
      removeHint={(r) => `${nameOf(r.user_id)} · net ${currency(r.net_pay)}`}
      emptyHint="Set up the first paycheck for a team member."
      emptyIcon={Wallet}
      fields={fields}
      preparePayload={preparePayload}
      rowsTransform={rowsTransform}
      summary={summary}
      toolbarExtra={
        <>
          <Select value={personFilter} onChange={(e) => setPersonFilter(e.target.value)} aria-label="Filter by member">
            <option value="">All members</option>
            {userOptions.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </Select>
        </>
      }
      columns={[
        { key: 'user_id', header: 'Member', render: (r) => <span className="cell-strong">{nameOf(r.user_id)}</span> },
        { key: 'base_salary', header: 'Base', align: 'right', render: (r) => <span className="cell-num">{currency(r.base_salary)}</span> },
        { key: 'allowances', header: 'Allowances', align: 'right', render: (r) => <span className="cell-num muted">{currency(r.allowances)}</span> },
        { key: 'deductions', header: 'Deductions', align: 'right', render: (r) => <span className="cell-num muted">{num(r.deductions) ? `−${currency(r.deductions)}` : '—'}</span> },
        { key: 'net_pay', header: 'Net pay', align: 'right', render: (r) => <span className="cell-num cell-strong">{currency(r.net_pay)}</span> },
      ]}
    />
  )
}
