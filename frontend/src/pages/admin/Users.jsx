import { useState } from 'react'
import { ShieldCheck, UserPlus, Wallet, Boxes, Users as UsersIcon, LineChart, Mail, Pencil, Trash2, X, Eye, EyeOff } from 'lucide-react'
import { hrApi } from '../../api/hr'
import { useAuth } from '../../context/AuthContext'
import { useToast } from '../../context/ToastContext'
import { useList } from '../../lib/useList'
import { date as fmtDate, userName } from '../../lib/format'
import { accessLabel, MODULE_FLAGS } from '../../lib/roles'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import Badge from '../../components/ui/Badge'
import AccessDenied from '../../components/ui/AccessDenied'
import Table from '../../components/ui/Table'
import ConfirmDialog from '../../components/ui/ConfirmDialog'
import Drawer from '../../components/ui/Drawer'
import { Field, Input, Select } from '../../components/ui/Field'

const PERMISSIONS = [
  { key: 'has_dev_access', label: 'Dev Tracking', hint: 'Projects, investments, downloads', icon: LineChart },
  { key: 'has_hr_access', label: 'People & Payroll', hint: 'Users, attendance, leave, paychecks', icon: UsersIcon },
  { key: 'has_finance_access', label: 'Finance', hint: 'Expense ledger & overview', icon: Wallet },
  { key: 'has_scm_access', label: 'Purchases', hint: 'Products and purchases', icon: Boxes },
]

const EMPTY = {
  email: '',
  full_name: '',
  password: '',
  is_active: true,
  has_finance_access: false,
  has_scm_access: false,
  has_hr_access: false,
  has_dev_access: false,
  send_summary: false,
}

/**
 * User management (HR access required). Users are the employee directory and
 * carry per-module access flags; there is no separate "admin" role — a user
 * with all four flags is effectively an administrator.
 */
export default function UsersPage() {
  const { user: me, can, reload: reloadMe } = useAuth()
  const toast = useToast()
  const { rows: users, loading, denied, error, reload } = useList(() => hrApi.listUsers())

  const [drawerOpen, setDrawerOpen] = useState(false)
  const [selected, setSelected] = useState(null)
  const [values, setValues] = useState(EMPTY)
  const [showPassword, setShowPassword] = useState(false)
  const [saving, setSaving] = useState(false)
  const [pendingRemove, setPendingRemove] = useState(null)
  const [removing, setRemoving] = useState(false)

  if (!can('hr') || denied) return <AccessDenied module="user management" />

  const setField = (k, v) => setValues((s) => ({ ...s, [k]: v }))
  const isSelf = (u) => u && me && u.id === me.id
  const nameCleared = !!selected?.full_name && !values.full_name.trim()

  const startCreate = () => {
    setSelected(null)
    setValues(EMPTY)
    setShowPassword(false)
    setDrawerOpen(true)
  }

  const startEdit = (u) => {
    setSelected(u)
    setValues({
      email: u.email || '',
      full_name: u.full_name || '',
      password: '',
      is_active: !!u.is_active,
      has_finance_access: !!u.has_finance_access,
      has_scm_access: !!u.has_scm_access,
      has_hr_access: !!u.has_hr_access,
      has_dev_access: !!u.has_dev_access,
      send_summary: !!u.send_summary,
    })
    setShowPassword(false)
    setDrawerOpen(true)
  }

  // The form keeps its values while the drawer slides out; they are reset on the next open.
  const closeDrawer = () => setDrawerOpen(false)

  const submit = async (e) => {
    e.preventDefault()
    const email = values.email.trim()
    const fullName = values.full_name.trim()
    const toggles = ['is_active', 'send_summary', ...Object.values(MODULE_FLAGS)]
    let payload

    if (selected) {
      if (isSelf(selected) && !values.is_active) {
        toast.error('You cannot deactivate your own account')
        return
      }
      if (nameCleared) {
        toast.error("Full name can't be cleared")
        return
      }
      // Send only what was edited, so a change another admin made meanwhile is not overwritten.
      payload = {}
      if (email !== (selected.email || '')) payload.email = email
      if (fullName !== (selected.full_name || '')) payload.full_name = fullName
      for (const key of toggles) {
        if (!!values[key] !== !!selected[key]) payload[key] = !!values[key]
      }
      if (values.password) payload.password = values.password
      if (!Object.keys(payload).length) {
        toast.info('No changes to save')
        closeDrawer()
        return
      }
    } else {
      if (!values.password) {
        toast.error('A password is required for new users')
        return
      }
      payload = { email, password: values.password, full_name: fullName || undefined }
      for (const key of toggles) payload[key] = !!values[key]
    }

    setSaving(true)
    try {
      if (selected) {
        await hrApi.updateUser(selected.id, payload)
        toast.success(`${fullName || email} updated`)
        if (isSelf(selected)) {
          await reloadMe()
          if (payload.has_hr_access === false) toast.info('You removed your own HR access — this page is now locked')
        }
      } else {
        await hrApi.createUser(payload)
        toast.success(`${fullName || email} created`)
      }
      closeDrawer()
      reload()
    } catch (err) {
      toast.error(err?.detail || 'Could not save user')
    } finally {
      setSaving(false)
    }
  }

  const confirmRemove = async () => {
    setRemoving(true)
    try {
      await hrApi.deleteUser(pendingRemove.id)
      toast.success(`${userName(pendingRemove)} deleted`)
      setPendingRemove(null)
      reload()
    } catch (err) {
      toast.error(err?.detail || 'Could not delete user')
    } finally {
      setRemoving(false)
    }
  }

  const sorted = [...users].sort(
    (a, b) => Number(b.is_active) - Number(a.is_active) || userName(a).localeCompare(userName(b)),
  )

  const columns = [
    {
      key: 'name',
      header: 'User',
      render: (r) => (
        <div className="col">
          <span className="cell-strong">
            {r.full_name || '—'}
            {isSelf(r) && (
              <span className="muted" style={{ fontWeight: 400, marginLeft: 6, fontSize: 12 }}>
                (you)
              </span>
            )}
          </span>
          <span className="cell-sub">{r.email}</span>
        </div>
      ),
    },
    {
      key: 'access',
      header: 'Access',
      render: (r) => {
        const granted = PERMISSIONS.filter((p) => r[p.key])
        return (
          <div className="col gap-1">
            <span style={{ fontSize: 13 }}>{accessLabel(r)}</span>
            <div className="row gap-1 wrap">
              {granted.length ? (
                granted.map((p) => (
                  <Badge key={p.key} tone="success">
                    {p.label}
                  </Badge>
                ))
              ) : (
                <span className="muted" style={{ fontSize: 12 }}>
                  No module access
                </span>
              )}
            </div>
          </div>
        )
      },
    },
    { key: 'created_at', header: 'Joined', className: 'nowrap', render: (r) => <span className="muted">{fmtDate(r.created_at)}</span> },
    {
      key: 'status',
      header: 'Status',
      width: 90,
      render: (r) => <Badge tone={r.is_active ? 'success' : 'danger'}>{r.is_active ? 'Active' : 'Inactive'}</Badge>,
    },
    {
      key: 'send_summary',
      header: 'Summary',
      width: 90,
      render: (r) => (r.send_summary ? <Badge tone="info">Email</Badge> : <span className="muted">—</span>),
    },
    {
      key: 'actions',
      header: '',
      align: 'right',
      width: 80,
      render: (r) => (
        <span className="row-actions">
          <button type="button" className="icon-btn" onClick={() => startEdit(r)} aria-label="Edit user" title="Edit">
            <Pencil size={15} />
          </button>
          {!isSelf(r) && (
            <button
              type="button"
              className="icon-btn line-remove"
              onClick={() => setPendingRemove(r)}
              aria-label="Delete user"
              title="Delete"
            >
              <Trash2 size={15} />
            </button>
          )}
        </span>
      ),
    },
  ]

  return (
    <div className="module-page col gap-5">
      <PageHeader
        title="Users & Access"
        subtitle="Provision team members, reset passwords and choose which modules each person can open."
        icon={ShieldCheck}
      />

      <Card className="card-pad col gap-4">
        <div className="row spread">
          <div>
            <h2>Team</h2>
            <p className="muted">Everyone with an account, and what they can access.</p>
          </div>
          <div className="row gap-2">
            <Button onClick={reload} variant="outline" size="sm" loading={loading}>
              Refresh
            </Button>
            <Button onClick={startCreate} size="sm" icon={UserPlus}>
              New user
            </Button>
          </div>
        </div>

        {error ? (
          <div className="note-box">{error}</div>
        ) : (
          <Table
            columns={columns}
            rows={sorted}
            loading={loading}
            empty={{ title: 'No users found', hint: 'Create the first account with the New user button.' }}
          />
        )}
      </Card>

      <Drawer
        open={drawerOpen}
        onClose={closeDrawer}
        title={selected ? 'Edit user' : 'New user'}
        subtitle={
          selected
            ? [selected.full_name, selected.email].filter(Boolean).join(' · ')
            : 'Register a team member and grant their initial module access.'
        }
        footer={
          <>
            <Button variant="ghost" icon={X} onClick={closeDrawer} disabled={saving}>
              Cancel
            </Button>
            <Button type="submit" form="user-form" icon={selected ? ShieldCheck : UserPlus} loading={saving}>
              {selected ? 'Save changes' : 'Create user'}
            </Button>
          </>
        }
      >
        <form id="user-form" onSubmit={submit} className="col gap-4">
          <Field label="Full name" error={nameCleared ? "Full name can't be cleared." : undefined}>
            <Input
              value={values.full_name}
              onChange={(e) => setField('full_name', e.target.value)}
              placeholder="e.g. Ada Lovelace"
              autoFocus
            />
          </Field>

          <Field label="Email" required>
            <Input
              type="email"
              value={values.email}
              onChange={(e) => setField('email', e.target.value)}
              placeholder="e.g. ada@company.com"
              required
            />
          </Field>

          <Field
            label={selected ? 'New password' : 'Password'}
            required={!selected}
            hint={selected ? 'Leave blank to keep the current password.' : 'Share it with the person; they can’t change it themselves yet.'}
          >
            <div className="control-affix">
              <Input
                type={showPassword ? 'text' : 'password'}
                value={values.password}
                onChange={(e) => setField('password', e.target.value)}
                placeholder={selected ? '••••••••' : 'Temporary password'}
                required={!selected}
                autoComplete="new-password"
              />
              <button
                type="button"
                className="icon-btn"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                title={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
          </Field>

          <Field label="Account status" hint={selected && isSelf(selected) ? 'You cannot deactivate yourself.' : undefined}>
            <Select
              value={values.is_active ? 'active' : 'inactive'}
              disabled={selected && isSelf(selected)}
              onChange={(e) => setField('is_active', e.target.value === 'active')}
            >
              <option value="active">Active</option>
              <option value="inactive">Inactive — cannot sign in</option>
            </Select>
          </Field>

          <div className="col gap-2" style={{ borderTop: '1px solid var(--border)', paddingTop: 'var(--s-3)' }}>
            <span className="field-label">Module access</span>
            <div className="perm-grid">
              {PERMISSIONS.map((p) => {
                const Icon = p.icon
                return (
                  <label key={p.key} className="check-field">
                    <input
                      type="checkbox"
                      checked={!!values[p.key]}
                      onChange={(e) => setField(p.key, e.target.checked)}
                    />
                    <span>
                      <span className="field-label row gap-2" style={{ alignItems: 'center' }}>
                        <Icon size={14} className="muted" /> {p.label}
                      </span>
                      <span className="field-hint muted">{p.hint}</span>
                    </span>
                  </label>
                )
              })}
            </div>
            <span className="field-hint muted">
              All four together make an administrator. User management needs People &amp; Payroll.
            </span>
          </div>

          <div className="col gap-2" style={{ borderTop: '1px solid var(--border)', paddingTop: 'var(--s-3)' }}>
            <span className="field-label">Notifications</span>
            <label className="check-field">
              <input
                type="checkbox"
                checked={!!values.send_summary}
                onChange={(e) => setField('send_summary', e.target.checked)}
              />
              <span>
                <span className="field-label row gap-2" style={{ alignItems: 'center' }}>
                  <Mail size={14} className="muted" /> Receive project summary email
                </span>
                <span className="field-hint muted">
                  AI-written status summary of every module, sent on the schedule set in the server config. Inactive accounts are skipped.
                </span>
              </span>
            </label>
          </div>
        </form>
      </Drawer>

      <ConfirmDialog
        open={!!pendingRemove}
        onClose={() => setPendingRemove(null)}
        onConfirm={confirmRemove}
        loading={removing}
        title="Delete user"
        message={pendingRemove ? `This will permanently delete ${userName(pendingRemove)}.` : ''}
        hint="Their attendance logs, leave requests and paychecks are deleted with them. Prefer marking the account inactive to keep history."
      />
    </div>
  )
}
