import { useState } from 'react'
import { Plus, AlertCircle, Pencil, Trash2 } from 'lucide-react'
import { useList } from '../lib/useList'
import { useToast } from '../context/ToastContext'
import Table from './ui/Table'
import Button from './ui/Button'
import Modal from './ui/Modal'
import ConfirmDialog from './ui/ConfirmDialog'
import AccessDenied from './ui/AccessDenied'
import { SchemaForm, initialValues, editValues, buildPayload } from './SchemaForm'

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
 *  - fields: SchemaForm schema for the create/edit modal
 *  - createLabel, createTitle
 *  - update: (row, payload) => promise (optional; adds a per-row edit action
 *    reusing `fields` prefilled from the row)
 *  - updateTitle: edit modal title ("Edit department", …)
 *  - remove: (row) => promise    (optional; adds a per-row delete action)
 *  - removeLabel: noun used in the delete confirmation ("department", …)
 *  - removeHint: extra consequence line shown in the delete confirmation
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
  update,
  updateTitle = 'Edit',
  remove,
  removeLabel = 'record',
  removeHint,
  emptyHint,
  emptyIcon,
  toolbarExtra,
  rowsTransform,
}) {
  const toast = useToast()
  const { rows, loading, error, denied, reload } = useList(fetcher, deps)
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState(null) // row being edited, null = create
  const [values, setValues] = useState(() => initialValues(fields))
  const [saving, setSaving] = useState(false)
  const [pendingRemove, setPendingRemove] = useState(null)
  const [removing, setRemoving] = useState(false)

  if (denied) return <AccessDenied module={moduleName} />

  const openModal = () => {
    setEditing(null)
    setValues(initialValues(fields))
    setOpen(true)
  }

  const openEdit = (row) => {
    setEditing(row)
    setValues(editValues(fields, row))
    setOpen(true)
  }

  const submit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      if (editing) {
        await update(editing, buildPayload(fields, values, { clearNullable: true }))
        toast.success(`${updateTitle} saved`)
      } else {
        await create(buildPayload(fields, values))
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

  const tableColumns = update || remove
    ? [
        ...columns,
        {
          key: 'actions',
          header: '',
          align: 'right',
          width: update && remove ? 80 : 44,
          render: (r) => (
            <span className="row-actions">
              {update && (
                <button
                  type="button"
                  className="icon-btn"
                  onClick={() => openEdit(r)}
                  aria-label={`Edit ${removeLabel}`}
                >
                  <Pencil size={15} />
                </button>
              )}
              {remove && (
                <button
                  type="button"
                  className="icon-btn line-remove"
                  onClick={() => setPendingRemove(r)}
                  aria-label={`Delete ${removeLabel}`}
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
          columns={tableColumns}
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

      {(create || update) && (
        <Modal
          open={open}
          onClose={() => setOpen(false)}
          title={editing ? updateTitle : createTitle || createLabel}
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

      {remove && (
        <ConfirmDialog
          open={!!pendingRemove}
          onClose={() => setPendingRemove(null)}
          onConfirm={confirmRemove}
          loading={removing}
          title={`Delete ${removeLabel}`}
          message={`This will permanently delete this ${removeLabel}.`}
          hint={removeHint}
        />
      )}
    </div>
  )
}
