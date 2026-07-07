import { useState } from 'react'
import { ShieldCheck, UserPlus } from 'lucide-react'
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
import SessionList from '../../components/ui/SessionList'
import { SchemaForm } from '../../components/SchemaForm'

const ROLES = Object.keys(ROLE_LABELS).map((v) => ({ value: v, label: ROLE_LABELS[v] }))

/** Admin-only: create users via POST /auth/register. */
export default function UsersPage() {
  const { user } = useAuth()
  const toast = useToast()
  const [values, setValues] = useState({ role: 'employee' })
  const [created, setCreated] = useState([])
  const [saving, setSaving] = useState(false)

  if (user?.role !== 'admin') return <AccessDenied module="user management" />

  const fields = [
    { key: 'full_name', label: 'Full name', placeholder: 'Ada Lovelace' },
    { key: 'email', label: 'Email', type: 'email', required: true, placeholder: 'ada@company.com' },
    { key: 'password', label: 'Temporary password', type: 'password', required: true },
    { key: 'role', label: 'Role', type: 'select', required: true, default: 'employee', options: ROLES },
  ]

  const submit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const u = await authApi.register({
        email: values.email,
        password: values.password,
        full_name: values.full_name || undefined,
        role: values.role || 'employee',
      })
      setCreated((c) => [u, ...c])
      toast.success(`User ${u.email} created`)
      setValues({ role: 'employee' })
    } catch (err) {
      toast.error(err?.detail || 'Could not create user')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="module-page">
      <PageHeader title="User Management" subtitle="Provision team members and assign module access." icon={ShieldCheck} />

      <Card className="card-pad" style={{ maxWidth: 640 }}>
        <form onSubmit={submit} className="col gap-4">
          <SchemaForm fields={fields} values={values} setField={(k, v) => setValues((s) => ({ ...s, [k]: v }))} />
          <div className="row" style={{ justifyContent: 'flex-end' }}>
            <Button type="submit" icon={UserPlus} loading={saving}>
              Create user
            </Button>
          </div>
        </form>
      </Card>

      <SessionList
        items={created}
        title="Users created this session"
        columns={[
          { key: 'id', header: '#', render: (r) => <span className="mono">{r.id}</span> },
          { key: 'full_name', header: 'Name', render: (r) => r.full_name || '—' },
          { key: 'email', header: 'Email' },
          { key: 'role', header: 'Role', render: (r) => <Badge tone="info">{titleize(r.role)}</Badge> },
        ]}
      />
    </div>
  )
}
