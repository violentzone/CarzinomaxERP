import { useState } from 'react'
import { Plus, AlertCircle, Pencil, Trash2, RefreshCw } from 'lucide-react'
import { useList } from '../lib/useList'
import { useToast } from '../context/ToastContext'
import Table from './ui/Table'
import Button from './ui/Button'
import Modal from './ui/Modal'
import ConfirmDialog from './ui/ConfirmDialog'
import AccessDenied from './ui/AccessDenied'
import { SchemaForm, initialValues, editValues, buildPayload } from './SchemaForm'

/**
 * Generic "list + create / edit / delete" section for CRUD resources. Every
 * module endpoint in the backend follows the same `*_list` / POST / PUT /
 * DELETE shape, so most tabs are a thin configuration of this component.
 *
 * Props:
 *  - title, subtitle, moduleName
 *  - fetcher: () => rows          (GET list)
 *  - deps: [] for the fetcher
 *  - columns: <Table> columns
 *  - idKey: primary-key field (default 'id'; dev projects use 'project_id')
 *  - create: (payload) => created (optional; omit for read-only lists)
 *  - fields: SchemaForm schema for the create/edit modal (or a function of
 *    the row being edited — `fields(null)` for create)
 *  - createLabel, createTitle
 *  - update: (row, payload) => promise (optional; adds a per-row edit action)
 *  - updateTitle: edit modal title ("Edit department", …)
 *  - remove: (row) => promise    (optional; adds a per-row delete action)
 *  - removeLabel: noun used in the delete confirmation ("department", …)
 *  - removeHint: extra consequence line, string or (row) => string
 *  - canRemove: (row) => bool     (hide delete for protected rows)
 *  - rowActions: (row, helpers) => node   extra per-row actions, rendered
 *    before edit/delete. helpers = { reload, toast }
 *  - emptyHint, emptyIcon
 *  - toolbarExtra: node rendered on the left of the toolbar (e.g. filters)
 *  - rowsTransform: optional transform of fetched rows (filter/sort/enrich)
 *  - summary: (rows) => node  rendered above the table (stat tiles, charts)
 *  - modalSize: 'sm' | 'md' | 'lg'
 *  - onRows: (rows) => void   notified whenever the list loads
 */
export default function ResourceSection({
  title,
  subtitle,
  moduleName,
  fetcher,
  deps = [],
  columns,
  idKey = 'id',
  create,
  fields = [],
  createLabel = 'New',
  createTitle,
  update,
  updateTitle = 'Edit',
  remove,
  removeLabel = 'record',
  removeHint,
  canRemove,
  rowActions,
  emptyHint,
  emptyIcon,
  toolbarExtra,
  rowsTransform,
  summary,
  modalSize = 'md',
  preparePayload,
}) {
  const toast = useToast()
  const { rows, loading, error, denied, reload } = useList(fetcher, deps)
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState(null) // row being edited, null = create
  const [values, setValues] = useState({})
  const [saving, setSaving] = useState(false)
  const [pendingRemove, setPendingRemove] = useState(null)
  const [removing, setRemoving] = useState(false)

  if (denied) return <AccessDenied module={moduleName} />

  const schemaFor = (row) => (typeof fields === 'function' ? fields(row) : fields)
  const activeFields = schemaFor(editing)

  const openModal = () => {
    setEditing(null)
    setValues(initialValues(schemaFor(null)))
    setOpen(true)
  }

  const openEdit = (row) => {
    setEditing(row)
    setValues(editValues(schemaFor(row), row))
    setOpen(true)
  }

  const submit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const finalize = (p) => (preparePayload ? preparePayload(p, editing, values) : p)
      if (editing) {
        await update(editing, finalize(buildPayload(activeFields, values, { clearNullable: true })))
        toast.success(`${updateTitle} saved`)
      } else {
        await create(finalize(buildPayload(activeFields, values)))
        toast.success(`${createTitle || createLabel} saved`)
      }
      setOpen(false)
      reload()
    } catch (err) {
      toast.error(err?.detail || 'Could not save')
    } finally {
      setSaving(false)
    }
  }

  const confirmRemove = async () => {
    setRemoving(true)
    try {
      await remove(pendingRemove)
      toast.success(`${removeLabel[0].toUpperCase()}${removeLabel.slice(1)} deleted`)
      setPendingRemove(null)
      reload()
    } catch (err) {
      toast.error(err?.detail || 'Could not delete')
    } finally {
      setRemoving(false)
    }
  }

  const displayRows = rowsTransform ? rowsTransform(rows) : rows
  const hasActions = update || remove || rowActions

  const tableColumns = hasActions
    ? [
        ...columns,
        {
          key: '__actions',
          header: '',
          align: 'right',
          render: (r) => (
            <span className="row-actions">
              {rowActions && rowActions(r, { reload, toast })}
              {update && (
                <button
                  type="button"
                  className="icon-btn"
                  onClick={() => openEdit(r)}
                  aria-label={`Edit ${removeLabel}`}
                  title="Edit"
                >
                  <Pencil size={15} />
                </button>
              )}
              {remove && (!canRemove || canRemove(r)) && (
                <button
                  type="button"
                  className="icon-btn line-remove"
                  onClick={() => setPendingRemove(r)}
                  aria-label={`Delete ${removeLabel}`}
                  title="Delete"
                >
                  <Trash2 size={15} />
                </button>
              )}
            </span>
          ),
        },
      ]
    : columns

  return (
    <div className="col gap-4">
      <div className="section-toolbar">
        <div>
          <h2>{title}</h2>
          {subtitle && <div className="muted">{subtitle}</div>}
        </div>
        <div className="filter-row">
          {typeof toolbarExtra === 'function' ? toolbarExtra({ reload, toast, rows }) : toolbarExtra}
          <button type="button" className="icon-btn" onClick={reload} aria-label="Refresh" title="Refresh">
            <RefreshCw size={16} className={loading ? 'spin' : ''} />
          </button>
          {create && (
            <Button icon={Plus} onClick={openModal}>
              {createLabel}
            </Button>
          )}
        </div>
      </div>

      {summary && !error && !loading && rows.length > 0 && summary(displayRows)}

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
          columns={tableColumns}
          rows={displayRows}
          rowKey={(row, i) => row?.[idKey] ?? i}
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

      {(create || update) && (
        <Modal
          open={open}
          onClose={() => setOpen(false)}
          title={editing ? updateTitle : createTitle || createLabel}
          size={modalSize}
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
            <SchemaForm
              fields={activeFields}
              values={values}
              setField={(k, v) => setValues((s) => ({ ...s, [k]: v }))}
            />
          </form>
        </Modal>
      )}

      {remove && (
        <ConfirmDialog
          open={!!pendingRemove}
          onClose={() => setPendingRemove(null)}
          onConfirm={confirmRemove}
          loading={removing}
          title={`Delete ${removeLabel}`}
          message={`This will permanently delete this ${removeLabel}.`}
          hint={typeof removeHint === 'function' ? (pendingRemove ? removeHint(pendingRemove) : undefined) : removeHint}
        />
      )}
    </div>
  )
}
