import { useCallback, useEffect, useRef, useState } from 'react'
import { Wallet, BookOpen, PieChart as PieIcon, ScanLine, Paperclip } from 'lucide-react'
import PageHeader from '../../components/ui/PageHeader'
import Tabs from '../../components/ui/Tabs'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import Modal from '../../components/ui/Modal'
import Spinner from '../../components/ui/Spinner'
import ResourceSection from '../../components/ResourceSection'
import { Select } from '../../components/ui/Field'
import { useAuth } from '../../context/AuthContext'
import { useToast } from '../../context/ToastContext'
import { useList } from '../../lib/useList'
import { financeApi, EXPENSE_TYPES, EXPENSE_CATEGORIES } from '../../api/finance'
import { devApi } from '../../api/devTracking'
import { num, currency, date as fmtDate, shortId, titleize, today, fileSize, BASE_CURRENCY } from '../../lib/format'
import { isOverdue } from '../../lib/expenses'
import { UPLOAD_ACCEPT, UPLOAD_MAX_BYTES } from '../../lib/uploads'
import FinanceOverview from './FinanceOverview'

const TABS = [
  { key: 'overview', label: 'Overview', icon: PieIcon },
  { key: 'ledger', label: 'Expense ledger', icon: BookOpen },
]

const TYPE_OPTIONS = EXPENSE_TYPES.map((v) => ({ value: v, label: titleize(v) }))
const CATEGORY_OPTIONS = EXPENSE_CATEGORIES.map((v) => ({ value: v, label: titleize(v) }))

/** Finance: where the unit's money goes — overview across modules plus the expense ledger. */
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

/**
 * The ledger itself. "Record expense" opens the blank form; "Book from receipt"
 * uploads a receipt or invoice, lets the AI read it (`POST /finance/receipt`) and
 * opens the same form prefilled with the draft — nothing is saved until Save.
 * A row booked from a receipt opens that document in `ReceiptModal`.
 */
function LedgerSection() {
  const { can } = useAuth()
  const toast = useToast()
  const [typeFilter, setTypeFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [reading, setReading] = useState(false)
  const [viewing, setViewing] = useState(null) // the expense whose receipt is open
  const closeReceipt = useCallback(() => setViewing(null), [])
  const fileRef = useRef(null)
  // Projects are only needed for the project link; a user without dev access sees no project field
  const projects = useList(() => (can('dev') ? devApi.listProjects() : Promise.resolve([])), [])
  const projectOptions = [...projects.rows]
    .sort((a, b) => a.project_name.localeCompare(b.project_name))
    .map((p) => ({ value: String(p.project_id), label: p.project_name }))
  const projectMap = Object.fromEntries(projects.rows.map((p) => [String(p.project_id), p]))
  const projectName = (id) => projectMap[String(id)]?.project_name || `Project #${id}`

  /** Upload the picked file, read it, then open the create form with the draft. */
  const readReceipt = async (file, openCreate) => {
    if (!file) return
    if (file.size > UPLOAD_MAX_BYTES) {
      toast.error(`${file.name} is larger than ${fileSize(UPLOAD_MAX_BYTES)}`)
      return
    }
    setReading(true)
    try {
      const { draft, receipt_path, note } = await financeApi.readReceipt(file)
      if (!draft) {
        openCreate({ receipt_path }, `Could not read the receipt: ${note}. Fill in the expense by hand; the file stays attached.`)
        return
      }
      const expenseDate = draft.expense_date || today()
      const values = {
        expense_type: draft.expense_type || '',
        amount: draft.amount ?? '',
        vendor: draft.vendor || '',
        reference: draft.reference || '',
        description: draft.description || '',
        category: draft.category || '',
        expense_date: expenseDate,
        due_date: draft.due_date || '',
        // A till or card receipt proves payment; an invoice stays an open bill
        paid_date: draft.paid ? expenseDate : '',
        project_id: draft.project_id ? String(draft.project_id) : '',
        receipt_path,
      }
      const remarks = [
        `Read with ${draft.confidence} confidence`,
        draft.paid === null ? 'could not tell whether it is paid' : null,
        draft.currency && draft.currency !== BASE_CURRENCY ? `the amount is printed in ${draft.currency}, the books are in ${BASE_CURRENCY}` : null,
        draft.notes,
      ].filter(Boolean)
      openCreate(values, `${remarks.join(' · ')}. Check every field before saving.`)
    } catch (err) {
      toast.error(err?.detail || err?.message || 'Could not read the receipt')
    } finally {
      setReading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const summary = (rows) => {
    const unpaid = rows.filter((r) => !r.paid_date)
    const overdue = unpaid.filter(isOverdue)
    const sum = (list) => list.reduce((s, r) => s + num(r.amount), 0)
    const tiles = [
      { k: 'Booked', v: currency(sum(rows)), hint: `${rows.length} expenses` },
      { k: 'Unpaid', v: currency(sum(unpaid)), hint: `${unpaid.length} open` },
      { k: 'Overdue', v: currency(sum(overdue)), hint: `${overdue.length} past due`, accent: overdue.length > 0 },
      { k: 'With receipt', v: rows.filter((r) => r.receipt_path).length, hint: 'booked from a document' },
    ]
    return (
      <div className="summary-row">
        {tiles.map((t) => (
          <div key={t.k} className={`summary-tile ${t.accent ? 'accent' : ''}`}>
            <span className="sum-k">{t.k}</span>
            <span className="sum-v">{t.v}</span>
            <span className="sum-hint">{t.hint}</span>
          </div>
        ))}
      </div>
    )
  }

  const fields = [
    { key: 'expense_type', label: 'Expense type', type: 'select', required: true, options: TYPE_OPTIONS, hint: 'Investment: cloud, licences, hardware or consulting for a project.' },
    { key: 'amount', label: 'Amount', type: 'number', step: '0.01', min: 0, required: true },
    { key: 'vendor', label: 'Vendor', placeholder: 'Amazon Web Services, GitHub…', nullable: true },
    { key: 'reference', label: 'Invoice / receipt no.', placeholder: 'INV-0725', nullable: true },
    { key: 'expense_date', label: 'Document date', type: 'date', required: true, default: today() },
    { key: 'due_date', label: 'Due date', type: 'date', nullable: true },
    { key: 'category', label: 'Category', type: 'select', options: CATEGORY_OPTIONS, nullable: true },
    { key: 'paid_date', label: 'Paid on', type: 'date', nullable: true, hint: 'Leave empty while the bill is open; clearing it re-opens the bill.' },
    ...(projectOptions.length
      ? [{ key: 'project_id', label: 'Project', type: 'select', numeric: true, full: true, options: projectOptions, placeholder: 'No project', hint: 'An investment linked to a project is also recorded under Dev Tracking.' }]
      : []),
    { key: 'description', label: 'Description', type: 'textarea', full: true, nullable: true },
  ]

  return (
    <>
      <ResourceSection
        title="Expense ledger"
        subtitle="Every recorded expense: who was paid, for what, and whether the bill is settled."
        moduleName="Finance"
        fetcher={() => financeApi.listExpenses()}
        create={financeApi.createExpense}
        createLabel="Record expense"
        createTitle="Record an expense"
        update={(row, payload) => financeApi.updateExpense(row.id, payload)}
        updateTitle="Edit expense"
        remove={(row) => financeApi.deleteExpense(row.id)}
        removeLabel="expense"
        removeHint={(r) => `${titleize(r.expense_type)} · ${r.vendor || 'no vendor'} · ${currency(r.amount)} · ${fmtDate(r.expense_date)} · ${shortId(r.id)}`}
        emptyHint="Record your first expense, or book one from a receipt."
        emptyIcon={BookOpen}
        summary={summary}
        // The receipt path is not a form field; it rides along from the draft on create only
        preparePayload={(payload, editing, values) => (!editing && values.receipt_path ? { ...payload, receipt_path: values.receipt_path } : payload)}
        rowsTransform={(rows) =>
          [...rows]
            .filter((r) => !typeFilter || r.expense_type === typeFilter)
            .filter((r) => {
              if (statusFilter === 'unpaid') return !r.paid_date
              if (statusFilter === 'overdue') return isOverdue(r)
              if (statusFilter === 'paid') return Boolean(r.paid_date)
              return true
            })
            .sort((a, b) => b.expense_date.localeCompare(a.expense_date) || new Date(b.created_at) - new Date(a.created_at))
        }
        toolbarExtra={({ openCreate }) => (
          <>
            <Select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} aria-label="Filter by type">
              <option value="">All types</option>
              {TYPE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </Select>
            <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} aria-label="Filter by payment status">
              <option value="">Paid and unpaid</option>
              <option value="unpaid">Unpaid</option>
              <option value="overdue">Overdue</option>
              <option value="paid">Paid</option>
            </Select>
            <input
              ref={fileRef}
              type="file"
              accept={UPLOAD_ACCEPT}
              hidden
              onChange={(e) => readReceipt(e.target.files?.[0], openCreate)}
            />
            <Button variant="outline" icon={ScanLine} loading={reading} onClick={() => fileRef.current?.click()}>
              {reading ? 'Reading receipt…' : 'Book from receipt'}
            </Button>
          </>
        )}
        rowActions={(r) =>
          r.receipt_path ? (
            <button type="button" className="icon-btn" onClick={() => setViewing(r)} aria-label="View receipt" title="View receipt">
              <Paperclip size={15} />
            </button>
          ) : null
        }
        columns={[
          { key: 'expense_date', header: 'Date', render: (r) => fmtDate(r.expense_date) },
          {
            key: 'vendor',
            header: 'Vendor',
            render: (r) => (
              <span>
                <span className="cell-strong">
                  {r.receipt_path ? (
                    // Booked from a document: the name opens the receipt
                    <button type="button" className="link-btn" onClick={() => setViewing(r)} title="View receipt" aria-label={`View receipt from ${r.vendor || 'unknown vendor'}`}>
                      {r.vendor || '—'}
                      <Paperclip size={12} style={{ marginLeft: 6, verticalAlign: -1 }} aria-hidden="true" />
                    </button>
                  ) : (
                    r.vendor || '—'
                  )}
                </span>
                <span className="cell-sub">{r.reference || r.description || ''}</span>
              </span>
            ),
          },
          { key: 'expense_type', header: 'Type', render: (r) => <Badge status={r.expense_type} /> },
          { key: 'category', header: 'Category', render: (r) => (r.category ? <Badge status={r.category} /> : <span className="muted">—</span>) },
          { key: 'amount', header: 'Amount', align: 'right', render: (r) => <span className="cell-num">{currency(r.amount)}</span> },
          {
            key: 'due_date',
            header: 'Due',
            render: (r) => (isOverdue(r) ? <Badge status="overdue">{fmtDate(r.due_date)}</Badge> : fmtDate(r.due_date)),
          },
          { key: 'paid_date', header: 'Paid', render: (r) => (r.paid_date ? fmtDate(r.paid_date) : <Badge status="unpaid" />) },
          ...(can('dev')
            ? [{ key: 'project_id', header: 'Project', render: (r) => (r.project_id ? <span className="cell-strong">{projectName(r.project_id)}</span> : <span className="muted">—</span>) }]
            : []),
        ]}
        fields={fields}
      />
      <ReceiptModal expense={viewing} onClose={closeReceipt} />
    </>
  )
}

/**
 * Shows the receipt or invoice an expense was booked from. The file is fetched
 * with the bearer token (`GET /finance/expense/{id}/receipt`) and shown through an
 * object URL: an image inline, a PDF in a frame. The modal stays mounted and
 * `open` follows `expense`; what it shows follows the last opened expense, so the
 * close animation keeps its content and re-opening the same row needs no refetch.
 */
function ReceiptModal({ expense, onClose }) {
  // The last opened expense; derived-state update during render, as React documents for a prop that may go null
  const [shown, setShown] = useState(expense)
  if (expense && expense !== shown) setShown(expense)
  const shownId = shown?.id
  // The outcome of the last fetch, tagged with its expense id so a stale result never shows for another row
  const [loaded, setLoaded] = useState(null) // { id, url, type } or { id, error }
  const current = loaded?.id === shownId ? loaded : null
  const file = current?.url ? current : null
  const error = current?.error || null
  // Re-opening a row whose fetch failed retries it; `attempt` re-runs the effect because the id does not change
  const [attempt, setAttempt] = useState(0)
  const [wasOpen, setWasOpen] = useState(Boolean(expense))
  if (Boolean(expense) !== wasOpen) {
    setWasOpen(Boolean(expense))
    if (expense && error) setAttempt((count) => count + 1)
  }

  useEffect(() => {
    if (!shownId) return undefined
    let cancelled = false
    let url = null
    financeApi
      .fetchReceipt(shownId)
      .then((blob) => {
        url = URL.createObjectURL(blob)
        // Superseded before the file arrived: release the URL right away instead of leaking it
        if (cancelled) {
          URL.revokeObjectURL(url)
          return
        }
        setLoaded({ id: shownId, url, type: blob.type })
      })
      .catch((err) => {
        if (!cancelled) setLoaded({ id: shownId, error: err?.detail || err?.message || 'Could not load the receipt' })
      })
    return () => {
      // Runs when another row is opened or the ledger unmounts, not on close. Revoking also breaks a reload in a tab opened from the footer link
      cancelled = true
      if (url) URL.revokeObjectURL(url)
      setLoaded((previous) => (previous?.id === shownId ? null : previous))
    }
  }, [shownId, attempt])

  const subtitle = shown ? [shown.reference, fmtDate(shown.expense_date), currency(shown.amount)].filter(Boolean).join(' · ') : ''

  return (
    <Modal
      open={Boolean(expense)}
      onClose={onClose}
      title={`Receipt · ${shown?.vendor || 'expense'}`}
      subtitle={subtitle}
      size="lg"
      footer={
        <>
          {file && (
            <a className="btn btn-outline btn-md" href={file.url} target="_blank" rel="noopener">
              Open in new tab
            </a>
          )}
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
        </>
      }
    >
      <div className="receipt-box">
        {error ? (
          <div className="muted">{error}</div>
        ) : !file ? (
          <Spinner />
        ) : file.type.startsWith('image/') ? (
          <img className="receipt-view" src={file.url} alt={`Receipt from ${shown?.vendor || 'the vendor'}`} />
        ) : (
          <iframe className="receipt-frame" src={file.url} title="Receipt" />
        )}
      </div>
    </Modal>
  )
}
