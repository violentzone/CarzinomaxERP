import { useState } from 'react'
import { Scale } from 'lucide-react'
import { financeApi } from '../../api/finance'
import { useList } from '../../lib/useList'
import { useToast } from '../../context/ToastContext'
import { num, currency, date as fmtDate, today, titleize } from '../../lib/format'
import Card from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import AccessDenied from '../../components/ui/AccessDenied'
import SessionList from '../../components/ui/SessionList'
import Badge from '../../components/ui/Badge'
import { SchemaForm } from '../../components/SchemaForm'
import LineItemsEditor from '../../components/ui/LineItemsEditor'

let seq = 0
const blankLine = () => ({ _key: ++seq, gl_account_id: '', debit: 0, credit: 0 })

/** Journal entries are POST-only and must balance (debits = credits). */
export default function JournalSection() {
  const toast = useToast()
  const { rows: accounts, denied } = useList(() => financeApi.listAccounts())
  const [header, setHeader] = useState({ entry_date: today(), status: 'draft' })
  const [lines, setLines] = useState([blankLine(), blankLine()])
  const [created, setCreated] = useState([])
  const [saving, setSaving] = useState(false)

  if (denied) return <AccessDenied module="Finance" />

  const accountOptions = (accounts || []).map((a) => ({ value: String(a.id), label: `${a.code} · ${a.name}` }))
  const totalDebit = lines.reduce((s, l) => s + num(l.debit), 0)
  const totalCredit = lines.reduce((s, l) => s + num(l.credit), 0)
  const balanced = totalDebit === totalCredit && totalDebit > 0
  const allAccounts = lines.every((l) => l.gl_account_id)

  const submit = async (e) => {
    e.preventDefault()
    if (!balanced) {
      toast.error('Debits must equal credits and be greater than zero.')
      return
    }
    setSaving(true)
    try {
      const entry = await financeApi.createJournalEntry({
        entry_date: header.entry_date,
        description: header.description,
        status: header.status || 'draft',
        lines: lines.map((l) => ({ gl_account_id: num(l.gl_account_id), debit: num(l.debit), credit: num(l.credit) })),
      })
      setCreated((c) => [{ ...entry, _debit: totalDebit }, ...c])
      toast.success('Journal entry posted')
      setHeader({ entry_date: today(), status: 'draft', description: '' })
      setLines([blankLine(), blankLine()])
    } catch (err) {
      toast.error(err?.detail || 'Could not create journal entry')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <div className="section-toolbar">
        <div>
          <h2>New journal entry</h2>
          <div className="muted">Double-entry — total debits must equal total credits.</div>
        </div>
      </div>

      <Card className="card-pad">
        <form onSubmit={submit} className="col gap-4">
          <SchemaForm
            fields={[
              { key: 'entry_date', label: 'Entry date', type: 'date', required: true, default: today() },
              { key: 'status', label: 'Status', type: 'select', default: 'draft', options: ['draft', 'posted'].map((v) => ({ value: v, label: titleize(v) })) },
              { key: 'description', label: 'Description', required: true, full: true, placeholder: 'e.g. Monthly rent accrual' },
            ]}
            values={header}
            setField={(k, v) => setHeader((s) => ({ ...s, [k]: v }))}
          />

          <LineItemsEditor
            fields={[
              { key: 'gl_account_id', label: 'Account', type: 'select', flex: 2.2, options: accountOptions, placeholder: accountOptions.length ? 'Select account…' : 'Create GL accounts first' },
              { key: 'debit', label: 'Debit', type: 'number', step: '0.01', min: 0 },
              { key: 'credit', label: 'Credit', type: 'number', step: '0.01', min: 0 },
            ]}
            value={lines}
            onChange={setLines}
            newRow={blankLine}
            addLabel="Add line"
            summary={() => (
              <>
                <span><span className="sum-k">Debit</span> <span className="sum-v">{currency(totalDebit)}</span></span>
                <span><span className="sum-k">Credit</span> <span className="sum-v">{currency(totalCredit)}</span></span>
                <span className={balanced ? 'balance-ok' : 'balance-bad'}>
                  {balanced ? '● Balanced' : `● Off by ${currency(Math.abs(totalDebit - totalCredit))}`}
                </span>
              </>
            )}
          />

          <div className="row" style={{ justifyContent: 'flex-end' }}>
            <Button type="submit" icon={Scale} loading={saving} disabled={!balanced || !allAccounts}>
              Post entry
            </Button>
          </div>
        </form>
      </Card>

      <SessionList
        items={created}
        title="Entries posted this session"
        columns={[
          { key: 'id', header: '#', render: (r) => <span className="mono">{r.id}</span> },
          { key: 'entry_date', header: 'Date', render: (r) => fmtDate(r.entry_date) },
          { key: 'description', header: 'Description' },
          { key: 'lines', header: 'Lines', align: 'right', render: (r) => r.lines?.length ?? '—' },
          { key: '_debit', header: 'Amount', align: 'right', render: (r) => <span className="cell-num">{currency(r._debit)}</span> },
          { key: 'status', header: 'Status', render: (r) => <Badge status={r.status} /> },
        ]}
      />
    </div>
  )
}
