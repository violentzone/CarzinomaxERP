import { useState } from 'react'
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'
import { LineChart, FolderKanban, Cloud, Download, Star } from 'lucide-react'
import PageHeader from '../../components/ui/PageHeader'
import Tabs from '../../components/ui/Tabs'
import ResourceSection from '../../components/ResourceSection'
import Badge from '../../components/ui/Badge'
import Card from '../../components/ui/Card'
import { Select } from '../../components/ui/Field'
import { devApi, INVESTMENT_CATEGORIES, DOWNLOAD_PLATFORMS } from '../../api/devTracking'
import { useList } from '../../lib/useList'
import { projectStats, downloadSeries } from '../../lib/devStats'
import { num, currency, compactCurrency, number, compactNumber, date as fmtDate, titleize, today, parseDate } from '../../lib/format'

const TABS = [
  { key: 'projects', label: 'Projects', icon: FolderKanban },
  { key: 'investments', label: 'Investments', icon: Cloud },
  { key: 'downloads', label: 'Downloads', icon: Download },
]

const CATEGORIES = INVESTMENT_CATEGORIES.map((v) => ({ value: v, label: titleize(v) }))
const PLATFORMS = DOWNLOAD_PLATFORMS.map((v) => ({ value: v, label: titleize(v) }))

/** Dev tracking: the programs being built, what they cost, and how they're doing out there. */
export default function DevTrackingPage() {
  const [tab, setTab] = useState('projects')
  // Shared lookups; `tick` bumps to re-fetch after a section mutates them.
  const [tick, setTick] = useState(0)
  const projects = useList(() => devApi.listProjects(), [tick])
  const investments = useList(() => devApi.listInvestments(), [tick])
  const downloads = useList(() => devApi.listDownloads(), [tick])
  const refresh = () => setTick((t) => t + 1)

  const projectOptions = [...projects.rows]
    .sort((a, b) => a.project_name.localeCompare(b.project_name))
    .map((p) => ({ value: String(p.project_id), label: p.project_name }))
  const projectMap = Object.fromEntries(projects.rows.map((p) => [String(p.project_id), p]))
  const projectName = (id) => projectMap[String(id)]?.project_name || `Project #${id}`

  return (
    <div className="module-page">
      <PageHeader
        title="Dev Tracking"
        subtitle="Programs under development: status, money invested and adoption."
        icon={LineChart}
      />
      <Tabs tabs={TABS} active={tab} onChange={setTab} idBase="dev" />

      <div className="tab-panel">
        {tab === 'projects' && (
          <ProjectsSection
            key={tick}
            investments={investments.rows}
            downloads={downloads.rows}
            onChanged={refresh}
          />
        )}
        {tab === 'investments' && (
          <InvestmentsSection key={tick} projectOptions={projectOptions} projectName={projectName} onChanged={refresh} />
        )}
        {tab === 'downloads' && (
          <DownloadsSection key={tick} projectOptions={projectOptions} projectName={projectName} onChanged={refresh} />
        )}
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------------ */

function ProjectsSection({ investments, downloads, onChanged }) {
  const wrap = (fn) => async (...args) => {
    const out = await fn(...args)
    onChanged()
    return out
  }

  const summary = (rows) => {
    const stats = projectStats(rows, investments, downloads)
    const spend = Object.values(stats).reduce((s, p) => s + p.spend, 0)
    const dls = Object.values(stats).reduce((s, p) => s + p.downloads, 0)
    const stars = Object.values(stats).reduce((s, p) => s + p.stars, 0)
    return (
      <div className="summary-row">
        <div className="summary-tile accent">
          <span className="sum-k">Projects</span>
          <span className="sum-v">{rows.length}</span>
        </div>
        <div className="summary-tile">
          <span className="sum-k">Total invested</span>
          <span className="sum-v">{currency(spend)}</span>
        </div>
        <div className="summary-tile">
          <span className="sum-k">Downloads</span>
          <span className="sum-v">{number(dls)}</span>
          <span className="sum-hint">latest snapshot per platform</span>
        </div>
        <div className="summary-tile">
          <span className="sum-k">Stars</span>
          <span className="sum-v">{number(stars)}</span>
        </div>
      </div>
    )
  }

  return (
    <ResourceSection
      title="Projects"
      subtitle="Each program being developed, with its spend and traction."
      moduleName="Dev Tracking"
      idKey="project_id"
      fetcher={() => devApi.listProjects()}
      create={wrap(devApi.createProject)}
      createLabel="New project"
      createTitle="New project"
      update={wrap((row, payload) => devApi.updateProject(row.project_id, payload))}
      updateTitle="Edit project"
      remove={wrap((row) => devApi.deleteProject(row.project_id))}
      removeLabel="project"
      removeHint={(r) => `${r.project_name} — its investments and download records are deleted too.`}
      emptyHint="Add the first program you are developing."
      emptyIcon={FolderKanban}
      summary={summary}
      rowsTransform={(rows) => [...rows].sort((a, b) => a.project_name.localeCompare(b.project_name))}
      columns={[
        {
          key: 'project_name',
          header: 'Project',
          render: (r) => (
            <div className="col">
              <span className="cell-strong">{r.project_name}</span>
              {r.project_description && <span className="cell-sub">{r.project_description}</span>}
            </div>
          ),
        },
        {
          key: 'spend',
          header: 'Invested',
          align: 'right',
          render: (r) => {
            const s = projectStats([r], investments, downloads)[String(r.project_id)]
            return <span className="cell-num">{s.investmentCount ? currency(s.spend) : <span className="muted">—</span>}</span>
          },
        },
        {
          key: 'downloads',
          header: 'Downloads',
          align: 'right',
          render: (r) => {
            const s = projectStats([r], investments, downloads)[String(r.project_id)]
            return <span className="cell-num">{s.snapshotCount ? number(s.downloads) : <span className="muted">—</span>}</span>
          },
        },
        {
          key: 'stars',
          header: 'Stars',
          align: 'right',
          render: (r) => {
            const s = projectStats([r], investments, downloads)[String(r.project_id)]
            return s.stars ? (
              <span className="cell-num">
                <Star size={12} style={{ verticalAlign: -1, marginRight: 3 }} />
                {number(s.stars)}
              </span>
            ) : (
              <span className="muted">—</span>
            )
          },
        },
        {
          key: 'platforms',
          header: 'Platforms',
          render: (r) => {
            const s = projectStats([r], investments, downloads)[String(r.project_id)]
            return s.platforms.length ? (
              <span className="row gap-1 wrap">
                {s.platforms.map((p) => (
                  <Badge key={p} status={p} />
                ))}
              </span>
            ) : (
              <span className="muted">—</span>
            )
          },
        },
        {
          key: 'last',
          header: 'Last activity',
          render: (r) => {
            const s = projectStats([r], investments, downloads)[String(r.project_id)]
            return <span className="muted">{s.lastDate ? fmtDate(s.lastDate) : fmtDate(r.created_at)}</span>
          },
        },
      ]}
      fields={[
        { key: 'project_name', label: 'Project name', required: true, placeholder: 'Carzinomax ERP', full: true },
        { key: 'project_description', label: 'Description', type: 'textarea', full: true, nullable: true, placeholder: 'What is it, where is it at?' },
      ]}
    />
  )
}

/* ------------------------------------------------------------------------ */

function InvestmentsSection({ projectOptions, projectName, onChanged }) {
  const [projectFilter, setProjectFilter] = useState('')
  const wrap = (fn) => async (...args) => {
    const out = await fn(...args)
    onChanged()
    return out
  }

  const summary = (rows) => {
    const total = rows.reduce((s, r) => s + num(r.amount), 0)
    const byCat = {}
    for (const r of rows) byCat[r.category] = (byCat[r.category] || 0) + num(r.amount)
    const top = Object.entries(byCat).sort((a, b) => b[1] - a[1])
    return (
      <div className="summary-row">
        <div className="summary-tile accent">
          <span className="sum-k">Total invested</span>
          <span className="sum-v">{currency(total)}</span>
          <span className="sum-hint">{rows.length} entr{rows.length === 1 ? 'y' : 'ies'}</span>
        </div>
        {top.slice(0, 3).map(([cat, amt]) => (
          <div key={cat} className="summary-tile">
            <span className="sum-k">{titleize(cat)}</span>
            <span className="sum-v">{compactCurrency(amt)}</span>
            <span className="sum-hint">{total ? Math.round((amt / total) * 100) : 0}% of spend</span>
          </div>
        ))}
      </div>
    )
  }

  return (
    <ResourceSection
      title="Investments"
      subtitle="Cloud, licences, hardware and consulting spent on each project."
      moduleName="Dev Tracking"
      fetcher={() => devApi.listInvestments()}
      create={wrap(devApi.createInvestment)}
      createLabel="Log investment"
      createTitle="Log an investment"
      update={wrap((row, payload) => devApi.updateInvestment(row.id, payload))}
      updateTitle="Edit investment"
      remove={wrap((row) => devApi.deleteInvestment(row.id))}
      removeLabel="investment"
      removeHint={(r) => `${r.vendor} · ${currency(r.amount)} · ${fmtDate(r.date)}`}
      emptyHint="Log the first cloud bill or licence for a project."
      emptyIcon={Cloud}
      summary={summary}
      rowsTransform={(rows) =>
        [...rows]
          .filter((r) => !projectFilter || String(r.project_id) === projectFilter)
          .sort((a, b) => (parseDate(b.date) ?? 0) - (parseDate(a.date) ?? 0) || b.id - a.id)
      }
      toolbarExtra={<ProjectFilter value={projectFilter} onChange={setProjectFilter} options={projectOptions} />}
      columns={[
        { key: 'date', header: 'Date', render: (r) => fmtDate(r.date) },
        { key: 'project_id', header: 'Project', render: (r) => <span className="cell-strong">{projectName(r.project_id)}</span> },
        { key: 'vendor', header: 'Vendor', render: (r) => r.vendor },
        { key: 'category', header: 'Category', render: (r) => <Badge status={r.category} /> },
        { key: 'amount', header: 'Amount', align: 'right', render: (r) => <span className="cell-num">{currency(r.amount)}</span> },
        { key: 'description', header: 'Note', render: (r) => <span className="cell-sub">{r.description || '—'}</span> },
      ]}
      fields={[
        {
          key: 'project_id',
          label: 'Project',
          type: 'select',
          numeric: true,
          required: true,
          full: true,
          options: projectOptions,
          placeholder: projectOptions.length ? 'Select a project…' : 'Create a project first',
        },
        { key: 'date', label: 'Date', type: 'date', required: true, default: today() },
        { key: 'amount', label: 'Amount', type: 'number', step: '0.01', min: 0, required: true },
        { key: 'vendor', label: 'Vendor', required: true, placeholder: 'AWS, GitHub, JetBrains…' },
        { key: 'category', label: 'Category', type: 'select', options: CATEGORIES, default: 'cloud' },
        { key: 'description', label: 'Note', type: 'textarea', full: true, nullable: true },
      ]}
    />
  )
}

/* ------------------------------------------------------------------------ */

function DownloadsSection({ projectOptions, projectName, onChanged }) {
  const [projectFilter, setProjectFilter] = useState('')
  const wrap = (fn) => async (...args) => {
    const out = await fn(...args)
    onChanged()
    return out
  }

  const summary = (rows) => {
    const series = downloadSeries(rows)
    const latest = series[series.length - 1]
    return (
      <Card className="chart-card">
        <div className="row spread">
          <h3>
            <Download size={15} style={{ verticalAlign: -2, marginRight: 6 }} />
            Download trend{projectFilter ? ` · ${projectName(projectFilter)}` : ''}
          </h3>
          {latest && (
            <span className="muted" style={{ fontSize: 13 }}>
              Latest: {number(latest.downloads)} downloads · {number(latest.stars)} stars
            </span>
          )}
        </div>
        {series.length > 1 ? (
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={series.map((d) => ({ ...d, label: fmtDate(d.date) }))} margin={{ left: -18, right: 6, top: 6 }}>
              <defs>
                <linearGradient id="dl-trend" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#aa3bff" stopOpacity={0.55} />
                  <stop offset="100%" stopColor="#aa3bff" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis dataKey="label" tick={{ fontSize: 11, fill: 'var(--text-dim)' }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 11, fill: 'var(--text-dim)' }} tickLine={false} axisLine={false} tickFormatter={compactNumber} />
              <Tooltip formatter={(v) => number(v)} />
              <Area type="monotone" dataKey="downloads" name="Downloads" stroke="#aa3bff" strokeWidth={2.5} fill="url(#dl-trend)" />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="chart-empty">Add a second snapshot to see a trend</div>
        )}
      </Card>
    )
  }

  return (
    <ResourceSection
      title="Downloads"
      subtitle="Snapshots of downloads and stars per platform, over time."
      moduleName="Dev Tracking"
      fetcher={() => devApi.listDownloads()}
      create={wrap(devApi.createDownload)}
      createLabel="Add snapshot"
      createTitle="Add a download snapshot"
      update={wrap((row, payload) => devApi.updateDownload(row.id, payload))}
      updateTitle="Edit snapshot"
      remove={wrap((row) => devApi.deleteDownload(row.id))}
      removeLabel="snapshot"
      removeHint={(r) => `${projectName(r.project_id)} · ${titleize(r.platform)} · ${fmtDate(r.date)}`}
      emptyHint="Record the first download count for a project."
      emptyIcon={Download}
      summary={summary}
      rowsTransform={(rows) =>
        [...rows]
          .filter((r) => !projectFilter || String(r.project_id) === projectFilter)
          .sort((a, b) => (parseDate(b.date) ?? 0) - (parseDate(a.date) ?? 0) || b.id - a.id)
      }
      toolbarExtra={<ProjectFilter value={projectFilter} onChange={setProjectFilter} options={projectOptions} />}
      columns={[
        { key: 'date', header: 'Date', render: (r) => fmtDate(r.date) },
        { key: 'project_id', header: 'Project', render: (r) => <span className="cell-strong">{projectName(r.project_id)}</span> },
        { key: 'platform', header: 'Platform', render: (r) => <Badge status={r.platform} /> },
        { key: 'download_count', header: 'Downloads', align: 'right', render: (r) => <span className="cell-num">{number(r.download_count)}</span> },
        { key: 'star_count', header: 'Stars', align: 'right', render: (r) => <span className="cell-num">{r.star_count == null ? '—' : number(r.star_count)}</span> },
      ]}
      fields={[
        {
          key: 'project_id',
          label: 'Project',
          type: 'select',
          numeric: true,
          required: true,
          full: true,
          options: projectOptions,
          placeholder: projectOptions.length ? 'Select a project…' : 'Create a project first',
        },
        { key: 'date', label: 'Snapshot date', type: 'date', required: true, default: today() },
        { key: 'platform', label: 'Platform', type: 'select', options: PLATFORMS, default: 'github' },
        { key: 'download_count', label: 'Downloads', type: 'number', min: 0, step: '1', required: true, default: 0 },
        { key: 'star_count', label: 'Stars', type: 'number', min: 0, step: '1', nullable: true },
      ]}
    />
  )
}

function ProjectFilter({ value, onChange, options }) {
  return (
    <Select value={value} onChange={(e) => onChange(e.target.value)} aria-label="Filter by project">
      <option value="">All projects</option>
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </Select>
  )
}
