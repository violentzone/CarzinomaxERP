import { useState } from 'react'
import { Plus, Download } from 'lucide-react'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts'
import { devApi } from '../../api/devTracking'
import { useList } from '../../lib/useList'
import { useToast } from '../../context/ToastContext'
import { num, number, date as fmtDate, today, titleize } from '../../lib/format'
import Card from '../../components/ui/Card'
import Table from '../../components/ui/Table'
import Button from '../../components/ui/Button'
import Modal from '../../components/ui/Modal'
import Badge from '../../components/ui/Badge'
import AccessDenied from '../../components/ui/AccessDenied'
import { SchemaForm, initialValues, buildPayload } from '../../components/SchemaForm'

const PLATFORMS = ['github', 'npm', 'pypi', 'dockerhub'].map((v) => ({ value: v, label: titleize(v) }))

const FIELDS = [
  { key: 'date', label: 'Date', type: 'date', required: true, default: today() },
  { key: 'platform', label: 'Platform', type: 'select', default: 'github', options: PLATFORMS },
  { key: 'download_count', label: 'Downloads', type: 'number', required: true, min: 0 },
  { key: 'star_count', label: 'Stars', type: 'number', min: 0 },
]

/** Download logs with a traction trend chart above a list + create modal. */
export default function DownloadsSection() {
  const toast = useToast()
  const { rows, loading, denied, reload } = useList(() => devApi.listDownloads())
  const [open, setOpen] = useState(false)
  const [values, setValues] = useState(() => initialValues(FIELDS))
  const [saving, setSaving] = useState(false)

  if (denied) return <AccessDenied module="Dev Tracking" />

  const series = [...(rows || [])]
    .sort((a, b) => new Date(a.date) - new Date(b.date))
    .map((d) => ({ date: fmtDate(d.date), downloads: num(d.download_count) }))

  const openModal = () => {
    setValues(initialValues(FIELDS))
    setOpen(true)
  }

  const submit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      await devApi.createDownload(buildPayload(FIELDS, values))
      toast.success('Download log saved')
      setOpen(false)
      reload()
    } catch (err) {
      toast.error(err?.detail || 'Could not save download log')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <div className="section-toolbar">
        <div>
          <h2>Project Downloads</h2>
          <div className="muted">Download and star counts tracked over time.</div>
        </div>
        <div className="filter-row">
          <Button icon={Plus} onClick={openModal}>
            New download log
          </Button>
        </div>
      </div>

      <Card className="chart-card">
        <h3>
          <Download size={15} style={{ verticalAlign: -2, marginRight: 6 }} />
          Downloads over time
        </h3>
        {series.length ? (
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={series} margin={{ left: -18, right: 6, top: 6 }}>
              <defs>
                <linearGradient id="dl-trend" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#aa3bff" stopOpacity={0.55} />
                  <stop offset="100%" stopColor="#aa3bff" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: 'var(--text-dim)' }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 11, fill: 'var(--text-dim)' }} tickLine={false} axisLine={false} />
              <Tooltip />
              <Area type="monotone" dataKey="downloads" stroke="#aa3bff" strokeWidth={2.5} fill="url(#dl-trend)" />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="chart-empty">No download data yet</div>
        )}
      </Card>

      <Table
        columns={[
          { key: 'date', header: 'Date', render: (r) => fmtDate(r.date) },
          { key: 'platform', header: 'Platform', render: (r) => <Badge tone="info">{titleize(r.platform)}</Badge> },
          { key: 'download_count', header: 'Downloads', align: 'right', render: (r) => <span className="cell-num">{number(r.download_count)}</span> },
          { key: 'star_count', header: 'Stars', align: 'right', render: (r) => <span className="cell-num">{r.star_count == null || r.star_count === '' ? '—' : number(r.star_count)}</span> },
        ]}
        rows={rows}
        loading={loading}
        empty={{ title: 'No download logs yet', hint: 'Log your first download snapshot.', action: <Button icon={Plus} variant="outline" onClick={openModal}>New download log</Button> }}
      />

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="New download log"
        footer={
          <>
            <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" form="download-form" loading={saving}>Save</Button>
          </>
        }
      >
        <form id="download-form" onSubmit={submit}>
          <SchemaForm fields={FIELDS} values={values} setField={(k, v) => setValues((s) => ({ ...s, [k]: v }))} />
        </form>
      </Modal>
    </div>
  )
}
