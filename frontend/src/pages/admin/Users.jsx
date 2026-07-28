import { useState, useEffect } from 'react'
import {
  ShieldCheck,
  UserPlus,
  Wallet,
  Boxes,
  Users as UsersIcon,
  LineChart,
  Pencil,
  X,
} from 'lucide-react'
import { authApi } from '../../api/auth'
import { useAuth } from '../../context/AuthContext'
import { useToast } from '../../context/ToastContext'
import { titleize } from '../../lib/format'
import { ROLE_LABELS } from '../../lib/roles'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import Badge from '../../components/ui/Badge'
import AccessDenied from '../../components/ui/AccessDenied'
import Table from '../../components/ui/Table'
import { Field, Input, Select } from '../../components/ui/Field'

const ROLES = Object.keys(ROLE_LABELS).map((v) => ({ value: v, label: ROLE_LABELS[v] }))

export default function UsersPage() {
  const { user } = useAuth()
  const toast = useToast()

  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [selectedUser, setSelectedUser] = useState(null)

  const [values, setValues] = useState({
    email: '',
    full_name: '',
    role: 'employee',
    is_active: true,
    has_finance_access: false,
    has_scm_access: false,
    has_hr_access: false,
    has_dev_access: false,
    password: '',
  })

  const loadUsers = async () => {
    try {
      setLoading(true)
      const list = await authApi.listUsers()
      setUsers(list)
    } catch (err) {
      toast.error(err?.detail || 'Could not fetch users')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let alive = true
    if (user?.role === 'admin') {
      authApi.listUsers()
        .then((list) => {
          if (alive) {
            setUsers(list)
            setLoading(false)
          }
        })
        .catch((err) => {
          if (alive) {
            toast.error(err?.detail || 'Could not fetch users')
            setLoading(false)
          }
        })
    }
    return () => {
      alive = false
    }
  }, [user, toast])

  if (user?.role !== 'admin') return <AccessDenied module="user management" />

  const startEdit = (u) => {
    setSelectedUser(u)
    setValues({
      email: u.email,
      full_name: u.full_name || '',
      role: u.role || 'employee',
      is_active: u.is_active,
      has_finance_access: u.has_finance_access || false,
      has_scm_access: u.has_scm_access || false,
      has_hr_access: u.has_hr_access || false,
      has_dev_access: u.has_dev_access || false,
      password: '',
    })
  }

  const cancelEdit = () => {
    setSelectedUser(null)
    setValues({
      email: '',
      full_name: '',
      role: 'employee',
      is_active: true,
      has_finance_access: false,
      has_scm_access: false,
      has_hr_access: false,
      has_dev_access: false,
      password: '',
    })
  }

  const submit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      if (selectedUser) {
        // Edit flow
        const updated = await authApi.updateUser(selectedUser.id, {
          email: values.email,
          full_name: values.full_name,
          role: values.role,
          is_active: values.is_active,
          has_finance_access: values.has_finance_access,
          has_scm_access: values.has_scm_access,
          has_hr_access: values.has_hr_access,
          has_dev_access: values.has_dev_access,
          password: values.password || undefined,
        })
        toast.success(`User ${updated.email} updated successfully`)
        cancelEdit()
        loadUsers()
      } else {
        // Create flow
        if (!values.password) {
          toast.error('Password is required for new users')
          setSaving(false)
          return
        }
        const created = await authApi.register({
          email: values.email,
          password: values.password,
          full_name: values.full_name || undefined,
          role: values.role || 'employee',
          has_finance_access: values.has_finance_access,
          has_scm_access: values.has_scm_access,
          has_hr_access: values.has_hr_access,
          has_dev_access: values.has_dev_access,
        })
        toast.success(`User ${created.email} created successfully`)
        cancelEdit()
        loadUsers()
      }
    } catch (err) {
      toast.error(err?.detail || 'Could not save user')
    } finally {
      setSaving(false)
    }
  }

  const setField = (k, v) => setValues((s) => ({ ...s, [k]: v }))

  const columns = [
    {
      key: 'name',
      header: 'User details',
      render: (r) => (
        <div className="col">
          <span className="cell-strong" style={{ fontWeight: 600 }}>{r.full_name || '—'}</span>
          <span className="muted" style={{ fontSize: '13px' }}>{r.email}</span>
        </div>
      ),
    },
    {
      key: 'role',
      header: 'Role',
      render: (r) => <Badge tone={r.role === 'admin' ? 'success' : 'info'}>{ROLE_LABELS[r.role] || titleize(r.role)}</Badge>,
    },
    {
      key: 'permissions',
      header: 'Module access',
      render: (r) => (
        <div className="row gap-2 wrap">
          <Badge tone={r.has_finance_access ? 'success' : 'neutral'} style={{ opacity: r.has_finance_access ? 1 : 0.45 }}>
            Finance
          </Badge>
          <Badge tone={r.has_scm_access ? 'info' : 'neutral'} style={{ opacity: r.has_scm_access ? 1 : 0.45 }}>
            SCM
          </Badge>
          <Badge tone={r.has_hr_access ? 'warning' : 'neutral'} style={{ opacity: r.has_hr_access ? 1 : 0.45 }}>
            People
          </Badge>
          <Badge tone={r.has_dev_access ? 'danger' : 'neutral'} style={{ opacity: r.has_dev_access ? 1 : 0.45 }}>
            Dev
          </Badge>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      width: 90,
      render: (r) => (
        <Badge tone={r.is_active ? 'success' : 'danger'}>
          {r.is_active ? 'Active' : 'Inactive'}
        </Badge>
      ),
    },
    {
      key: 'actions',
      header: '',
      align: 'right',
      width: 80,
      render: (r) => (
        <Button variant="ghost" size="sm" icon={Pencil} onClick={() => startEdit(r)}>
          Edit
        </Button>
      ),
    },
  ]

  return (
    <div className="module-page col gap-5">
      <PageHeader
        title="User Management"
        subtitle="Provision team members, reset passwords, and configure module-level access."
        icon={ShieldCheck}
      />

      <div className="row items-start gap-5 wrap" style={{ width: '100%' }}>
        {/* Left Side: Users List */}
        <div style={{ flex: '2 1 600px', minWidth: 320 }} className="col gap-4">
          <Card className="card-pad col gap-4">
            <div className="row spread">
              <div>
                <h2>System Users</h2>
                <p className="muted">Currently registered system accounts and their authorizations.</p>
              </div>
              <Button onClick={loadUsers} variant="outline" size="sm">
                Refresh
              </Button>
            </div>

            <Table
              columns={columns}
              rows={users}
              loading={loading}
              empty={{
                title: 'No users found',
                hint: 'Try refreshing or create a new user.',
              }}
            />
          </Card>
        </div>

        {/* Right Side: Form */}
        <div style={{ flex: '1 1 350px', minWidth: 320 }} className="col gap-4">
          <Card className="card-pad col gap-4" variant={!!selectedUser}>
            <div>
              <h2>{selectedUser ? 'Edit User Permissions' : 'Create User Account'}</h2>
              <p className="muted">
                {selectedUser
                  ? `Configure account details and module permissions for ${selectedUser.email}.`
                  : 'Register a new team member and assign their initial workspace access.'}
              </p>
            </div>

            <form onSubmit={submit} className="col gap-4">
              <Field label="Full Name" required={!selectedUser}>
                <Input
                  value={values.full_name}
                  onChange={(e) => setField('full_name', e.target.value)}
                  placeholder="e.g. Ada Lovelace"
                  required={!selectedUser}
                />
              </Field>

              <Field label="Email Address" required>
                <Input
                  type="email"
                  value={values.email}
                  onChange={(e) => setField('email', e.target.value)}
                  placeholder="e.g. ada@company.com"
                  required
                />
              </Field>

              <Field
                label={selectedUser ? 'Change Password' : 'Temporary Password'}
                required={!selectedUser}
                hint={selectedUser ? 'Leave blank to keep existing password' : ''}
              >
                <Input
                  type="password"
                  value={values.password}
                  onChange={(e) => setField('password', e.target.value)}
                  placeholder={selectedUser ? '••••••••' : 'Enter temporary password'}
                  required={!selectedUser}
                />
              </Field>

              <Field label="Base System Role" required>
                <Select value={values.role} onChange={(e) => setField('role', e.target.value)} required>
                  {ROLES.map((r) => (
                    <option key={r.value} value={r.value}>
                      {r.label}
                    </option>
                  ))}
                </Select>
              </Field>

              <Field label="Account Status">
                <Select
                  value={values.is_active ? 'active' : 'inactive'}
                  onChange={(e) => setField('is_active', e.target.value === 'active')}
                >
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                </Select>
              </Field>

              {/* Granular Module Permissions */}
              <div className="col gap-3" style={{ padding: 'var(--s-2) 0', borderTop: '1px solid var(--border)', marginTop: 'var(--s-2)' }}>
                <span className="field-label" style={{ fontWeight: 600 }}>Granular Module Permissions</span>
                <span className="field-hint muted">Check which navbar items this user is authorized to access:</span>
                
                <div className="col gap-3" style={{ marginTop: 'var(--s-1)' }}>
                  <label className="row gap-3" style={{ cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      style={{ cursor: 'pointer', width: 17, height: 17 }}
                      checked={values.has_finance_access}
                      onChange={(e) => setField('has_finance_access', e.target.checked)}
                    />
                    <div className="row gap-2">
                      <Wallet size={16} className="muted" />
                      <span>Finance & Accounting</span>
                    </div>
                  </label>

                  <label className="row gap-3" style={{ cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      style={{ cursor: 'pointer', width: 17, height: 17 }}
                      checked={values.has_scm_access}
                      onChange={(e) => setField('has_scm_access', e.target.checked)}
                    />
                    <div className="row gap-2">
                      <Boxes size={16} className="muted" />
                      <span>Supply Chain</span>
                    </div>
                  </label>

                  <label className="row gap-3" style={{ cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      style={{ cursor: 'pointer', width: 17, height: 17 }}
                      checked={values.has_hr_access}
                      onChange={(e) => setField('has_hr_access', e.target.checked)}
                    />
                    <div className="row gap-2">
                      <UsersIcon size={16} className="muted" />
                      <span>People & HR</span>
                    </div>
                  </label>

                  <label className="row gap-3" style={{ cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      style={{ cursor: 'pointer', width: 17, height: 17 }}
                      checked={values.has_dev_access}
                      onChange={(e) => setField('has_dev_access', e.target.checked)}
                    />
                    <div className="row gap-2">
                      <LineChart size={16} className="muted" />
                      <span>Dev Tracking</span>
                    </div>
                  </label>
                </div>
              </div>

              <div className="row gap-2" style={{ justifyContent: 'flex-end', borderTop: '1px solid var(--border)', paddingTop: 'var(--s-3)' }}>
                {selectedUser && (
                  <Button variant="ghost" icon={X} onClick={cancelEdit} disabled={saving}>
                    Cancel
                  </Button>
                )}
                <Button type="submit" icon={selectedUser ? ShieldCheck : UserPlus} loading={saving}>
                  {selectedUser ? 'Save Permissions' : 'Create User'}
                </Button>
              </div>
            </form>
          </Card>
        </div>
      </div>
    </div>
  )
}
