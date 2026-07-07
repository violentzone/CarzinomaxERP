import { useState } from 'react'
import { Plus, AlertCircle } from 'lucide-react'
import { useList } from '../lib/useList'
import { useToast } from '../context/ToastContext'
import Table from './ui/Table'
import Button from './ui/Button'
import Modal from './ui/Modal'
import AccessDenied from './ui/AccessDenied'
import { SchemaForm, initialValues, buildPayload } from './SchemaForm'

/**
 * Generic "list + create" section for the straightforward CRUD resources
 * (accounts, products, vendors, departments, …). Complex flows with line items
 * or POST-only endpoints use bespoke components instead.
 *
 * Props:
 *  - title, subtitle, moduleName
 *  - fetcher: () => rows          (GET list)
 *  - deps: [] for the fetcher
 *  - columns: <Table> columns
 *  - create: (payload) => created (optional; omit for read-only lists)
 *  - fields: SchemaForm schema for the create modal
 *  - createLabel, createTitle
 *  - emptyHint
 *  - toolbarExtra: node rendered on the left of the toolbar (e.g. filters)
 *  - onExternalRows / rowsTransform: optional transform of fetched rows
 */
export default function ResourceSection({
  title,
  subtitle,
  moduleName,
  fetcher,
  deps = [],
  columns,
  create,
  fields = [],
  createLabel = 'New',
  createTitle,
  emptyHint,
  emptyIcon,
  toolbarExtra,
  rowsTransform,
}) {
  const toast = useToast()
  const { rows, loading, error, denied, reload } = useList(fetcher, deps)
  const [open, setOpen] = useState(false)
  const [values, setValues] = useState(() => initialValues(fields))
  const [saving, setSaving] = useState(false)

  if (denied) return <AccessDenied module={moduleName} />

  const openModal = () => {
    setValues(initialValues(fields))
    setOpen(true)
  }

  const submit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      await create(buildPayload(fields, values))
      toast.success(`${createTitle || createLabel} saved`)
      setOpen(false)
      reload()
    } catch (err) {
      toast.error(err?.detail || 'Could not save')
    } finally {
      setSaving(false)
    }
  }

  const displayRows = rowsTransform ? rowsTransform(rows) : rows

  return (
    <div>
      <div className="section-toolbar">
        <div>
          <h2>{title}</h2>
          {subtitle && <div className="muted">{subtitle}</div>}
        </div>
        <div className="filter-row">
          {toolbarExtra}
          {create && (
            <Button icon={Plus} onClick={openModal}>
              {createLabel}
            </Button>
          )}
        </div>
      </div>

      {error ? (
        <div className="empty-state">
          <AlertCircle size={24} color="var(--danger)" />
          <div className="empty-title">Couldn’t load {title.toLowerCase()}</div>
          <div className="muted">{error}</div>
          <div className="empty-action">
            <Button variant="outline" onClick={reload}>
              Retry
            </Button>
          </div>
        </div>
      ) : (
        <Table
          columns={columns}
          rows={displayRows}
          loading={loading}
          empty={{
            title: `No ${title.toLowerCase()} yet`,
            hint: emptyHint,
            icon: emptyIcon,
            action: create ? (
              <Button icon={Plus} variant="outline" onClick={openModal}>
                {createLabel}
              </Button>
            ) : null,
          }}
        />
      )}

      {create && (
        <Modal
          open={open}
          onClose={() => setOpen(false)}
          title={createTitle || createLabel}
          footer={
            <>
              <Button variant="ghost" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" form="resource-form" loading={saving}>
                Save
              </Button>
            </>
          }
        >
          <form id="resource-form" onSubmit={submit}>
            <SchemaForm fields={fields} values={values} setField={(k, v) => setValues((s) => ({ ...s, [k]: v }))} />
          </form>
        </Modal>
      )}
    </div>
  )
}
